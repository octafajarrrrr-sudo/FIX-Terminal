from __future__ import annotations

"""Trade log reader and aggregator.

Reads the JSON-lines trades.log file and computes aggregate statistics
for the LLM analyst to evaluate.
"""

import json
import os
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

LOG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "shared", "logs", "trades.log"
)


def read_trades(hours: int = 24) -> list[dict]:
    """Read trades from the log file within the last N hours.

    Args:
        hours: Number of hours to look back.

    Returns:
        List of trade dicts.
    """
    if not os.path.exists(LOG_FILE):
        logger.warning("trades.log not found at %s", LOG_FILE)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    trades = []

    try:
        with open(LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    trade = json.loads(line)
                    ts = trade.get("timestamp", "")
                    if ts:
                        trade_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if trade_time >= cutoff:
                            trades.append(trade)
                    else:
                        trades.append(trade)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning("Skipping malformed log line: %s", e)
    except Exception as e:
        logger.error("Failed to read trades.log: %s", e)

    logger.info("Read %d trades from last %d hours", len(trades), hours)
    return trades


def aggregate(trades: list[dict]) -> dict:
    """Compute aggregate statistics from a list of trades.

    Args:
        trades: List of trade dicts with at least 'profit_net' and 'status' keys.

    Returns:
        Dict with keys: total_trades, win_count, win_rate, avg_profit_net,
        total_profit, error_count.
    """
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_count": 0,
            "win_rate": 0.0,
            "avg_profit_net": 0.0,
            "total_profit": 0.0,
            "error_count": 0,
        }

    win_count = sum(1 for t in trades if t.get("profit_net", 0) > 0)
    error_count = sum(1 for t in trades if t.get("status") == "ERROR")
    total_profit = sum(t.get("profit_net", 0) for t in trades)
    avg_profit_net = total_profit / total_trades

    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

    stats = {
        "total_trades": total_trades,
        "win_count": win_count,
        "win_rate": round(win_rate, 2),
        "avg_profit_net": round(avg_profit_net, 6),
        "total_profit": round(total_profit, 6),
        "error_count": error_count,
    }

    logger.info("Aggregated stats: %s", stats)
    return stats
