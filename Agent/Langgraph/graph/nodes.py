from __future__ import annotations

from typing import Any, Dict

from backend import complexity as complexity_mod
from backend import security as security_mod


def node_security(state: Dict[str, Any]) -> Dict[str, Any]:
    result = security_mod.analyse(state["prompt"])
    return {"risk_score": result.risk_score, "is_safe": result.is_safe, "matched_patterns": result.matched_patterns, "security_reason": result.reason}


def node_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    result = complexity_mod.analyse(state["prompt"])
    return {"complexity_score": result.score, "complexity_level": result.level, "complexity_tags": result.tags, "est_input_tokens": result.est_input_tokens, "est_output_tokens": result.est_output_tokens, "est_total_tokens": result.est_total_tokens}


def node_budget(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"budget_remaining": state.get("budget_remaining", 0.0), "budget_ok": True}


def node_cache(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"cache_hit": state.get("cache_hit", False)}


def node_router(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"selected_model": state.get("selected_model", ""), "selected_label": state.get("selected_label", "")}


def node_otari(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"response": state.get("response", "")}


def node_response(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"response": state.get("response", "")}
