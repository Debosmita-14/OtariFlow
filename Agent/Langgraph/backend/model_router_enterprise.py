"""
Multi-level AI Model Routing System.
Intelligently routes prompts to Low/Medium/High tier models based on complexity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

from .complexity import analyse as analyse_complexity
from .config import settings


class ModelTier(Enum):
    """AI model tiers with performance levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ModelProfile:
    """Profile information for a routing tier."""
    tier: ModelTier
    emoji: str
    description: str
    model_ids: List[str]
    latency_ms: int
    capability_score: float
    cost_per_1k_tokens: float


# Define tier-specific model profiles
TIER_PROFILES: Dict[ModelTier, ModelProfile] = {
    ModelTier.LOW: ModelProfile(
        tier=ModelTier.LOW,
        emoji="🟢",
        description="Fast & efficient for simple queries",
        model_ids=["gemma-7b", "mistral-7b"],
        latency_ms=800,
        capability_score=0.6,
        cost_per_1k_tokens=0.0001
    ),
    ModelTier.MEDIUM: ModelProfile(
        tier=ModelTier.MEDIUM,
        emoji="🟡",
        description="Balanced for complex reasoning",
        model_ids=["mixtral-8x7b", "llama-2-70b"],
        latency_ms=2000,
        capability_score=0.8,
        cost_per_1k_tokens=0.0003
    ),
    ModelTier.HIGH: ModelProfile(
        tier=ModelTier.HIGH,
        emoji="🔴",
        description="Most capable for advanced tasks",
        model_ids=["llama-3-70b", "gpt-4", "claude-3-opus"],
        latency_ms=4000,
        capability_score=0.95,
        cost_per_1k_tokens=0.001
    )
}


# Task categorization for routing
LOW_TIER_KEYWORDS = {
    "greetings", "hello", "hi", "simple", "easy", "basic",
    "grammar", "spelling", "rewrite", "summarize", "faq",
    "repeat", "paraphrase", "translate", "list", "count"
}

MEDIUM_TIER_KEYWORDS = {
    "code", "debug", "analyze", "database", "api", "math",
    "json", "structure", "format", "documentation", "explain",
    "convert", "optimize", "refactor", "logic", "algorithm"
}

HIGH_TIER_KEYWORDS = {
    "reason", "research", "architecture", "design", "strategy",
    "planning", "complex", "advanced", "deep", "profound",
    "multi-step", "project", "framework", "comprehensive", "expert"
}


@dataclass
class RoutingDecision:
    """Result of model tier routing decision."""
    selected_tier: ModelTier
    selected_model_id: str
    confidence: float
    reason: str
    keyword_matches: Dict[ModelTier, int] = field(default_factory=dict)
    complexity_score: float = 0.0
    complexity_level: str = ""
    recommended_alternatives: List[str] = field(default_factory=list)


def _calculate_keyword_score(prompt: str) -> Dict[ModelTier, int]:
    """Calculate tier score based on keyword matches."""
    prompt_lower = prompt.lower()
    scores: Dict[ModelTier, int] = {tier: 0 for tier in ModelTier}
    
    # Count keyword matches
    for keyword in LOW_TIER_KEYWORDS:
        if keyword in prompt_lower:
            scores[ModelTier.LOW] += 1
    
    for keyword in MEDIUM_TIER_KEYWORDS:
        if keyword in prompt_lower:
            scores[ModelTier.MEDIUM] += 2  # Higher weight
    
    for keyword in HIGH_TIER_KEYWORDS:
        if keyword in prompt_lower:
            scores[ModelTier.HIGH] += 3  # Highest weight
    
    return scores


def _get_tier_for_complexity(complexity_score: float, complexity_level: str) -> ModelTier:
    """Map complexity analysis to model tier."""
    if complexity_level == "high":
        return ModelTier.HIGH
    if complexity_level == "medium":
        return ModelTier.MEDIUM
    return ModelTier.LOW


def route_to_tier(prompt: str) -> RoutingDecision:
    """
    Route a prompt to the most appropriate model tier.
    
    Args:
        prompt: The user prompt to route
        
    Returns:
        RoutingDecision with selected tier and reasoning
    """
    # Analyze complexity
    complexity = analyse_complexity(prompt)
    complexity_tier = _get_tier_for_complexity(
        complexity.score,
        complexity.level
    )
    
    # Calculate keyword scores
    keyword_scores = _calculate_keyword_score(prompt)
    
    # Determine final tier based on both signals
    tier_scores = {
        ModelTier.LOW: keyword_scores[ModelTier.LOW] + (1 if complexity_tier == ModelTier.LOW else 0),
        ModelTier.MEDIUM: keyword_scores[ModelTier.MEDIUM] + (2 if complexity_tier == ModelTier.MEDIUM else 0),
        ModelTier.HIGH: keyword_scores[ModelTier.HIGH] + (3 if complexity_tier == ModelTier.HIGH else 0)
    }
    
    selected_tier = max(tier_scores, key=tier_scores.get)
    profile = TIER_PROFILES[selected_tier]
    
    # Select specific model from tier
    selected_model_id = profile.model_ids[0]
    
    # Calculate confidence (0.0 to 1.0)
    max_score = max(tier_scores.values()) if tier_scores.values() else 1.0
    confidence = tier_scores[selected_tier] / (max_score + 1) if max_score > 0 else 0.5
    confidence = min(1.0, max(0.0, confidence))
    
    # Build reason
    reason = f"Complexity: {complexity.level.title()} | Keywords: {', '.join(complexity.tags) or 'none'}"
    
    # Get alternatives
    alternatives = [
        m for tier, prof in TIER_PROFILES.items()
        if tier != selected_tier
        for m in prof.model_ids[:2]
    ]
    
    return RoutingDecision(
        selected_tier=selected_tier,
        selected_model_id=selected_model_id,
        confidence=round(confidence, 2),
        reason=reason,
        keyword_matches=keyword_scores,
        complexity_score=complexity.score,
        complexity_level=complexity.level,
        recommended_alternatives=alternatives
    )


def get_tier_display_badge(tier: ModelTier) -> str:
    """Get display badge for tier."""
    profile = TIER_PROFILES[tier]
    return f"{profile.emoji} {tier.value.title()} Model"


def get_tier_capabilities(tier: ModelTier) -> Dict[str, Any]:
    """Get detailed capabilities for a tier."""
    profile = TIER_PROFILES[tier]
    return {
        "tier": tier.value,
        "emoji": profile.emoji,
        "description": profile.description,
        "avg_latency_ms": profile.latency_ms,
        "capability_score": profile.capability_score,
        "estimated_cost": f"${profile.cost_per_1k_tokens:.4f} per 1K tokens",
        "typical_use_cases": _get_use_cases(tier)
    }


def _get_use_cases(tier: ModelTier) -> List[str]:
    """Get typical use cases for a tier."""
    use_cases = {
        ModelTier.LOW: [
            "Greetings and simple questions",
            "Grammar and spelling checks",
            "Text rewriting and paraphrasing",
            "Summarization of short texts",
            "FAQ responses"
        ],
        ModelTier.MEDIUM: [
            "Code debugging and optimization",
            "Data analysis and processing",
            "API documentation generation",
            "Mathematical problem solving",
            "Database query help"
        ],
        ModelTier.HIGH: [
            "Long-form reasoning and research",
            "System architecture design",
            "Multi-step project planning",
            "Complex debugging scenarios",
            "Advanced AI-driven insights"
        ]
    }
    return use_cases.get(tier, [])
