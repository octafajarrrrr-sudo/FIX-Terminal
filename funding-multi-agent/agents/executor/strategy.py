"""Trading strategy logic for funding rate arbitrage.

Handles pair filtering, sorting, selection, quantity calculation,
and entry timing decisions.
"""

from __future__ import annotations

import time
import logging

logger = logging.getLogger(__name__)


def filter_pairs(funding_rates: list[dict], min_rate: float) -> list[dict]:
    """Filter pairs where funding_rate <= min_rate (negative rates).

    Args:
        funding_rates: List of dicts with 'funding_rate' key (in percentage).
        min_rate: Minimum (most negative) funding rate threshold.

    Returns:
        Filtered list of pairs meeting the criteria.
    """
    filtered = [p for p in funding_rates if p["funding_rate"] <= min_rate]
    logger.info("Filtered %d pairs with rate <= %.2f%%", len(filtered), min_rate)
    return filtered


def sort_by_rate(pairs: list[dict], ascending: bool = True) -> list[dict]:
    """Sort pairs by funding rate. Most negative first when ascending=True.

    Args:
        pairs: List of pair dicts.
        ascending: If True, most negative rates come first.

    Returns:
        Sorted list.
    """
    return sorted(pairs, key=lambda p: p["funding_rate"], reverse=not ascending)


def select_top_pairs(pairs: list[dict], max_count: int = 3) -> list[dict]:
    """Select the top N pairs after sorting.

    Args:
        pairs: Pre-sorted list of pair dicts.
        max_count: Maximum number of pairs to return.

    Returns:
        Top N pairs.
    """
    selected = pairs[:max_count]
    if selected:
        symbols = [p["symbol"] for p in selected]
        logger.info("Selected top %d pairs: %s", len(selected), symbols)
    return selected


def calculate_quantity(margin_usd: float, leverage: int, mark_price: float) -> float:
    """Calculate order quantity based on margin, leverage, and price.

    Args:
        margin_usd: USD margin allocated per trade.
        leverage: Leverage multiplier.
        mark_price: Current mark price of the asset.

    Returns:
        Order quantity. Returns 0.0 if mark_price is zero.
    """
    if mark_price <= 0:
        logger.error("Invalid mark_price: %f", mark_price)
        return 0.0
    quantity = (margin_usd * leverage) / mark_price
    logger.info(
        "Calculated quantity: margin=$%.2f, leverage=%dx, price=%.4f -> qty=%.6f",
        margin_usd, leverage, mark_price, quantity,
    )
    return quantity


def entry_timing(next_funding_time_ms: int, entry_window_sec: int = 10) -> bool:
    """Check if it is time to enter a position before funding settlement.

    Args:
        next_funding_time_ms: Next funding timestamp in milliseconds.
        entry_window_sec: Seconds before settlement to enter.

    Returns:
        True if current time is within the entry window.
    """
    now_ms = int(time.time() * 1000)
    threshold_ms = next_funding_time_ms - (entry_window_sec * 1000)

    if now_ms >= threshold_ms and now_ms < next_funding_time_ms:
        logger.info("Entry window open: %d ms until settlement", next_funding_time_ms - now_ms)
        return True
    return False
