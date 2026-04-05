"""Tests for the analyst agent modules."""

import sys
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.analyst.json_parser import parse_llm_response, validate_suggestion
from agents.analyst.log_reader import aggregate


# ---------------------------------------------------------------------------
# JSON Parser tests
# ---------------------------------------------------------------------------

class TestJsonParser:
    """Tests for LLM response parsing and validation."""

    def test_parse_valid_json(self):
        response = json.dumps({
            "action": "ADJUST",
            "reason": "Low win rate",
            "suggestions": {
                "min_funding_rate": -1.2,
                "margin_per_trade_usd": None,
                "max_concurrent_pairs": None,
                "entry_window_seconds": None,
            }
        })
        result = parse_llm_response(response)
        assert result is not None
        assert result["action"] == "ADJUST"

    def test_parse_json_in_code_block(self):
        response = '```json\n{"action": "OK", "reason": "All good", "suggestions": {}}\n```'
        result = parse_llm_response(response)
        assert result is not None
        assert result["action"] == "OK"

    def test_parse_invalid_json(self):
        result = parse_llm_response("This is not JSON at all")
        assert result is None

    def test_parse_empty_response(self):
        result = parse_llm_response("")
        assert result is None

    def test_validate_invalid_action(self):
        data = {"action": "INVALID", "reason": "test", "suggestions": {}}
        result = validate_suggestion(data)
        assert result is None

    def test_validate_pause_action(self):
        data = {"action": "PAUSE", "reason": "win rate too low", "suggestions": {}}
        result = validate_suggestion(data)
        assert result is not None
        assert result["action"] == "PAUSE"

    def test_validate_margin_out_of_range(self):
        data = {
            "action": "ADJUST",
            "reason": "test",
            "suggestions": {"margin_per_trade_usd": 50.0},
        }
        result = validate_suggestion(data)
        assert result is not None
        assert result["suggestions"]["margin_per_trade_usd"] is None

    def test_validate_concurrent_pairs_out_of_range(self):
        data = {
            "action": "ADJUST",
            "reason": "test",
            "suggestions": {"max_concurrent_pairs": 20},
        }
        result = validate_suggestion(data)
        assert result is not None
        assert result["suggestions"]["max_concurrent_pairs"] is None


# ---------------------------------------------------------------------------
# Log Reader aggregate tests
# ---------------------------------------------------------------------------

class TestLogAggregate:
    """Tests for the log aggregation function."""

    def test_aggregate_empty(self):
        stats = aggregate([])
        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0

    def test_aggregate_mixed_trades(self):
        trades = [
            {"profit_net": 0.5, "status": "SUCCESS"},
            {"profit_net": -0.2, "status": "SUCCESS"},
            {"profit_net": 0.3, "status": "SUCCESS"},
            {"profit_net": 0.0, "status": "ERROR"},
        ]
        stats = aggregate(trades)
        assert stats["total_trades"] == 4
        assert stats["win_count"] == 2
        assert stats["win_rate"] == 50.0
        assert stats["error_count"] == 1
        assert abs(stats["total_profit"] - 0.6) < 1e-6

    def test_aggregate_all_wins(self):
        trades = [
            {"profit_net": 0.1, "status": "SUCCESS"},
            {"profit_net": 0.2, "status": "SUCCESS"},
        ]
        stats = aggregate(trades)
        assert stats["win_rate"] == 100.0
        assert stats["win_count"] == 2
