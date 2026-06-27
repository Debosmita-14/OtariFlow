from __future__ import annotations

import sys
import os

# Ensure the project root is on the path so `cache` package resolves correctly
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
from dataclasses import dataclass
from typing import Any, Dict, List

from .complexity import analyse as analyse_complexity
from .config import settings
from .router import route
from .security import analyse as analyse_security
from . import store
from cache import faiss_store as cache_store


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


def _build_response(prompt: str, model_id: str, complexity_level: str, model_label: str) -> str:
    """
    Build a simulated response for the selected model.
    Replace this body with a real API call when you have credentials.

    Example real call (Groq/OpenRouter/etc.):
        import httpx
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
            json={"model": model_id, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        return r.json()["choices"][0]["message"]["content"]
    """
    profile = settings.model_profile(model_id)
    tier = profile["tier"]

    if tier == "economy":
        return (
            f"[{model_label}] Simple request handled.\n\n"
            f"Prompt summary: {prompt.strip()[:220]}"
        )
    return (
        f"[{model_label}] Complex request handled.\n\n"
        f"Complexity tier: {complexity_level}.\n"
        f"Analysis: I reviewed the task and selected the best-fit model for this query.\n"
        f"Prompt focus: {prompt.strip()[:220]}"
    )


def process_prompt(prompt: str, session_id: str = "default") -> Dict[str, Any]:
    state: Dict[str, Any] = {"prompt": prompt, "session_id": session_id, "timeline": [], "blocked": False}

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

    # --- Generate response ---
    start = time.time()
    response = _build_response(prompt, route_result.selected_model, complexity.level, route_result.selected_label)
    latency_ms = round(
        (time.time() - start) * 1000 + settings.model_profile(route_result.selected_model)["avg_latency_ms"],
        1,
    )
    actual_tokens = max(1, int(state["est_total_tokens"] * 0.9))
    actual_cost = round(selected_cost * 1.05, 6)

    state.update(
        {
            "response": response,
            "actual_tokens": actual_tokens,
            "actual_cost": actual_cost,
            "latency_ms": latency_ms,
            "timeline": _timeline(
                state,
                "Response generated",
                f"{actual_tokens} tokens | ${actual_cost:.5f} | {latency_ms:.0f}ms",
            ),
        }
    )

    store.deduct_budget(actual_cost)
    store.update_model_metrics(
        route_result.selected_label, actual_cost, actual_tokens, latency_ms, route_result.confidence
    )
    cache_store.add(
        prompt=prompt,
        response=response,
        model_id=route_result.selected_model,
        model_label=route_result.selected_label,
        similarity=1.0,
        cost_saved=max(0.0, selected_cost - actual_cost),
    )
    return _finalize(state)


def _finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "prompt": state.get("prompt", ""),
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
    }
    payload["request_id"] = store.create_request(payload)
    payload["budget"] = store.get_budget()
    payload["why_not"] = state.get("why_not", {})
    payload["matched_patterns"] = state.get("matched_patterns", [])
    payload["security_reason"] = state.get("security_reason", "")
    return payload
