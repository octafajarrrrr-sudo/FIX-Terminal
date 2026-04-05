"""Executor bot main loop.

Continuously monitors Binance funding rates, opens LONG positions
on pairs with highly negative funding rates just before settlement,
collects the funding fee, and closes the position shortly after.
"""

import os
import sys
import time
import signal
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.executor.binance_client import BinanceClient
from agents.executor import strategy
from agents.executor.risk_manager import RiskManager
from agents.executor.logger import log_trade, log_error, log_exception
from agents.executor import metrics_exporter

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("executor")

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
RELOAD_FLAG = PROJECT_ROOT / "agents" / "executor" / "reload.flag"

shutdown_event = False


def _handle_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_event
    logger.info("Received signal %d, shutting down...", signum)
    shutdown_event = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def load_config() -> dict:
    """Load configuration from config.yaml.

    Returns:
        Parsed config dict.
    """
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def run():
    """Main executor loop."""
    global shutdown_event

    config = load_config()
    exec_cfg = config["executor"]
    strat_cfg = exec_cfg["strategy"]
    risk_cfg = exec_cfg["risk"]
    binance_cfg = exec_cfg["binance"]

    client = BinanceClient(
        testnet=binance_cfg.get("testnet", True),
    )
    risk = RiskManager(risk_cfg)

    leverage = binance_cfg.get("futures_leverage", 10)
    margin_mode = binance_cfg.get("margin_mode", "ISOLATED")
    min_funding_rate = strat_cfg.get("min_funding_rate", -1.0)
    max_pairs = strat_cfg.get("max_concurrent_pairs", 3)
    margin_per_trade = strat_cfg.get("margin_per_trade_usd", 10)
    entry_window = strat_cfg.get("entry_window_seconds", 10)
    exit_window = strat_cfg.get("exit_window_seconds", 5)

    # Track cumulative stats for metrics
    total_profit = 0.0
    total_trades = 0
    total_wins = 0

    # Start prometheus metrics server
    metrics_exporter.start_metrics_server(port=8000)

    logger.info("Executor bot started. min_rate=%.2f%%, leverage=%dx, poll_interval=30s", min_funding_rate, leverage)

    config_mtime = os.path.getmtime(CONFIG_PATH) if CONFIG_PATH.exists() else 0

    while not shutdown_event:
        try:
            # Check for config reload
            if CONFIG_PATH.exists():
                current_mtime = os.path.getmtime(CONFIG_PATH)
                if current_mtime > config_mtime:
                    logger.info("Config changed, reloading...")
                    config = load_config()
                    exec_cfg = config["executor"]
                    strat_cfg = exec_cfg["strategy"]
                    risk_cfg = exec_cfg["risk"]
                    min_funding_rate = strat_cfg.get("min_funding_rate", -1.0)
                    max_pairs = strat_cfg.get("max_concurrent_pairs", 3)
                    margin_per_trade = strat_cfg.get("margin_per_trade_usd", 10)
                    entry_window = strat_cfg.get("entry_window_seconds", 10)
                    exit_window = strat_cfg.get("exit_window_seconds", 5)
                    config_mtime = current_mtime

            # Check reload flag file
            if RELOAD_FLAG.exists():
                logger.info("Reload flag detected, reloading config...")
                config = load_config()
                exec_cfg = config["executor"]
                strat_cfg = exec_cfg["strategy"]
                min_funding_rate = strat_cfg.get("min_funding_rate", -1.0)
                max_pairs = strat_cfg.get("max_concurrent_pairs", 3)
                margin_per_trade = strat_cfg.get("margin_per_trade_usd", 10)
                RELOAD_FLAG.unlink(missing_ok=True)

            # Daily reset check
            risk.check_daily_reset()

            # Check if paused
            if risk.is_paused():
                logger.info("Bot is paused, waiting...")
                time.sleep(30)
                continue

            if risk.check_daily_loss():
                logger.warning("Daily loss limit reached, pausing until reset")
                risk.pause(duration_seconds=3600)
                continue

            if risk.check_consecutive_losses():
                logger.warning("Consecutive loss limit, pausing 60 minutes")
                risk.pause(duration_seconds=3600)
                continue

            # Fetch funding rates
            rates = client.get_funding_rates()
            if not rates:
                time.sleep(30)
                continue

            # Filter, sort, select
            filtered = strategy.filter_pairs(rates, min_funding_rate)
            sorted_pairs = strategy.sort_by_rate(filtered, ascending=True)
            top_pairs = strategy.select_top_pairs(sorted_pairs, max_pairs)

            if not top_pairs:
                time.sleep(30)
                continue

            # Check existing positions
            open_positions = client.get_open_positions()
            open_symbols = {p.get("symbol", "") for p in open_positions}
            metrics_exporter.update_open_positions(len(open_positions))

            for pair in top_pairs:
                if shutdown_event:
                    break

                symbol = pair["symbol"]
                if symbol in open_symbols:
                    continue

                next_funding = pair.get("next_funding_time", 0)
                if not strategy.entry_timing(next_funding, entry_window):
                    continue

                mark_price = pair.get("mark_price", 0) or client.get_mark_price(symbol)
                if mark_price <= 0:
                    continue

                qty = strategy.calculate_quantity(margin_per_trade, leverage, mark_price)
                if qty <= 0:
                    continue

                # Configure margin and leverage
                client.set_leverage(symbol, leverage)
                client.set_margin_type(symbol, margin_mode)

                # Entry: open LONG
                logger.info("Opening LONG %s qty=%.6f rate=%.4f%%", symbol, qty, pair["funding_rate"])
                entry_order = client.create_market_order(symbol, "buy", qty)
                if not entry_order:
                    metrics_exporter.record_error()
                    log_error({
                        "source": "executor.entry_order",
                        "message": f"Failed to open LONG {symbol}",
                        "level": "ERROR",
                        "details": {"symbol": symbol, "qty": qty, "rate": pair["funding_rate"]},
                    })
                    log_trade({
                        "symbol": symbol,
                        "funding_rate": pair["funding_rate"],
                        "profit_net": 0,
                        "status": "ERROR",
                        "error": "entry_order_failed",
                    })
                    continue

                entry_price = float(entry_order.get("average", mark_price))

                # Wait for funding settlement
                wait_ms = max(0, next_funding - int(time.time() * 1000))
                wait_sec = wait_ms / 1000.0
                logger.info("Waiting %.1f seconds for settlement...", wait_sec)

                # Wait in small increments to allow stop-loss checks
                waited = 0.0
                early_exit = False
                while waited < wait_sec and not shutdown_event:
                    step = min(1.0, wait_sec - waited)
                    time.sleep(step)
                    waited += step

                    current_price = client.get_mark_price(symbol)
                    if current_price > 0 and risk.stop_loss_triggered(entry_price, current_price, "long"):
                        logger.warning("Stop loss triggered during wait for %s", symbol)
                        early_exit = True
                        break

                # Wait exit_window after settlement (unless early exit)
                if not early_exit and not shutdown_event:
                    time.sleep(exit_window)

                # Exit: close LONG
                logger.info("Closing LONG %s", symbol)
                exit_order = client.create_market_order(symbol, "sell", qty)

                exit_price = 0.0
                if exit_order:
                    exit_price = float(exit_order.get("average", 0))

                # Calculate approximate profit
                price_pnl = (exit_price - entry_price) * qty if exit_price > 0 else 0
                funding_income = abs(pair["funding_rate"] / 100) * margin_per_trade * leverage
                # Rough fee estimate: 0.04% taker fee each way
                fees = 2 * 0.0004 * margin_per_trade * leverage
                profit_net = price_pnl + funding_income - fees

                total_profit += profit_net
                total_trades += 1
                if profit_net > 0:
                    total_wins += 1

                # Update risk manager
                risk.update_daily_loss(profit_net)

                # Update metrics
                metrics_exporter.update_profit(total_profit)
                metrics_exporter.update_daily_loss(risk.daily_loss)
                metrics_exporter.record_trade(won=(profit_net > 0))
                if total_trades > 0:
                    metrics_exporter.update_win_rate((total_wins / total_trades) * 100)

                trade_status = "SUCCESS" if not early_exit else "STOP_LOSS"
                log_trade({
                    "symbol": symbol,
                    "funding_rate": pair["funding_rate"],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "quantity": qty,
                    "price_pnl": round(price_pnl, 6),
                    "funding_income": round(funding_income, 6),
                    "fees": round(fees, 6),
                    "profit_net": round(profit_net, 6),
                    "status": trade_status,
                })

            # Update balance metric
            balance = client.get_account_balance()
            metrics_exporter.update_balance(balance)

        except Exception as e:
            logger.error("Unexpected error in main loop: %s", e, exc_info=True)
            log_exception("executor.main_loop", e, critical=True)
            metrics_exporter.record_error()
            if risk_cfg.get("pause_on_error", True):
                risk.pause(duration_seconds=300)

        time.sleep(30)

    logger.info("Executor bot stopped")


if __name__ == "__main__":
    run()
