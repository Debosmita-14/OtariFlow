from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .complexity import ComplexityResult
from .config import settings


MODEL_CATALOG = settings.model_catalog()
MAX_LATENCY_MS = max(profile["avg_latency_ms"] for profile in MODEL_CATALOG)
MIN_MODEL_COST = min((profile["input_cost"] + profile["output_cost"]) / 2 for profile in MODEL_CATALOG)
MAX_MODEL_COST = max((profile["input_cost"] + profile["output_cost"]) / 2 for profile in MODEL_CATALOG)


@dataclass
class ModelScore:
    model_id: str
    label: str
    total_score: float
    complexity_fit: float
    cost_score: float
    latency_score: float
    confidence: float
    estimated_cost: float
    estimated_latency_ms: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class RoutingResult:
    selected_model: str
    selected_label: str
    selected_tier: str
    confidence: float
    routing_reason: str
    all_scores: List[ModelScore]
    why_not: Dict[str, dict]


def _cost_for_model(model_id: str, total_tokens: int) -> float:
    profile = settings.model_profile(model_id)
    input_tokens = int(total_tokens * 0.4)
    output_tokens = int(total_tokens * 0.6)
    return round((input_tokens * profile["input_cost"] + output_tokens * profile["output_cost"]) / 1000, 6)


def _model_cost_score(profile: dict) -> float:
    model_cost = (profile["input_cost"] + profile["output_cost"]) / 2
    if MAX_MODEL_COST <= MIN_MODEL_COST:
        return 1.0
    return round(1.0 - ((model_cost - MIN_MODEL_COST) / (MAX_MODEL_COST - MIN_MODEL_COST)), 4)


def _preferred_models(complexity: ComplexityResult) -> List[str]:
    tags = set(complexity.tags)
    if complexity.level == "high" or {"code", "research", "document"} & tags:
        return ["otari-flagship-ultra", "otari-neural-code", "grok-3-pro", "claude-3-7-sonnet", "gpt-4o", "llama-3-70b", "grok-3-mini", "mixtral-8x7b", "gemma-7b", "otari-lite-turbo"]
    if {"math", "json_structured", "long_context"} & tags:
        return ["otari-neural-code", "otari-flagship-ultra", "claude-3-7-sonnet", "gpt-4o", "grok-3-pro", "mixtral-8x7b", "grok-3-mini", "llama-3-70b", "gemma-7b", "otari-lite-turbo"]
    return ["otari-lite-turbo", "gemma-7b", "grok-3-mini", "mixtral-8x7b", "gpt-4o", "llama-3-70b", "otari-neural-code", "claude-3-7-sonnet", "grok-3-pro", "otari-flagship-ultra"]


def _tier_label(model_id: str) -> str:
    order = {
        "otari-lite-turbo": "Low Model",
        "gemma-7b": "Low Model",
        "grok-3-mini": "Medium Model",
        "mixtral-8x7b": "Medium Model",
        "llama-3-70b": "High Model",
        "otari-neural-code": "High Model",
        "gpt-4o": "High Model",
        "otari-flagship-ultra": "Premium Model",
        "grok-3-pro": "Premium Model",
        "claude-3-7-sonnet": "Premium Model",
    }
    return order.get(model_id, settings.model_profile(model_id)["label"])


def route(complexity: ComplexityResult, remaining_budget: float) -> RoutingResult:
    scores: List[ModelScore] = []
    weights = {"complexity": 0.4, "cost": 0.25, "latency": 0.2, "confidence": 0.15}
    preferred_order = _preferred_models(complexity)
    first_choice = preferred_order[0]

    for profile in settings.model_catalog():
        model_id = profile["model_id"]
        if complexity.score <= profile["max_complexity"]:
            fit = 1.0 - abs(complexity.score - profile["max_complexity"] * 0.7)
        else:
            fit = max(0.0, 1.0 - (complexity.score - profile["max_complexity"]) * 3)

        fit = round(min(1.0, max(0.0, fit)), 4)
        cost_score = _model_cost_score(profile)
        latency_score = round(1.0 - min(profile["avg_latency_ms"], MAX_LATENCY_MS) / MAX_LATENCY_MS, 4)
        confidence = round(profile["quality_score"] * fit, 4)
        estimated_cost = _cost_for_model(model_id, complexity.est_total_tokens)
        preference_bonus = round((len(preferred_order) - preferred_order.index(model_id)) / len(preferred_order) * 0.15, 4)
        if first_choice != "gemma-7b" and model_id == "gemma-7b":
            preference_bonus -= 0.25
        if model_id == first_choice:
            preference_bonus += 0.20

        if estimated_cost > remaining_budget:
            cost_score = 0.0

        total = round(
            weights["complexity"] * fit
            + weights["cost"] * cost_score
            + weights["latency"] * latency_score
            + weights["confidence"] * confidence,
            4,
        )
        total = round(min(1.0, total + preference_bonus), 4)

        reasons: List[str] = []
        if fit > 0.7:
            reasons.append("good complexity match")
        if cost_score > 0.7:
            reasons.append("cost efficient")
        if latency_score > 0.7:
            reasons.append("fast response")
        if confidence > 0.7:
            reasons.append("high confidence")
        if model_id == preferred_order[0]:
            reasons.append("best prompt match")

        scores.append(
            ModelScore(
                model_id=model_id,
                label=profile["label"],
                total_score=total,
                complexity_fit=fit,
                cost_score=cost_score,
                latency_score=latency_score,
                confidence=confidence,
                estimated_cost=estimated_cost,
                estimated_latency_ms=profile["avg_latency_ms"],
                reasons=reasons,
            )
        )

    scores.sort(key=lambda item: item.total_score, reverse=True)
    best = scores[0]
    why_not: Dict[str, dict] = {}

    for other in scores[1:]:
        cost_diff = round(other.estimated_cost - best.estimated_cost, 6)
        why_not[other.label] = {
            "cost_diff": cost_diff,
            "latency_diff": round(other.estimated_latency_ms - best.estimated_latency_ms, 0),
            "quality_diff": round(settings.model_profile(other.model_id)["quality_score"] - settings.model_profile(best.model_id)["quality_score"], 3),
            "savings": round(-cost_diff, 6) if cost_diff < 0 else 0.0,
        }

    reason = f"Selected {best.label} (score {best.total_score:.2f})"
    if best.reasons:
        reason += " — " + "; ".join(best.reasons)

    return RoutingResult(
        selected_model=best.model_id,
        selected_label=best.label,
        selected_tier=_tier_label(best.model_id),
        confidence=best.confidence,
        routing_reason=reason,
        all_scores=scores,
        why_not=why_not,
    )
