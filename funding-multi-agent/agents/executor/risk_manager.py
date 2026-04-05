"""Risk management module for the executor bot.

Tracks daily losses, consecutive losses, and stop-loss triggers.
Persists state to a JSON file so it survives restarts.
"""

import json
import os
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "shared", "data", "risk_state.json"
)


class RiskManager:
    """Manages trading risk: daily loss limits, consecutive losses, pause logic."""

    def __init__(self, config: dict):
        """Initialize the risk manager.

        Args:
            config: Risk config dict with keys max_daily_loss_usd,
                    max_consecutive_losses, stop_loss_percent, pause_on_error.
        """
        self.max_daily_loss = config.get("max_daily_loss_usd", 5.0)
        self.max_consecutive_losses = config.get("max_consecutive_losses", 3)
        self.stop_loss_percent = config.get("stop_loss_percent", 2.0)
        self.pause_on_error = config.get("pause_on_error", True)

        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.paused = False
        self.pause_until = 0
        self.last_reset_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        self._load_state()

    def _load_state(self):
        """Load persisted risk state from disk."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                self.daily_loss = state.get("daily_loss", 0.0)
                self.consecutive_losses = state.get("consecutive_losses", 0)
                self.paused = state.get("paused", False)
                self.pause_until = state.get("pause_until", 0)
                self.last_reset_date = state.get(
                    "last_reset_date",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                )
                logger.info("Loaded risk state: daily_loss=%.4f, consecutive=%d", self.daily_loss, self.consecutive_losses)
        except Exception as e:
            logger.error("Failed to load risk state: %s", e)

    def _save_state(self):
        """Persist risk state to disk."""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            state = {
                "daily_loss": self.daily_loss,
                "consecutive_losses": self.consecutive_losses,
                "paused": self.paused,
                "pause_until": self.pause_until,
                "last_reset_date": self.last_reset_date,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error("Failed to save risk state: %s", e)

    def check_daily_reset(self):
        """Reset daily counters if the UTC date has changed."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.last_reset_date:
            logger.info("Daily reset: %s -> %s", self.last_reset_date, today)
            self.daily_loss = 0.0
            self.last_reset_date = today
            self.paused = False
            self._save_state()

    def update_daily_loss(self, profit_loss: float):
        """Update the running daily loss total.

        Args:
            profit_loss: The P&L of the latest trade (negative = loss).
        """
        if profit_loss < 0:
            self.daily_loss += abs(profit_loss)
            self.consecutive_losses += 1
            logger.warning(
                "Loss recorded: %.4f, daily total: %.4f, consecutive: %d",
                profit_loss, self.daily_loss, self.consecutive_losses,
            )
        else:
            self.consecutive_losses = 0

        self._save_state()

    def check_daily_loss(self) -> bool:
        """Check whether the daily loss limit has been exceeded.

        Returns:
            True if daily loss >= max_daily_loss.
        """
        exceeded = self.daily_loss >= self.max_daily_loss
        if exceeded:
            logger.warning("Daily loss limit reached: %.4f >= %.4f", self.daily_loss, self.max_daily_loss)
        return exceeded

    def check_consecutive_losses(self) -> bool:
        """Check whether the consecutive loss limit has been reached.

        Returns:
            True if consecutive losses >= max_consecutive_losses.
        """
        exceeded = self.consecutive_losses >= self.max_consecutive_losses
        if exceeded:
            logger.warning("Consecutive loss limit: %d >= %d", self.consecutive_losses, self.max_consecutive_losses)
        return exceeded

    def stop_loss_triggered(
        self, entry_price: float, current_price: float, side: str = "long"
    ) -> bool:
        """Check if stop loss has been triggered.

        Args:
            entry_price: The entry price of the position.
            current_price: Current mark price.
            side: 'long' or 'short'.

        Returns:
            True if price moved against the position beyond stop_loss_percent.
        """
        if entry_price <= 0:
            return False

        if side == "long":
            pct_change = ((current_price - entry_price) / entry_price) * 100
            triggered = pct_change <= -self.stop_loss_percent
        else:
            pct_change = ((entry_price - current_price) / entry_price) * 100
            triggered = pct_change <= -self.stop_loss_percent

        if triggered:
            logger.warning(
                "Stop loss triggered: entry=%.4f, current=%.4f, change=%.2f%%",
                entry_price, current_price, pct_change,
            )
        return triggered

    def pause(self, duration_seconds: int = 3600):
        """Pause trading for a specified duration.

        Args:
            duration_seconds: How long to pause (default 60 minutes).
        """
        self.paused = True
        self.pause_until = int(time.time()) + duration_seconds
        logger.warning("Bot paused for %d seconds", duration_seconds)
        self._save_state()

    def is_paused(self) -> bool:
        """Check if the bot is currently paused.

        Returns:
            True if paused and pause duration has not expired.
        """
        if not self.paused:
            return False

        if time.time() >= self.pause_until:
            self.paused = False
            self.pause_until = 0
            self._save_state()
            logger.info("Pause expired, resuming trading")
            return False

        return True
