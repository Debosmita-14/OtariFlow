from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Request:
    prompt: str
    response: Optional[str] = None
    risk_score: float = 0.0
    complexity: str = "low"
    complexity_score: float = 0.0
    complexity_tags: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    actual_tokens: int = 0
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    selected_model: Optional[str] = None
    selected_model_id: Optional[str] = None
    routing_scores: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    routing_reason: str = ""
    latency_ms: float = 0.0
    cache_hit: bool = False
    blocked: bool = False
    timeline: List[Dict[str, str]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Budget:
    total_budget: float = 5.0
    spent: float = 0.0
    remaining: float = 5.0
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BlockedAttack:
    prompt: str
    reason: str = ""
    risk_score: float = 0.0
    matched_patterns: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CacheEntry:
    prompt: str
    response: str
    model_used: str = ""
    similarity: float = 1.0
    cost_saved: float = 0.0
    hits: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelMetrics:
    model_name: str
    total_requests: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    last_used: datetime = field(default_factory=datetime.utcnow)
