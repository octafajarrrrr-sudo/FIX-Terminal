"""Telegram approval bot.

Runs as a long-polling Telegram bot that:
1. Periodically checks for new suggestions from the LLM analyst.
2. Sends recommendations to the user for approval.
3. Processes yes/no replies to update config or reject changes.
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

from agents.approval.config_updater import update_config, reload_executor

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_bot")

SUGGESTIONS_PATH = PROJECT_ROOT / "shared" / "data" / "suggestions.json"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# In-memory state for pending approval
pending_suggestion = None


def load_suggestions() -> dict | None:
    """Load suggestions.json if it contains an unapproved recommendation.

    Returns:
        Suggestion dict if pending, None otherwise.
    """
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
    """Update the approved field in suggestions.json.

    Args:
        approved: True if user approved, False if rejected.
    """
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
    """Format a suggestion dict into a human-readable Telegram message.

    Args:
        suggestion: The suggestion dict from the analyst.

    Returns:
        Formatted message string.
    """
    action = suggestion.get("action", "UNKNOWN")
    reason = suggestion.get("reason", "No reason provided")
    changes = suggestion.get("suggestions", {})
    stats = suggestion.get("stats", {})

    lines = [
        f"📊 LLM Analyst Recommendation",
        f"",
        f"Action: {action}",
        f"Reason: {reason}",
        f"",
        f"📈 Performance (24h):",
        f"  Trades: {stats.get('total_trades', 0)}",
        f"  Win rate: {stats.get('win_rate', 0):.1f}%",
        f"  Total profit: ${stats.get('total_profit', 0):.4f}",
        f"",
    ]

    if changes:
        lines.append("🔧 Proposed Changes:")
        for key, val in changes.items():
            if val is not None:
                lines.append(f"  {key}: {val}")
        lines.append("")

    lines.append("Reply 'yes' to approve or 'no' to reject.")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Funding Fee Multi-Agent Bot\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/status - Check current bot status\n"
        "/check - Check for pending recommendations\n"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    suggestion = load_suggestions()
    if suggestion:
        status = "Pending recommendation awaiting approval"
    else:
        status = "No pending recommendations"

    await update.message.reply_text(f"Status: {status}")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - manually check for new suggestions."""
    global pending_suggestion

    suggestion = load_suggestions()
    if suggestion:
        pending_suggestion = suggestion
        msg = format_suggestion_message(suggestion)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No new recommendations.")


async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle yes/no text replies for approval."""
    global pending_suggestion

    if str(update.effective_chat.id) != str(CHAT_ID):
        return

    text = update.message.text.strip().lower()

    if text not in ("yes", "no"):
        return

    if pending_suggestion is None:
        # Try loading from file
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
            await update.message.reply_text("✅ Parameters updated and executor reloaded.")
        else:
            await update.message.reply_text("❌ Failed to update config. Check logs.")
    else:
        save_suggestion_status(approved=False)
        await update.message.reply_text("❌ Recommendation rejected.")

    pending_suggestion = None


async def check_suggestions_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job to check for new suggestions and notify the user."""
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


def main():
    """Start the Telegram bot."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    if not CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check", cmd_check))

    # Text reply handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))

    # Periodic job to check suggestions (every 30 minutes)
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_suggestions_job,
            interval=1800,  # 30 minutes
            first=10,       # first check after 10 seconds
        )

    logger.info("Telegram bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
