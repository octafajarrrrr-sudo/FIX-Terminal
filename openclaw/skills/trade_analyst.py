"""OpenClaw skill wrapper for the trade analyst.

This file is a thin wrapper that imports and delegates to the actual
analyst implementation in agents/analyst/openclaw_skill.py.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.analyst.openclaw_skill import run


def execute(params: dict = None) -> dict:
    """OpenClaw skill entry point.

    Args:
        params: Optional parameters dict.

    Returns:
        Result dict from the analyst.
    """
    return run(params)


if __name__ == "__main__":
    import json
    result = execute()
    print(json.dumps(result, indent=2))
