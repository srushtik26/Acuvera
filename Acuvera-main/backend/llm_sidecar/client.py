"""
LLM Sidecar — GROQ Cloud API client.
Feature-flagged, PHI-sanitized, never influences clinical decisions.
See SPEC.md §7 for exact rules.
"""
import json
import logging
import time
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger("acuvera.llm.client")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMCallError(Exception):
    pass


def _is_llm_enabled(feature_flags: dict) -> bool:
    return (
        bool(settings.GROQ_API_KEY)
        and feature_flags.get("LLM_ENABLED", settings.LLM_ENABLED_DEFAULT)
    )


def call_groq(
    system_prompt: str,
    user_content: str,
    feature_flags: dict,
    max_tokens: int = 512,
    retries: int = 3,
) -> Optional[str]:
    """
    Call GROQ Cloud API with retry + timeout.
    Returns raw text output or None on failure.
    PHI MUST be stripped before this call (see sanitizer.py).
    """
    if not _is_llm_enabled(feature_flags):
        logger.debug("LLM disabled — skipping GROQ call")
        return None

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,  # Low temperature for deterministic parsing tasks
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=settings.GROQ_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("GROQ call success attempt=%d tokens=%d", attempt,
                        data.get("usage", {}).get("total_tokens", 0))
            return content
        except requests.Timeout:
            logger.warning("GROQ timeout attempt %d/%d", attempt, retries)
        except requests.HTTPError as e:
            logger.warning("GROQ HTTP error %s attempt %d/%d", e, attempt, retries)
        except Exception as e:
            logger.error("GROQ unexpected error: %s attempt %d/%d", e, attempt, retries)

        if attempt < retries:
            time.sleep(2 ** attempt)  # exponential backoff

    return None


def call_groq_json(
    system_prompt: str,
    user_content: str,
    feature_flags: dict,
    expected_keys: list = None,
    max_tokens: int = 512,
) -> Optional[dict]:
    """
    Call GROQ and parse response as JSON.
    Validates expected_keys are present in output.
    Returns dict or None on failure/invalid schema.
    """
    raw = call_groq(system_prompt, user_content, feature_flags, max_tokens)
    if raw is None:
        return None

    # Extract JSON block if wrapped in markdown fences
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("GROQ returned invalid JSON: %s", text[:200])
        return None

    if expected_keys:
        missing = [k for k in expected_keys if k not in result]
        if missing:
            logger.warning("GROQ JSON missing expected keys: %s", missing)
            return None

    return result
