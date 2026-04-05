"""Telegram approval bot with AI conversation capabilities.

Runs as a long-polling Telegram bot that:
1. Periodically checks for new suggestions from the LLM analyst.
2. Sends recommendations to the user for approval.
3. Processes yes/no replies to update config or reject changes.
4. Allows the user to view/change parameters, request analysis, and chat with the AI.
5. Sends error notifications from the executor bot.
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from agents.approval.config_updater import update_config, reload_executor
from agents.analyst.log_reader import read_trades, aggregate
from agents.analyst.openrouter_client import call_qwen
from agents.analyst.json_parser import parse_llm_response

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_bot")

SUGGESTIONS_PATH = PROJECT_ROOT / "shared" / "data" / "suggestions.json"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
ERRORS_LOG = PROJECT_ROOT / "shared" / "logs" / "errors.log"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# In-memory state
pending_suggestion = None

# Telegram bot application reference for error notifications
_bot_app = None


def _is_authorized(update: Update) -> bool:
    """Check if the message comes from the authorized chat."""
    return str(update.effective_chat.id) == str(CHAT_ID)


def load_config() -> dict:
    """Load the current config.yaml."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def load_suggestions() -> dict | None:
    """Load suggestions.json if it contains an unapproved recommendation."""
    if not SUGGESTIONS_PATH.exists():
        return None
    try:
        with open(SUGGESTIONS_PATH, "r") as f:
            data = json.load(f)
        if data.get("approved") is None:
            return data
        return None
    except Exception as e:
        logger.error("Failed to read suggestions: %s", e)
        return None


def save_suggestion_status(approved: bool):
    """Update the approved field in suggestions.json."""
    try:
        if SUGGESTIONS_PATH.exists():
            with open(SUGGESTIONS_PATH, "r") as f:
                data = json.load(f)
            data["approved"] = approved
            data["decided_at"] = datetime.now(timezone.utc).isoformat()
            with open(SUGGESTIONS_PATH, "w") as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        logger.error("Failed to update suggestion status: %s", e)


def format_suggestion_message(suggestion: dict) -> str:
    """Format a suggestion dict into a readable Telegram message."""
    action = suggestion.get("action", "UNKNOWN")
    reason = suggestion.get("reason", "No reason provided")
    changes = suggestion.get("suggestions", {})
    stats = suggestion.get("stats", {})

    lines = [
        "LLM Analyst Recommendation",
        "",
        f"Action: {action}",
        f"Reason: {reason}",
        "",
        "Performance (24h):",
        f"  Trades: {stats.get('total_trades', 0)}",
        f"  Win rate: {stats.get('win_rate', 0):.1f}%",
        f"  Total profit: ${stats.get('total_profit', 0):.4f}",
        "",
    ]

    if changes:
        lines.append("Proposed Changes:")
        for key, val in changes.items():
            if val is not None:
                lines.append(f"  {key}: {val}")
        lines.append("")

    lines.append("Reply 'yes' to approve or 'no' to reject.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show help."""
    if not _is_authorized(update):
        return

    await update.message.reply_text(
        "Funding Fee Multi-Agent Bot\n\n"
        "Commands:\n"
        "/start - Show this help\n"
        "/status - Bot status and account info\n"
        "/config - View current configuration\n"
        "/setparam <key> <value> - Change a parameter\n"
        "/profit - View trading performance\n"
        "/analyze - Trigger LLM analysis now\n"
        "/errors - View recent errors\n"
        "/check - Check pending recommendations\n"
        "/ask <question> - Ask the AI anything about trading\n"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show bot and system status."""
    if not _is_authorized(update):
        return

    suggestion = load_suggestions()
    pending = "Yes - awaiting your approval" if suggestion else "None"

    try:
        config = load_config()
        testnet = config["executor"]["binance"].get("testnet", True)
        mode = "TESTNET" if testnet else "MAINNET"
    except Exception:
        mode = "Unknown"

    # Check error count
    error_count = 0
    if ERRORS_LOG.exists():
        try:
            with open(ERRORS_LOG, "r") as f:
                error_count = sum(1 for _ in f)
        except Exception:
            pass

    await update.message.reply_text(
        f"Bot Status\n\n"
        f"Mode: {mode}\n"
        f"Pending recommendation: {pending}\n"
        f"Total errors logged: {error_count}\n"
    )


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /config command - display current configuration."""
    if not _is_authorized(update):
        return

    try:
        config = load_config()
        exec_cfg = config.get("executor", {})
        strat = exec_cfg.get("strategy", {})
        risk = exec_cfg.get("risk", {})
        binance = exec_cfg.get("binance", {})

        lines = [
            "Current Configuration",
            "",
            "Binance:",
            f"  testnet: {binance.get('testnet', True)}",
            f"  leverage: {binance.get('futures_leverage', 10)}x",
            f"  margin_mode: {binance.get('margin_mode', 'ISOLATED')}",
            "",
            "Strategy:",
            f"  min_funding_rate: {strat.get('min_funding_rate', -1.0)}%",
            f"  max_concurrent_pairs: {strat.get('max_concurrent_pairs', 3)}",
            f"  margin_per_trade_usd: ${strat.get('margin_per_trade_usd', 10)}",
            f"  entry_window_seconds: {strat.get('entry_window_seconds', 10)}",
            f"  exit_window_seconds: {strat.get('exit_window_seconds', 5)}",
            "",
            "Risk Management:",
            f"  max_daily_loss_usd: ${risk.get('max_daily_loss_usd', 5)}",
            f"  max_consecutive_losses: {risk.get('max_consecutive_losses', 3)}",
            f"  stop_loss_percent: {risk.get('stop_loss_percent', 2.0)}%",
            f"  pause_on_error: {risk.get('pause_on_error', True)}",
            "",
            "Use /setparam <key> <value> to change parameters.",
            "Example: /setparam min_funding_rate -1.5",
        ]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Failed to load config: {e}")


async def cmd_setparam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setparam <key> <value> - change a configuration parameter."""
    if not _is_authorized(update):
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /setparam <key> <value>\n\n"
            "Available keys:\n"
            "  min_funding_rate (float, e.g. -1.5)\n"
            "  margin_per_trade_usd (float, 1-30)\n"
            "  max_concurrent_pairs (int, 1-10)\n"
            "  entry_window_seconds (int)\n"
            "  exit_window_seconds (int)\n"
            "  stop_loss_percent (float)\n"
            "  max_daily_loss_usd (float)\n"
            "  max_consecutive_losses (int)\n"
        )
        return

    key = args[0].strip()
    raw_value = " ".join(args[1:]).strip()

    # Map keys to config paths
    strategy_keys = {
        "min_funding_rate", "margin_per_trade_usd", "max_concurrent_pairs",
        "entry_window_seconds", "exit_window_seconds",
    }
    risk_keys = {
        "stop_loss_percent", "max_daily_loss_usd", "max_consecutive_losses",
    }

    if key not in strategy_keys and key not in risk_keys:
        await update.message.reply_text(f"Unknown parameter: {key}")
        return

    # Parse value
    try:
        if key in ("max_concurrent_pairs", "entry_window_seconds",
                    "exit_window_seconds", "max_consecutive_losses"):
            value = int(raw_value)
        else:
            value = float(raw_value)
    except ValueError:
        await update.message.reply_text(f"Invalid value: {raw_value}")
        return

    # Validate ranges
    if key == "margin_per_trade_usd" and (value <= 0 or value > 30):
        await update.message.reply_text("margin_per_trade_usd must be between 0 and 30")
        return
    if key == "max_concurrent_pairs" and (value < 1 or value > 10):
        await update.message.reply_text("max_concurrent_pairs must be between 1 and 10")
        return

    try:
        config = load_config()
        if key in strategy_keys:
            config["executor"]["strategy"][key] = value
        else:
            config["executor"]["risk"][key] = value

        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        reload_executor()
        await update.message.reply_text(
            f"Parameter updated: {key} = {value}\nExecutor will reload."
        )
    except Exception as e:
        await update.message.reply_text(f"Failed to update: {e}")


async def cmd_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /profit command - show trading performance stats."""
    if not _is_authorized(update):
        return

    trades = read_trades(hours=24)
    stats = aggregate(trades)

    if stats["total_trades"] == 0:
        await update.message.reply_text("No trades in the last 24 hours.")
        return

    # Also get 7-day stats
    trades_7d = read_trades(hours=168)
    stats_7d = aggregate(trades_7d)

    lines = [
        "Trading Performance",
        "",
        "Last 24 hours:",
        f"  Total trades: {stats['total_trades']}",
        f"  Wins: {stats['win_count']}",
        f"  Win rate: {stats['win_rate']:.1f}%",
        f"  Avg profit: ${stats['avg_profit_net']:.4f}",
        f"  Total profit: ${stats['total_profit']:.4f}",
        f"  Errors: {stats['error_count']}",
        "",
        "Last 7 days:",
        f"  Total trades: {stats_7d['total_trades']}",
        f"  Win rate: {stats_7d['win_rate']:.1f}%",
        f"  Total profit: ${stats_7d['total_profit']:.4f}",
    ]

    await update.message.reply_text("\n".join(lines))


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command - trigger LLM analysis on demand."""
    if not _is_authorized(update):
        return

    await update.message.reply_text("Running analysis... This may take a moment.")

    try:
        from agents.analyst.openclaw_skill import run as analyst_run
        result = analyst_run()

        if "error" in result:
            await update.message.reply_text(f"Analysis error: {result['error']}")
            return

        if result.get("action") == "OK" and result.get("reason") == "No trades to analyze":
            await update.message.reply_text("No trades to analyze yet.")
            return

        # Load and present the suggestion
        suggestion = load_suggestions()
        if suggestion:
            global pending_suggestion
            pending_suggestion = suggestion
            msg = format_suggestion_message(suggestion)
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(
                f"Analysis complete:\n"
                f"Action: {result.get('action', '?')}\n"
                f"Reason: {result.get('reason', '?')}"
            )
    except Exception as e:
        await update.message.reply_text(f"Analysis failed: {e}")


async def cmd_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /errors command - show recent errors."""
    if not _is_authorized(update):
        return

    if not ERRORS_LOG.exists():
        await update.message.reply_text("No errors logged yet.")
        return

    errors = []
    try:
        with open(ERRORS_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        errors.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        await update.message.reply_text(f"Failed to read errors: {e}")
        return

    if not errors:
        await update.message.reply_text("No errors logged yet.")
        return

    # Show last 5 errors
    recent = errors[-5:][::-1]
    lines = [f"Recent Errors ({len(errors)} total)", ""]

    for err in recent:
        ts = err.get("timestamp", "?")
        if "T" in ts:
            ts = ts.split("T")[1][:8]
        lines.append(
            f"[{err.get('level', '?')}] {ts}\n"
            f"  {err.get('source', '?')}: {err.get('message', '?')[:80]}"
        )
        lines.append("")

    await update.message.reply_text("\n".join(lines))


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - check for pending recommendations."""
    if not _is_authorized(update):
        return

    global pending_suggestion

    suggestion = load_suggestions()
    if suggestion:
        pending_suggestion = suggestion
        msg = format_suggestion_message(suggestion)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No new recommendations.")


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ask <question> - chat with the AI about trading strategy."""
    if not _is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /ask <your question>")
        return

    question = " ".join(context.args)

    # Build context from current performance and config
    trades = read_trades(hours=24)
    stats = aggregate(trades)

    try:
        config = load_config()
        strat = config.get("executor", {}).get("strategy", {})
        risk_cfg = config.get("executor", {}).get("risk", {})
    except Exception:
        strat = {}
        risk_cfg = {}

    context_info = (
        f"Current trading stats (24h): {json.dumps(stats)}\n"
        f"Strategy config: {json.dumps(strat)}\n"
        f"Risk config: {json.dumps(risk_cfg)}"
    )

    system_prompt = (
        "You are a helpful crypto trading assistant specializing in funding rate arbitrage "
        "on Binance Futures. You help the user understand their trading performance, "
        "suggest parameter adjustments, and answer questions about the strategy.\n"
        "Be concise. Answer in the same language as the user's question.\n"
        "If asked to change parameters, tell them to use the /setparam command.\n\n"
        f"Current system context:\n{context_info}"
    )

    await update.message.reply_text("Thinking...")

    try:
        analyst_cfg = config.get("analyst", {}).get("openrouter", {})
        model = analyst_cfg.get("model", "qwen/qwen3.6-plus-preview:free")

        response = call_qwen(
            system_prompt=system_prompt,
            user_prompt=question,
            model=model,
            temperature=0.7,
        )

        if response:
            # Truncate if too long for Telegram
            if len(response) > 4000:
                response = response[:3997] + "..."
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("AI did not return a response. Check your OpenRouter API key.")
    except Exception as e:
        await update.message.reply_text(f"AI query failed: {e}")


# ---------------------------------------------------------------------------
# Text message handler (yes/no approval)
# ---------------------------------------------------------------------------

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text replies - process yes/no for approvals."""
    if not _is_authorized(update):
        return

    global pending_suggestion

    text = update.message.text.strip().lower()

    if text not in ("yes", "no"):
        # Not a yes/no - ignore (user can use /ask for AI conversation)
        return

    if pending_suggestion is None:
        pending_suggestion = load_suggestions()

    if pending_suggestion is None:
        await update.message.reply_text("No pending recommendation to approve/reject.")
        return

    if text == "yes":
        suggestions = pending_suggestion.get("suggestions", {})
        success = update_config(suggestions)
        if success:
            reload_executor()
            save_suggestion_status(approved=True)
            await update.message.reply_text("Parameters updated and executor reloaded.")
        else:
            await update.message.reply_text("Failed to update config. Check logs.")
    else:
        save_suggestion_status(approved=False)
        await update.message.reply_text("Recommendation rejected.")

    pending_suggestion = None


# ---------------------------------------------------------------------------
# Periodic jobs
# ---------------------------------------------------------------------------

async def check_suggestions_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job: check for new suggestions and notify user."""
    global pending_suggestion

    suggestion = load_suggestions()
    if suggestion and suggestion != pending_suggestion:
        pending_suggestion = suggestion
        msg = format_suggestion_message(suggestion)
        try:
            await context.bot.send_message(chat_id=CHAT_ID, text=msg)
            logger.info("Sent suggestion notification to chat %s", CHAT_ID)
        except Exception as e:
            logger.error("Failed to send suggestion notification: %s", e)


async def check_errors_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job: check for new critical errors and notify user."""
    if not ERRORS_LOG.exists():
        return

    # Read last error
    try:
        last_error = None
        with open(ERRORS_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        last_error = json.loads(line)
                    except json.JSONDecodeError:
                        pass

        if not last_error:
            return

        # Only notify for recent critical errors (last 5 minutes)
        ts = last_error.get("timestamp", "")
        if ts:
            try:
                err_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - err_time).total_seconds()
                if age > 300:  # older than 5 minutes
                    return
            except ValueError:
                return

        if last_error.get("level") in ("ERROR", "CRITICAL"):
            # Check if we already notified (use a simple state marker)
            state_key = f"last_notified_error_{last_error.get('timestamp', '')}"
            if context.bot_data.get(state_key):
                return
            context.bot_data[state_key] = True

            msg = (
                f"Error Alert\n\n"
                f"Level: {last_error.get('level')}\n"
                f"Source: {last_error.get('source', '?')}\n"
                f"Message: {last_error.get('message', '?')[:200]}\n"
                f"Time: {last_error.get('timestamp', '?')}"
            )
            await context.bot.send_message(chat_id=CHAT_ID, text=msg)

    except Exception as e:
        logger.error("Error check job failed: %s", e)


# ---------------------------------------------------------------------------
# Error notification callback (for executor to call)
# ---------------------------------------------------------------------------

def send_error_notification_sync(message: str):
    """Synchronous callback for error notifications from the executor.

    This writes to a notification queue file that the periodic job picks up.

    Args:
        message: Error message string.
    """
    notify_file = PROJECT_ROOT / "shared" / "data" / "error_notify.json"
    try:
        os.makedirs(notify_file.parent, exist_ok=True)
        data = {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(notify_file, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error("Failed to write error notification: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Start the Telegram bot."""
    global _bot_app

    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    if not CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    _bot_app = app

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("setparam", cmd_setparam))
    app.add_handler(CommandHandler("profit", cmd_profit))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("errors", cmd_errors))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("ask", cmd_ask))

    # Text reply handler for yes/no
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))

    # Periodic jobs
    job_queue = app.job_queue
    if job_queue:
        # Check for new suggestions every 30 minutes
        job_queue.run_repeating(
            check_suggestions_job,
            interval=1800,
            first=10,
        )
        # Check for new errors every 2 minutes
        job_queue.run_repeating(
            check_errors_job,
            interval=120,
            first=30,
        )

    logger.info("Telegram bot starting with AI conversation support...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
