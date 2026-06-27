from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class OtariState(TypedDict, total=False):
    prompt: str
    session_id: str
    risk_score: float
    is_safe: bool
    matched_patterns: List[str]
    security_reason: str
    complexity_score: float
    complexity_level: str
    complexity_tags: List[str]
    est_input_tokens: int
    est_output_tokens: int
    est_total_tokens: int
    estimated_cost: float
    budget_remaining: float
    budget_ok: bool
    cache_hit: bool
    cache_similarity: float
    cache_entry_id: Optional[int]
    selected_model: str
    selected_label: str
    selected_model_id: str
    selected_model_label: str
    routing_scores: Dict[str, float]
    routing_reason: str
    confidence: float
    why_not: Dict[str, Any]
    response: str
    actual_tokens: int
    actual_cost: float
    latency_ms: float
    blocked: bool
    error: Optional[str]
    db_request_id: Optional[int]
    timeline: List[Dict[str, str]]
