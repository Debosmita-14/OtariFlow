from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    label: str
    min_complexity: float
    max_complexity: float
    quality_score: float
    avg_latency_ms: int
    input_cost: float
    output_cost: float


class Settings:
    app_name = "OtariFlow"
    version = "1.0.0"

    total_budget = _env_float("TOTAL_BUDGET", 5.0)
    budget_warning_threshold = _env_float("BUDGET_WARNING_THRESHOLD", 0.8)
    risk_block_threshold = _env_float("RISK_BLOCK_THRESHOLD", 0.75)

    # Requested replacement for Anthropic/Claude references.
    otari_api_key = os.getenv("OTARI_API_KEY", "")
    mozilla_api_key = os.getenv("MOZILLA_API_KEY", "")

    backend_port = _env_int("BACKEND_PORT", 8000)
    frontend_port = _env_int("FRONTEND_PORT", 8000)
    cache_similarity_threshold = _env_float("CACHE_SIMILARITY_THRESHOLD", 0.85)
    cache_max_size = _env_int("CACHE_MAX_SIZE", 1000)
    rate_limit_per_minute = _env_int("RATE_LIMIT_PER_MINUTE", 20)
    model_timeout_ms = _env_int("MODEL_TIMEOUT_MS", 9000)
    memory_summary_threshold = _env_int("MEMORY_SUMMARY_THRESHOLD", 6)
    verification_confidence_floor = _env_float("VERIFICATION_CONFIDENCE_FLOOR", 0.70)

    db_path = os.getenv("OTARIFLOW_DB", os.path.join(os.path.dirname(__file__), "..", "otariflow.sqlite3"))

    models = {
        "otari-lite-turbo": {
            "name": "Otari Lite Turbo",
            "provider": "Otari",
            "cost_per_1k": 0.00005,
            "latency_avg": 0.4,
            "context_window": 16384,
            "strengths": ["instant response", "energy efficient", "native routing"],
            "tier": "economy",
        },
        "gemma-7b": {
            "name": "Gemma 7B",
            "provider": "Google",
            "cost_per_1k": 0.00007,
            "latency_avg": 0.6,
            "context_window": 8192,
            "strengths": ["ultra-fast", "ultra-cheap", "simple"],
            "tier": "economy",
        },
        "grok-3-mini": {
            "name": "Grok 3 Mini",
            "provider": "xAI",
            "cost_per_1k": 0.00035,
            "latency_avg": 0.8,
            "context_window": 32768,
            "strengths": ["rapid reasoning", "knowledge retrieval", "code"],
            "tier": "balanced",
        },
        "mixtral-8x7b": {
            "name": "Mixtral 8x7B",
            "provider": "Mistral",
            "cost_per_1k": 0.00024,
            "latency_avg": 1.1,
            "context_window": 32768,
            "strengths": ["multilingual", "fast", "balanced"],
            "tier": "balanced",
        },
        "llama-3-70b": {
            "name": "Llama 3 70B",
            "provider": "Meta",
            "cost_per_1k": 0.00059,
            "latency_avg": 1.6,
            "context_window": 8192,
            "strengths": ["open-source", "reasoning", "code"],
            "tier": "balanced",
        },
        "otari-neural-code": {
            "name": "Otari Neural Code",
            "provider": "Otari",
            "cost_per_1k": 0.00085,
            "latency_avg": 1.2,
            "context_window": 65536,
            "strengths": ["advanced software engineering", "polyglot execution", "debugging"],
            "tier": "premium",
        },
        "gpt-4o": {
            "name": "GPT-4o",
            "provider": "OpenAI",
            "cost_per_1k": 0.00095,
            "latency_avg": 1.3,
            "context_window": 128000,
            "strengths": ["omni-capabilities", "multimodal", "fast premium"],
            "tier": "premium",
        },
        "otari-flagship-ultra": {
            "name": "Otari Flagship Ultra",
            "provider": "Otari",
            "cost_per_1k": 0.00110,
            "latency_avg": 1.5,
            "context_window": 128000,
            "strengths": ["deep domain expertise", "native otari integration", "autonomous planning"],
            "tier": "premium",
        },
        "grok-3-pro": {
            "name": "Grok 3 Pro",
            "provider": "xAI",
            "cost_per_1k": 0.00120,
            "latency_avg": 1.7,
            "context_window": 128000,
            "strengths": ["advanced reasoning", "humor", "unfiltered real-time"],
            "tier": "premium",
        },
        "claude-3-7-sonnet": {
            "name": "Claude 3.7 Sonnet",
            "provider": "Anthropic",
            "cost_per_1k": 0.00150,
            "latency_avg": 2.1,
            "context_window": 200000,
            "strengths": ["expert coding", "hybrid reasoning", "superb logic"],
            "tier": "premium",
        },
    }

    def _normalize_model(self, model_id: str, raw: Any) -> Dict[str, Any]:
        if hasattr(raw, "avg_latency_ms"):
            return {
                "model_id": getattr(raw, "model_id", model_id),
                "label": getattr(raw, "label", model_id),
                "min_complexity": getattr(raw, "min_complexity", 0.0),
                "max_complexity": getattr(raw, "max_complexity", 1.0),
                "quality_score": getattr(raw, "quality_score", 0.8),
                "avg_latency_ms": getattr(raw, "avg_latency_ms", 1000),
                "input_cost": getattr(raw, "input_cost", 0.001),
                "output_cost": getattr(raw, "output_cost", 0.002),
                "provider": getattr(raw, "provider", "unknown"),
                "tier": getattr(raw, "tier", "balanced"),
                "context_window": getattr(raw, "context_window", 8192),
                "strengths": list(getattr(raw, "strengths", [])),
            }

        tier = str(raw.get("tier", "balanced"))
        label = str(raw.get("name", model_id))
        cost = float(raw.get("cost_per_1k", 0.001))
        latency_ms = int(float(raw.get("latency_avg", 1.0)) * 1000)
        return {
            "model_id": model_id,
            "label": label,
            "min_complexity": {"economy": 0.0, "balanced": 0.25, "premium": 0.55}.get(tier, 0.25),
            "max_complexity": {"economy": 0.55, "balanced": 0.9, "premium": 1.0}.get(tier, 0.9),
            "quality_score": {"economy": 0.74, "balanced": 0.86, "premium": 0.94}.get(tier, 0.86),
            "avg_latency_ms": latency_ms,
            "input_cost": cost,
            "output_cost": round(cost * 2.5, 6),
            "provider": str(raw.get("provider", "unknown")),
            "tier": tier,
            "context_window": int(raw.get("context_window", 8192)),
            "strengths": list(raw.get("strengths", [])),
        }

    def model_catalog(self) -> List[Dict[str, Any]]:
        return [self._normalize_model(model_id, raw) for model_id, raw in self.models.items()]

    def model_profile(self, model_id: str) -> Dict[str, Any]:
        return self._normalize_model(model_id, self.models[model_id])

    def model_ids(self) -> List[str]:
        return list(self.models.keys())


settings = Settings()
