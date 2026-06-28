from __future__ import annotations

import sys
import os

# Ensure the project root is on the path so `cache` package resolves correctly
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from .complexity import analyse as analyse_complexity
from .config import settings
from .router import route
from .security import analyse as analyse_security
from .agent_modes import get_mode, DEFAULT_MODE
from .llm_client import call_llm, LLMResult
from . import store
from cache import faiss_store as cache_store

logger = logging.getLogger("otariflow.service")

# ---------------------------------------------------------------------------
# Model upgrade order for latency watchdog (Feature 4)
# ---------------------------------------------------------------------------
UPGRADE_ORDER = ["otari-lite-turbo", "gemma-7b", "grok-3-mini", "mixtral-8x7b", "llama-3-70b", "otari-neural-code", "gpt-4o", "grok-3-pro", "otari-flagship-ultra", "claude-3-7-sonnet"]


def _timeline(state: Dict[str, Any], status: str, detail: str) -> List[Dict[str, str]]:
    entries = list(state.get("timeline", []))
    entries.append({"status": status, "detail": detail})
    return entries


def _cost_for_model(model_id: str, total_tokens: int) -> float:
    profile = settings.model_profile(model_id)
    input_tokens = int(total_tokens * 0.4)
    output_tokens = int(total_tokens * 0.6)
    return round((input_tokens * profile["input_cost"] + output_tokens * profile["output_cost"]) / 1000, 6)


def _default_model_id() -> str:
    catalog = settings.model_catalog()
    return min(catalog, key=lambda item: item["input_cost"] + item["output_cost"])["model_id"]


def _next_tier_model(current_model_id: str) -> str | None:
    """Return the next model up in the upgrade chain, or None if already at top."""
    try:
        idx = UPGRADE_ORDER.index(current_model_id)
    except ValueError:
        return None
    if idx + 1 < len(UPGRADE_ORDER):
        return UPGRADE_ORDER[idx + 1]
    return None


def _latency_threshold(model_id: str) -> float:
    """Return the latency watchdog threshold for a model (2× its avg_latency_ms)."""
    profile = settings.model_profile(model_id)
    return profile["avg_latency_ms"] * 2.0


def _do_llm_call(
    model_id: str,
    model_label: str,
    prompt: str,
    system_prompt: str,
    state: Dict[str, Any],
    remaining_budget: float,
    est_total_tokens: int,
) -> Dict[str, Any]:
    """Execute the real LLM call with latency watchdog and automatic model upgrade.

    Returns a dict with keys: response, actual_tokens, actual_cost, latency_ms,
    prompt_tokens, completion_tokens, total_tokens, escalation_history, extra_timeline.
    """
    escalation_history: List[Dict[str, Any]] = []
    extra_timeline: List[Dict[str, str]] = []
    current_model_id = model_id
    current_label = model_label
    timeout_ms = settings.model_timeout_ms

    # Show estimated cost for the initially selected model
    estimated_cost = _cost_for_model(current_model_id, est_total_tokens)
    extra_timeline.append({
        "status": "Estimated cost",
        "detail": f"{current_label}: ${estimated_cost:.6f}",
    })

    while True:
        # Use a generous timeout so we don't time out on slow free APIs
        call_timeout = max(timeout_ms, 25_000)
        result: LLMResult = call_llm(
            model_id=current_model_id,
            user_prompt=prompt,
            system_prompt=system_prompt,
            timeout_ms=call_timeout,
        )

        # On success — return immediately, skip latency escalation
        # (escalation causes rapid sequential calls that trip rate limits)
        if result.success:
            # Use real token counts from provider, fall back to estimates
            actual_tokens = result.total_tokens if result.total_tokens > 0 else max(1, int(est_total_tokens * 0.9))
            actual_cost = _cost_for_model(current_model_id, actual_tokens) if result.total_tokens > 0 else round(estimated_cost * 1.05, 6)

            return {
                "response": result.content,
                "actual_tokens": actual_tokens,
                "actual_cost": actual_cost,
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "escalation_history": escalation_history,
                "extra_timeline": extra_timeline,
                "selected_model": current_model_id,
                "selected_label": current_label,
                "estimated_cost": estimated_cost,
                "success": True,
            }

        # Call failed — try upgrade (with delay to avoid rate limiting)
        import time as _time
        _time.sleep(1.0)

        next_model = _next_tier_model(current_model_id)
        if next_model:
            next_profile = settings.model_profile(next_model)
            next_cost = _cost_for_model(next_model, est_total_tokens)

            if next_cost <= remaining_budget:
                escalation_entry = {
                    "from_model": current_label,
                    "to_model": next_profile["label"],
                    "reason": f"Call failed on {current_label}: {result.error}",
                    "estimated_cost": next_cost,
                }
                escalation_history.append(escalation_entry)
                extra_timeline.append({
                    "status": "Model upgraded",
                    "detail": (
                        f"{current_label} failed ({result.error[:80]}) "
                        f"— escalating to {next_profile['label']} (est. cost ${next_cost:.5f})"
                    ),
                })

                current_model_id = next_model
                current_label = next_profile["label"]
                estimated_cost = next_cost

                extra_timeline.append({
                    "status": "Updated estimated cost",
                    "detail": f"{current_label}: ${estimated_cost:.6f}",
                })
                continue

        # No more upgrades available — return error
        return {
            "response": "Sorry, I couldn't process your request right now. Please try again in a moment.",
            "actual_tokens": 0,
            "actual_cost": 0.0,
            "latency_ms": result.latency_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "escalation_history": escalation_history,
            "extra_timeline": extra_timeline,
            "selected_model": current_model_id,
            "selected_label": current_label,
            "estimated_cost": estimated_cost,
            "success": False,
        }


def process_prompt(
    prompt: str,
    session_id: str = "default",
    user_id: str = "default",
    agent_mode: str = DEFAULT_MODE,
) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "prompt": prompt,
        "session_id": session_id,
        "user_id": user_id,
        "agent_mode": agent_mode,
        "timeline": [],
        "blocked": False,
    }

    # --- Security check ---
    security = analyse_security(prompt)
    state.update(
        {
            "risk_score": security.risk_score,
            "is_safe": security.is_safe,
            "matched_patterns": security.matched_patterns,
            "security_reason": security.reason,
            "blocked": not security.is_safe,
            "timeline": _timeline(state, "Security checked", f"Risk score {security.risk_score:.2f}"),
        }
    )

    if state["blocked"]:
        store.log_attack(
            {
                "prompt": prompt,
                "reason": security.reason,
                "risk_score": security.risk_score,
                "matched_patterns": security.matched_patterns,
            }
        )
        return _finalize(state)

    # --- Complexity analysis ---
    complexity = analyse_complexity(prompt)
    state.update(
        {
            "complexity_score": complexity.score,
            "complexity_level": complexity.level,
            "complexity_tags": complexity.tags,
            "est_input_tokens": complexity.est_input_tokens,
            "est_output_tokens": complexity.est_output_tokens,
            "est_total_tokens": complexity.est_total_tokens,
            "timeline": _timeline(
                state,
                "Complexity classified",
                f"{complexity.level.title()} • {', '.join(complexity.tags) or 'none'}",
            ),
        }
    )

    # --- Budget check (pre-route) ---
    budget = store.get_budget()
    remaining_budget = float(budget["remaining"])
    state["budget_remaining"] = remaining_budget

    if remaining_budget <= 0:
        state["blocked"] = True
        state["security_reason"] = "Budget exhausted"
        state["timeline"] = _timeline(state, "Budget check failed", "No budget remaining")
        return _finalize(state)

    estimated_cost = _cost_for_model(_default_model_id(), state["est_total_tokens"])
    state["estimated_cost"] = estimated_cost

    # --- Cache lookup ---
    cache_hit = cache_store.lookup(prompt)
    if cache_hit:
        state.update(
            {
                "response": cache_hit["response"],
                "selected_model": cache_hit.get("model_id") or cache_hit.get("model_used"),
                "selected_label": cache_hit.get("model_label") or cache_hit.get("model_used", "Cached Model"),
                "selected_model_id": cache_hit.get("model_id") or cache_hit.get("model_used"),
                "selected_model_label": cache_hit.get("model_label") or cache_hit.get("model_used", "Cached Model"),
                "cache_hit": True,
                "cache_similarity": cache_hit.get("similarity", 1.0),
                "cache_entry_id": cache_hit.get("id"),
                "actual_tokens": 0,
                "actual_cost": 0.0,
                "latency_ms": 0.0,
                "timeline": _timeline(state, "Cache hit", f"Similarity {cache_hit.get('similarity', 0):.2%}"),
            }
        )
        cache_store.increment_hit(int(cache_hit["id"]))
        return _finalize(state)

    # --- Model routing ---
    route_result = route(complexity, remaining_budget=remaining_budget)
    state.update(
        {
            "selected_model": route_result.selected_model,
            "selected_label": route_result.selected_label,
            "routing_scores": {item.label: item.total_score for item in route_result.all_scores},
            "routing_reason": route_result.routing_reason,
            "confidence": route_result.confidence,
            "why_not": route_result.why_not,
            "timeline": _timeline(state, "Model routed", route_result.routing_reason),
        }
    )

    selected_cost = next(
        (item.estimated_cost for item in route_result.all_scores if item.model_id == route_result.selected_model),
        estimated_cost,
    )
    state["estimated_cost"] = selected_cost

    # --- Budget check (post-route) ---
    if selected_cost > remaining_budget:
        state["blocked"] = True
        state["security_reason"] = "Insufficient budget for selected model"
        state["timeline"] = _timeline(
            state,
            "Budget check failed",
            f"Needed ${selected_cost:.5f}, remaining ${remaining_budget:.5f}",
        )
        return _finalize(state)

    # --- Get system prompt from agent mode ---
    mode_config = get_mode(agent_mode)
    system_prompt = mode_config.get("system_prompt", "")
    state["timeline"] = _timeline(
        state, "Agent mode applied", f"{mode_config.get('label', agent_mode)}"
    )

    # --- Generate response (real LLM call with latency watchdog) ---
    llm_result = _do_llm_call(
        model_id=route_result.selected_model,
        model_label=route_result.selected_label,
        prompt=prompt,
        system_prompt=system_prompt,
        state=state,
        remaining_budget=remaining_budget,
        est_total_tokens=state["est_total_tokens"],
    )

    # Apply extra timeline entries from the LLM call
    for entry in llm_result.get("extra_timeline", []):
        state["timeline"] = _timeline(state, entry["status"], entry["detail"])

    # Update state with the final model (may have been upgraded)
    final_model_id = llm_result["selected_model"]
    final_label = llm_result["selected_label"]

    state.update(
        {
            "response": llm_result["response"],
            "actual_tokens": llm_result["actual_tokens"],
            "actual_cost": llm_result["actual_cost"],
            "latency_ms": llm_result["latency_ms"],
            "prompt_tokens": llm_result.get("prompt_tokens", 0),
            "completion_tokens": llm_result.get("completion_tokens", 0),
            "total_tokens": llm_result.get("total_tokens", 0),
            "escalation_history": llm_result.get("escalation_history", []),
            "estimated_cost": llm_result.get("estimated_cost", selected_cost),
            "selected_model": final_model_id,
            "selected_label": final_label,
            "timeline": _timeline(
                state,
                "Response generated",
                f"{llm_result['actual_tokens']} tokens | ${llm_result['actual_cost']:.5f} | {llm_result['latency_ms']:.0f}ms",
            ),
        }
    )

    # Only deduct budget and update metrics on successful calls
    if llm_result.get("success", True) and llm_result["actual_cost"] > 0:
        store.deduct_budget(llm_result["actual_cost"])
        store.update_model_metrics(
            final_label,
            llm_result["actual_cost"],
            llm_result["actual_tokens"],
            llm_result["latency_ms"],
            state.get("confidence", route_result.confidence),
        )
        cache_store.add(
            prompt=prompt,
            response=llm_result["response"],
            model_id=final_model_id,
            model_label=final_label,
            similarity=1.0,
            cost_saved=max(0.0, selected_cost - llm_result["actual_cost"]),
        )

    return _finalize(state)


def _finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    prompt = state.get("prompt", "")
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

    payload = {
        "prompt": prompt,
        "response": state.get("response"),
        "risk_score": state.get("risk_score", 0.0),
        "complexity": state.get("complexity_level", "low"),
        "complexity_level": state.get("complexity_level", "low"),
        "complexity_score": state.get("complexity_score", 0.0),
        "complexity_tags": state.get("complexity_tags", []),
        "estimated_tokens": state.get("est_total_tokens", 0),
        "actual_tokens": state.get("actual_tokens", 0),
        "estimated_cost": state.get("estimated_cost", 0.0),
        "actual_cost": state.get("actual_cost", 0.0),
        # Expose both label (human-readable) and id (machine-readable) for the frontend
        "selected_model": state.get("selected_label"),
        "selected_model_id": state.get("selected_model"),
        "selected_model_label": state.get("selected_label"),
        "cache_hit": state.get("cache_hit", False),
        "cache_similarity": state.get("cache_similarity", 0.0),
        "cache_entry_id": state.get("cache_entry_id"),
        "routing_scores": state.get("routing_scores", {}),
        "confidence": state.get("confidence", 0.0),
        "routing_reason": state.get("routing_reason", ""),
        "latency_ms": state.get("latency_ms", 0.0),
        "blocked": state.get("blocked", False),
        "timeline": state.get("timeline", []),
        "user_id": state.get("user_id", "default"),
        "session_id": state.get("session_id", "default"),
        "prompt_hash": prompt_hash,
        "selected_tier": state.get("selected_tier", "low"),
        "execution_time_ms": state.get("latency_ms", 0.0),
        "security_result": state.get("security_reason", ""),
        "escalation_history": state.get("escalation_history", []),
        "quality_score": 0.0,
        "quality_label": "unknown",
        "verification_status": "pending",
        "verification_notes": [],
        "self_eval": {},
        "agent_mode": state.get("agent_mode", DEFAULT_MODE),
        "prompt_tokens": state.get("prompt_tokens", 0),
        "completion_tokens": state.get("completion_tokens", 0),
        "total_tokens": state.get("total_tokens", 0),
    }
    payload["request_id"] = store.create_request(payload)
    payload["budget"] = store.get_budget()
    payload["why_not"] = state.get("why_not", {})
    payload["matched_patterns"] = state.get("matched_patterns", [])
    payload["security_reason"] = state.get("security_reason", "")
    return payload
