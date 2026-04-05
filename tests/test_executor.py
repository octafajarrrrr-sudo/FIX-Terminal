"""Tests for the executor agent modules."""

import sys
import os
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.executor import strategy
from agents.executor.risk_manager import RiskManager
from agents.executor.logger import log_trade
from tests.mock_binance import MockBinanceClient


# ---------------------------------------------------------------------------
# Strategy tests
# ---------------------------------------------------------------------------

class TestStrategy:
    """Tests for strategy module functions."""

    def setup_method(self):
        self.client = MockBinanceClient()
        self.rates = self.client.get_funding_rates()

    def test_filter_pairs_negative_rate(self):
        """Should filter pairs with rate <= threshold."""
        filtered = strategy.filter_pairs(self.rates, -1.0)
        symbols = [p["symbol"] for p in filtered]
        assert "ETH/USDT:USDT" in symbols  # -2.0
        assert "BTC/USDT:USDT" in symbols  # -1.5
        assert "DOGE/USDT:USDT" in symbols  # -1.2
        assert "SOL/USDT:USDT" not in symbols  # -0.5
        assert "ADA/USDT:USDT" not in symbols  # +0.01

    def test_filter_pairs_stricter_threshold(self):
        """Stricter threshold should return fewer pairs."""
        filtered = strategy.filter_pairs(self.rates, -1.5)
        symbols = [p["symbol"] for p in filtered]
        assert "ETH/USDT:USDT" in symbols
        assert "BTC/USDT:USDT" in symbols
        assert "DOGE/USDT:USDT" not in symbols

    def test_sort_by_rate_ascending(self):
        """Most negative rate should be first."""
        filtered = strategy.filter_pairs(self.rates, -1.0)
        sorted_pairs = strategy.sort_by_rate(filtered, ascending=True)
        rates = [p["funding_rate"] for p in sorted_pairs]
        assert rates == sorted(rates)

    def test_select_top_pairs(self):
        """Should return at most max_count pairs."""
        filtered = strategy.filter_pairs(self.rates, -1.0)
        sorted_pairs = strategy.sort_by_rate(filtered, ascending=True)
        top = strategy.select_top_pairs(sorted_pairs, max_count=2)
        assert len(top) == 2
        assert top[0]["funding_rate"] <= top[1]["funding_rate"]

    def test_calculate_quantity(self):
        """Quantity = (margin * leverage) / price."""
        qty = strategy.calculate_quantity(10, 10, 50000)
        assert abs(qty - 0.002) < 1e-6

    def test_calculate_quantity_zero_price(self):
        """Should return 0 for zero price."""
        qty = strategy.calculate_quantity(10, 10, 0)
        assert qty == 0.0

    def test_entry_timing_within_window(self):
        """Should return True when within entry window."""
        now_ms = int(time.time() * 1000)
        next_funding = now_ms + 5000  # 5 seconds from now
        assert strategy.entry_timing(next_funding, entry_window_sec=10) is True

    def test_entry_timing_outside_window(self):
        """Should return False when outside entry window."""
        now_ms = int(time.time() * 1000)
        next_funding = now_ms + 60000  # 60 seconds from now
        assert strategy.entry_timing(next_funding, entry_window_sec=10) is False

    def test_entry_timing_past_settlement(self):
        """Should return False when settlement has passed."""
        now_ms = int(time.time() * 1000)
        next_funding = now_ms - 5000  # 5 seconds ago
        assert strategy.entry_timing(next_funding, entry_window_sec=10) is False


# ---------------------------------------------------------------------------
# Risk Manager tests
# ---------------------------------------------------------------------------

class TestRiskManager:
    """Tests for the RiskManager class."""

    def setup_method(self):
        self.config = {
            "max_daily_loss_usd": 5.0,
            "max_consecutive_losses": 3,
            "stop_loss_percent": 2.0,
            "pause_on_error": True,
        }
        # Use a temp state file
        self.tmp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.tmp_dir, "risk_state.json")

    def _make_rm(self):
        with patch("agents.executor.risk_manager.STATE_FILE", self.state_file):
            return RiskManager(self.config)

    def test_initial_state(self):
        rm = self._make_rm()
        assert rm.daily_loss == 0.0
        assert rm.consecutive_losses == 0
        assert rm.paused is False

    def test_update_daily_loss_on_loss(self):
        rm = self._make_rm()
        rm.update_daily_loss(-1.5)
        assert rm.daily_loss == 1.5
        assert rm.consecutive_losses == 1

    def test_update_daily_loss_on_win(self):
        rm = self._make_rm()
        rm.update_daily_loss(-1.0)
        rm.update_daily_loss(0.5)
        assert rm.consecutive_losses == 0

    def test_check_daily_loss_exceeded(self):
        rm = self._make_rm()
        rm.daily_loss = 5.5
        assert rm.check_daily_loss() is True

    def test_check_daily_loss_not_exceeded(self):
        rm = self._make_rm()
        rm.daily_loss = 3.0
        assert rm.check_daily_loss() is False

    def test_check_consecutive_losses(self):
        rm = self._make_rm()
        rm.consecutive_losses = 3
        assert rm.check_consecutive_losses() is True

    def test_stop_loss_triggered_long(self):
        rm = self._make_rm()
        # Price dropped 3% from entry
        triggered = rm.stop_loss_triggered(100.0, 97.0, "long")
        assert triggered is True

    def test_stop_loss_not_triggered_long(self):
        rm = self._make_rm()
        # Price dropped only 1%
        triggered = rm.stop_loss_triggered(100.0, 99.0, "long")
        assert triggered is False

    def test_pause_and_is_paused(self):
        rm = self._make_rm()
        rm.pause(duration_seconds=5)
        assert rm.is_paused() is True

    def test_pause_expires(self):
        rm = self._make_rm()
        rm.pause(duration_seconds=0)
        time.sleep(0.1)
        assert rm.is_paused() is False


# ---------------------------------------------------------------------------
# Logger tests
# ---------------------------------------------------------------------------

class TestLogger:
    """Tests for the trade logger."""

    def test_log_trade_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_file = os.path.join(tmp, "trades.log")
            with patch("agents.executor.logger.LOG_FILE", log_file), \
                 patch("agents.executor.logger.LOG_DIR", tmp):
                log_trade({
                    "symbol": "BTC/USDT:USDT",
                    "funding_rate": -1.5,
                    "profit_net": 0.15,
                    "status": "SUCCESS",
                })

            assert os.path.exists(log_file)
            with open(log_file) as f:
                data = json.loads(f.readline())
            assert data["symbol"] == "BTC/USDT:USDT"
            assert data["profit_net"] == 0.15
            assert "timestamp" in data


# ---------------------------------------------------------------------------
# MockBinanceClient tests
# ---------------------------------------------------------------------------

class TestMockBinanceClient:
    """Sanity checks for the mock client."""

    def test_get_funding_rates(self):
        client = MockBinanceClient()
        rates = client.get_funding_rates()
        assert len(rates) == 5
        assert all("symbol" in r for r in rates)

    def test_create_market_order(self):
        client = MockBinanceClient()
        order = client.create_market_order("BTC/USDT:USDT", "buy", 0.001)
        assert order["side"] == "buy"
        assert order["amount"] == 0.001
        assert len(client.orders) == 1
