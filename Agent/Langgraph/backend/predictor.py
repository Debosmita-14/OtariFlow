from __future__ import annotations

from .complexity import analyse as analyse_complexity


def estimate(prompt: str) -> dict:
    result = analyse_complexity(prompt)
    return {
        "complexity_score": result.score,
        "complexity_level": result.level,
        "complexity_tags": result.tags,
        "estimated_tokens": result.est_total_tokens,
    }
