"""Isolated LLM HTTP client for OtariFlow.

All real provider calls are routed through `call_llm()`.
Provider: Pollinations AI — completely free, no API key required.
Endpoint: https://text.pollinations.ai/
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger("otariflow.llm_client")

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Model → Pollinations model name mapping
# ---------------------------------------------------------------------------
# All tiers use openai-fast (the only available free model on Pollinations).
# Tier labels remain distinct in the UI for routing display purposes.

POLLINATIONS_ENDPOINT = "https://text.pollinations.ai/"

PROVIDER_MAP: Dict[str, str] = {
    "otari-lite-turbo":  "openai-fast",
    "gemma-7b":          "openai-fast",
    "grok-3-mini":       "openai-fast",
    "mixtral-8x7b":      "openai-fast",
    "llama-3-70b":       "openai-fast",
    "otari-neural-code": "openai-fast",
    "gpt-4o":            "openai-fast",
    "otari-flagship-ultra": "openai-fast",
    "grok-3-pro":        "openai-fast",
    "claude-3-7-sonnet": "openai-fast",
}


@dataclass
class LLMResult:
    """Structured result from a real LLM call."""
    content: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)


def call_llm(
    model_id: str,
    user_prompt: str,
    system_prompt: str = "",
    timeout_ms: int = 30_000,
) -> LLMResult:
    """Call Pollinations AI for *model_id* — no API key needed.

    Returns an LLMResult with content on success or error details on failure.
    Never raises — all exceptions are caught and returned in the result.
    """
    if _requests is None:
        return LLMResult(
            content="",
            model_id=model_id,
            success=False,
            error="The 'requests' library is not installed. Run: pip install requests",
        )

    api_model = PROVIDER_MAP.get(model_id, "openai")

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    timeout_seconds = max(10, timeout_ms / 1000)

    start = time.perf_counter()
    try:
        resp = _requests.post(
            POLLINATIONS_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json={
                "model": api_model,
                "messages": messages,
                "seed": 42,
                "private": True,
            },
            timeout=timeout_seconds,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        if resp.status_code != 200:
            logger.error("Pollinations HTTP %d for %s: %s", resp.status_code, model_id, resp.text[:300])
            return LLMResult(
                content="",
                model_id=model_id,
                latency_ms=latency_ms,
                success=False,
                error=f"HTTP {resp.status_code}",
            )

        # Pollinations returns plain text directly
        content = resp.text.strip()

        # Estimate token counts (~4 chars per token)
        prompt_text = system_prompt + user_prompt
        est_prompt_tokens = max(1, len(prompt_text) // 4)
        est_completion_tokens = max(1, len(content) // 4)
        est_total = est_prompt_tokens + est_completion_tokens

        return LLMResult(
            content=content,
            model_id=model_id,
            prompt_tokens=est_prompt_tokens,
            completion_tokens=est_completion_tokens,
            total_tokens=est_total,
            latency_ms=latency_ms,
            success=True,
        )

    except _requests.exceptions.Timeout:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return LLMResult(
            content="",
            model_id=model_id,
            latency_ms=latency_ms,
            success=False,
            error=f"Request timed out after {timeout_seconds:.0f}s",
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.exception("LLM call failed for %s", model_id)
        return LLMResult(
            content="",
            model_id=model_id,
            latency_ms=latency_ms,
            success=False,
            error=str(exc),
        )
