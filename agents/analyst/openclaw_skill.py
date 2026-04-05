"""OpenClaw skill entrypoint for the trade analyst.

This module serves as the main entry point for the LLM analyst agent.
It reads trade logs, aggregates statistics, builds a prompt, calls the
Qwen model via OpenRouter, and saves recommendations to suggestions.json.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from agents.analyst.log_reader import read_trades, aggregate
from agents.analyst.openrouter_client import call_qwen
from agents.analyst.json_parser import parse_llm_response

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("analyst")

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "analyst_system.txt"
USER_TEMPLATE_PATH = PROJECT_ROOT / "config" / "prompts" / "analyst_user_template.txt"
RULES_PATH = PROJECT_ROOT / "config" / "rules.txt"
SUGGESTIONS_PATH = PROJECT_ROOT / "shared" / "data" / "suggestions.json"


def run(params: dict = None):
    """Run the analyst skill: aggregate logs, call LLM, save suggestions.

    Args:
        params: Optional dict with overrides (e.g. hours, model).

    Returns:
        Dict with the suggestion or error info.
    """
    params = params or {}
    hours = params.get("hours", 24)

    # Load config
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        return {"error": str(e)}

    analyst_cfg = config.get("analyst", {}).get("openrouter", {})
    exec_cfg = config.get("executor", {})
    strat_cfg = exec_cfg.get("strategy", {})

    model = analyst_cfg.get("model", "qwen/qwen3.6-plus-preview:free")
    temperature = analyst_cfg.get("temperature", 0.1)

    # Read and aggregate trades
    trades = read_trades(hours=hours)
    stats = aggregate(trades)

    if stats["total_trades"] == 0:
        logger.info("No trades in the last %d hours, skipping analysis", hours)
        return {"action": "OK", "reason": "No trades to analyze"}

    # Load prompts
    try:
        system_prompt = SYSTEM_PROMPT_PATH.read_text()
        user_template = USER_TEMPLATE_PATH.read_text()
        rules = RULES_PATH.read_text()
    except Exception as e:
        logger.error("Failed to load prompts: %s", e)
        return {"error": str(e)}

    # Append rules to system prompt
    full_system = system_prompt + "\n\nAdditional Rules:\n" + rules

    # Build user prompt
    user_prompt = user_template.format(
        total_trades=stats["total_trades"],
        win_count=stats["win_count"],
        win_rate=stats["win_rate"],
        avg_profit_net=stats["avg_profit_net"],
        total_profit=stats["total_profit"],
        error_count=stats["error_count"],
        min_funding_rate=strat_cfg.get("min_funding_rate", -1.0),
        margin_per_trade_usd=strat_cfg.get("margin_per_trade_usd", 10),
        max_concurrent_pairs=strat_cfg.get("max_concurrent_pairs", 3),
        entry_window_seconds=strat_cfg.get("entry_window_seconds", 10),
        futures_leverage=exec_cfg.get("binance", {}).get("futures_leverage", 10),
    )

    # Call LLM
    response_text = call_qwen(
        system_prompt=full_system,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
    )

    if not response_text:
        logger.error("Empty response from LLM")
        return {"error": "Empty LLM response"}

    # Parse and validate
    suggestion = parse_llm_response(response_text)
    if not suggestion:
        logger.error("Failed to parse LLM response")
        return {"error": "Invalid LLM response"}

    # Add metadata
    suggestion["generated_at"] = datetime.now(timezone.utc).isoformat()
    suggestion["approved"] = None  # pending approval
    suggestion["stats"] = stats

    # Save to suggestions.json
    try:
        os.makedirs(os.path.dirname(SUGGESTIONS_PATH), exist_ok=True)
        with open(SUGGESTIONS_PATH, "w") as f:
            json.dump(suggestion, f, indent=2)
        logger.info("Suggestion saved to %s", SUGGESTIONS_PATH)
    except Exception as e:
        logger.error("Failed to save suggestion: %s", e)
        return {"error": str(e)}

    return suggestion


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
