"""OpenRouter API client for calling Qwen LLM.

Sends chat completion requests to the OpenRouter API and returns
the model's response content.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_qwen(
    system_prompt: str,
    user_prompt: str,
    model: str = "qwen/qwen3.6-plus-preview:free",
    temperature: float = 0.1,
    api_key: str = None,
) -> str:
    """Call the Qwen model via OpenRouter API.

    Args:
        system_prompt: System-level instructions for the model.
        user_prompt: User message containing the data to analyze.
        model: OpenRouter model identifier.
        temperature: Sampling temperature (lower = more deterministic).
        api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.

    Returns:
        The model's response text. Empty string on error.
    """
    key = api_key or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        logger.error("OPENROUTER_API_KEY not set")
        return ""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/funding-multi-agent",
    }

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        logger.info("Calling OpenRouter model=%s temp=%.1f", model, temperature)
        resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("OpenRouter response received (%d chars)", len(content))
        return content

    except requests.exceptions.RequestException as e:
        logger.error("OpenRouter API call failed: %s", e)
        return ""
