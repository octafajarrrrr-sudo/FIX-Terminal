"""Trade and error logger module.

Writes structured JSON trade records to shared/logs/trades.log and
error records to shared/logs/errors.log, one JSON object per line.
Also supports sending critical error notifications via a callback.
"""

import json
import os
import logging
import traceback
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "logs")
LOG_FILE = os.path.join(LOG_DIR, "trades.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")

# Optional callback for sending error notifications (e.g. to Telegram)
_error_notify_callback = None


def set_error_notify_callback(callback):
    """Set a callback function for critical error notifications.

    Args:
        callback: Callable that accepts a single string message argument.
    """
    global _error_notify_callback
    _error_notify_callback = callback
    logger.info("Error notification callback registered")


def log_trade(trade_data: dict):
    """Append a trade record to the trades.log file as a single JSON line.

    Args:
        trade_data: Dict containing trade details. A timestamp is added
                    automatically if not present. Expected keys:
                    symbol, funding_rate, profit_net, status, entry_price,
                    exit_price, quantity, fees.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    if "timestamp" not in trade_data:
        trade_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(trade_data) + "\n")
        logger.info("Logged trade: %s %s profit=%.4f",
                     trade_data.get("symbol", "?"),
                     trade_data.get("status", "?"),
                     trade_data.get("profit_net", 0))
    except Exception as e:
        logger.error("Failed to write trade log: %s", e)


def log_error(error_data: dict):
    """Append an error record to the errors.log file.

    Also triggers the error notification callback if set and the error
    is marked as critical.

    Args:
        error_data: Dict with error details. Expected keys:
                    source, message, level (INFO/WARNING/ERROR/CRITICAL),
                    details (optional traceback or context).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    if "timestamp" not in error_data:
        error_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    if "level" not in error_data:
        error_data["level"] = "ERROR"

    try:
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(json.dumps(error_data) + "\n")
        logger.error("Logged error: [%s] %s - %s",
                      error_data.get("level", "?"),
                      error_data.get("source", "?"),
                      error_data.get("message", "?"))
    except Exception as e:
        logger.error("Failed to write error log: %s", e)

    # Send notification for critical errors
    if error_data.get("level") in ("ERROR", "CRITICAL") and _error_notify_callback:
        try:
            msg = (
                f"[{error_data['level']}] {error_data.get('source', 'unknown')}\n"
                f"{error_data.get('message', 'No message')}"
            )
            _error_notify_callback(msg)
        except Exception as e:
            logger.error("Failed to send error notification: %s", e)


def log_exception(source: str, exc: Exception, critical: bool = False):
    """Convenience function to log an exception with full traceback.

    Args:
        source: Where the error originated (e.g. 'executor.main_loop').
        exc: The exception object.
        critical: If True, marks the error as CRITICAL level.
    """
    log_error({
        "source": source,
        "message": str(exc),
        "level": "CRITICAL" if critical else "ERROR",
        "exception_type": type(exc).__name__,
        "traceback": traceback.format_exc(),
    })


def get_recent_errors(count: int = 10) -> list:
    """Read the most recent error entries from errors.log.

    Args:
        count: Number of recent errors to return.

    Returns:
        List of error dicts, most recent first.
    """
    if not os.path.exists(ERROR_LOG_FILE):
        return []

    errors = []
    try:
        with open(ERROR_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        errors.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.error("Failed to read errors.log: %s", e)

    return errors[-count:][::-1]
