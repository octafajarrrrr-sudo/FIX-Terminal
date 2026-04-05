"""Trade logger module.

Writes structured JSON trade records to the shared trades.log file,
one JSON object per line for easy parsing.
"""

import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "logs")
LOG_FILE = os.path.join(LOG_DIR, "trades.log")


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
