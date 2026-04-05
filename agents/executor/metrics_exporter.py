"""Prometheus metrics exporter for the executor bot.

Exposes trading metrics on an HTTP endpoint for Prometheus to scrape.
"""

import threading
import logging
from prometheus_client import start_http_server, Gauge, Counter

logger = logging.getLogger(__name__)

# -- Gauges (current values) --
TOTAL_PROFIT = Gauge("executor_total_profit_usd", "Total cumulative profit in USD")
WIN_RATE = Gauge("executor_win_rate", "Current win rate as a percentage")
OPEN_POSITIONS = Gauge("executor_open_positions", "Number of currently open positions")
DAILY_LOSS = Gauge("executor_daily_loss_usd", "Total daily loss in USD")
ACCOUNT_BALANCE = Gauge("executor_account_balance_usd", "Futures account balance in USD")

# -- Counters --
TRADES_TOTAL = Counter("executor_trades_total", "Total number of trades executed")
TRADES_WON = Counter("executor_trades_won", "Total number of winning trades")
TRADES_LOST = Counter("executor_trades_lost", "Total number of losing trades")
ERRORS_TOTAL = Counter("executor_errors_total", "Total number of errors encountered")


def start_metrics_server(port: int = 8000):
    """Start the Prometheus metrics HTTP server in a background thread.

    Args:
        port: Port to serve metrics on (default 8000).
    """
    def _start():
        try:
            start_http_server(port)
            logger.info("Prometheus metrics server started on port %d", port)
        except Exception as e:
            logger.error("Failed to start metrics server: %s", e)

    thread = threading.Thread(target=_start, daemon=True)
    thread.start()


def update_profit(profit: float):
    """Update the total profit gauge."""
    TOTAL_PROFIT.set(profit)


def update_win_rate(rate: float):
    """Update the win rate gauge."""
    WIN_RATE.set(rate)


def update_open_positions(count: int):
    """Update the open positions gauge."""
    OPEN_POSITIONS.set(count)


def update_daily_loss(loss: float):
    """Update the daily loss gauge."""
    DAILY_LOSS.set(loss)


def update_balance(balance: float):
    """Update the account balance gauge."""
    ACCOUNT_BALANCE.set(balance)


def record_trade(won: bool):
    """Record a completed trade.

    Args:
        won: True if the trade was profitable.
    """
    TRADES_TOTAL.inc()
    if won:
        TRADES_WON.inc()
    else:
        TRADES_LOST.inc()


def record_error():
    """Record an error occurrence."""
    ERRORS_TOTAL.inc()
