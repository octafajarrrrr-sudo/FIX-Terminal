"""Configuration updater module.

Reads, modifies, and writes config.yaml based on approved suggestions.
Also handles signaling the executor bot to reload its configuration.
"""

import os
import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
RELOAD_FLAG = PROJECT_ROOT / "agents" / "executor" / "reload.flag"


def update_config(suggestions: dict) -> bool:
    """Update config.yaml with the approved suggestion values.

    Only non-null values in suggestions are applied.

    Args:
        suggestions: Dict with optional keys: min_funding_rate,
                     margin_per_trade_usd, max_concurrent_pairs,
                     entry_window_seconds.

    Returns:
        True if config was updated successfully.
    """
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)

        strat = config.get("executor", {}).get("strategy", {})
        changed = False

        mapping = {
            "min_funding_rate": "min_funding_rate",
            "margin_per_trade_usd": "margin_per_trade_usd",
            "max_concurrent_pairs": "max_concurrent_pairs",
            "entry_window_seconds": "entry_window_seconds",
        }

        for suggestion_key, config_key in mapping.items():
            value = suggestions.get(suggestion_key)
            if value is not None:
                old_value = strat.get(config_key)
                strat[config_key] = value
                logger.info("Updated %s: %s -> %s", config_key, old_value, value)
                changed = True

        if changed:
            with open(CONFIG_PATH, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            logger.info("config.yaml updated successfully")
        else:
            logger.info("No changes to apply")

        return True

    except Exception as e:
        logger.error("Failed to update config: %s", e)
        return False


def reload_executor():
    """Signal the executor bot to reload configuration.

    Creates a reload.flag file that the executor watches for.
    """
    try:
        RELOAD_FLAG.parent.mkdir(parents=True, exist_ok=True)
        RELOAD_FLAG.touch()
        logger.info("Reload flag created at %s", RELOAD_FLAG)
    except Exception as e:
        logger.error("Failed to create reload flag: %s", e)
