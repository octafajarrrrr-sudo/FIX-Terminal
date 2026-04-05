"""JSON response parser and validator for LLM output.

Extracts and validates JSON from the LLM response, handling cases
where the model wraps JSON in markdown code blocks.
"""

from __future__ import annotations

import json
import re
import logging

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"PAUSE", "ADJUST", "OK"}


def parse_llm_response(response_text: str) -> dict | None:
    """Parse and validate JSON from the LLM response.

    Handles responses that may be wrapped in markdown code fences.

    Args:
        response_text: Raw text from the LLM.

    Returns:
        Parsed and validated dict, or None if invalid.
    """
    if not response_text:
        logger.warning("Empty LLM response")
        return None

    text = response_text.strip()

    # Try to extract JSON from markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        logger.debug("Raw response: %s", response_text[:500])
        return None

    return validate_suggestion(data)


def validate_suggestion(data: dict) -> dict | None:
    """Validate the structure of a suggestion dict.

    Args:
        data: Parsed JSON dict from the LLM.

    Returns:
        Validated dict or None if validation fails.
    """
    if not isinstance(data, dict):
        logger.error("LLM response is not a dict")
        return None

    action = data.get("action")
    if action not in VALID_ACTIONS:
        logger.error("Invalid action '%s', expected one of %s", action, VALID_ACTIONS)
        return None

    if "reason" not in data:
        logger.warning("Missing 'reason' field, adding placeholder")
        data["reason"] = "No reason provided"

    if "suggestions" not in data:
        data["suggestions"] = {}

    suggestions = data["suggestions"]
    if not isinstance(suggestions, dict):
        logger.error("'suggestions' is not a dict")
        return None

    # Validate suggestion values
    if suggestions.get("min_funding_rate") is not None:
        try:
            suggestions["min_funding_rate"] = float(suggestions["min_funding_rate"])
        except (TypeError, ValueError):
            logger.warning("Invalid min_funding_rate, setting to null")
            suggestions["min_funding_rate"] = None

    if suggestions.get("margin_per_trade_usd") is not None:
        try:
            val = float(suggestions["margin_per_trade_usd"])
            if val <= 0 or val > 30:
                logger.warning("margin_per_trade_usd out of range: %.2f", val)
                suggestions["margin_per_trade_usd"] = None
            else:
                suggestions["margin_per_trade_usd"] = val
        except (TypeError, ValueError):
            suggestions["margin_per_trade_usd"] = None

    if suggestions.get("max_concurrent_pairs") is not None:
        try:
            val = int(suggestions["max_concurrent_pairs"])
            if val < 1 or val > 10:
                suggestions["max_concurrent_pairs"] = None
            else:
                suggestions["max_concurrent_pairs"] = val
        except (TypeError, ValueError):
            suggestions["max_concurrent_pairs"] = None

    logger.info("Validated suggestion: action=%s", data["action"])
    return data
