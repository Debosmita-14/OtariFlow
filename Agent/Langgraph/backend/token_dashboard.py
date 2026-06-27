"""
Token Usage Dashboard and Cost Tracking.
Monitors token consumption and associated costs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any


@dataclass
class TokenUsage:
    """Token usage for a single request."""
    prompt_tokens: int
    completion_tokens: int
    model_used: str
    processing_time_ms: float
    estimated_cost: float
    timestamp: str
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.prompt_tokens + self.completion_tokens


@dataclass
class TokenUsageStats:
    """Aggregated token usage statistics."""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_processing_time_ms: float = 0.0
    request_count: int = 0
    model_breakdown: Dict[str, int] = field(default_factory=dict)


class TokenDashboard:
    """Dashboard for tracking token usage and costs."""
    
    def __init__(self) -> None:
        """Initialize token dashboard."""
        self.usage_history: List[TokenUsage] = []
        self.daily_stats: Dict[str, TokenUsageStats] = {}
    
    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_used: str,
        processing_time_ms: float,
        estimated_cost: float
    ) -> None:
        """Record token usage for a request."""
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_used=model_used,
            processing_time_ms=processing_time_ms,
            estimated_cost=estimated_cost,
            timestamp=datetime.utcnow().isoformat()
        )
        self.usage_history.append(usage)
        
        # Update daily stats
        today = datetime.utcnow().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = TokenUsageStats()
        
        stats = self.daily_stats[today]
        stats.total_prompt_tokens += prompt_tokens
        stats.total_completion_tokens += completion_tokens
        stats.total_tokens += usage.total_tokens
        stats.total_cost += estimated_cost
        stats.request_count += 1
        stats.avg_processing_time_ms = (
            (stats.avg_processing_time_ms * (stats.request_count - 1) + processing_time_ms)
            / stats.request_count
        )
        
        # Update model breakdown
        stats.model_breakdown[model_used] = stats.model_breakdown.get(model_used, 0) + 1
    
    def get_current_session_stats(self) -> TokenUsageStats:
        """Get stats for current session."""
        stats = TokenUsageStats()
        
        for usage in self.usage_history:
            stats.total_prompt_tokens += usage.prompt_tokens
            stats.total_completion_tokens += usage.completion_tokens
            stats.total_tokens += usage.total_tokens
            stats.total_cost += usage.estimated_cost
            stats.request_count += 1
            stats.model_breakdown[usage.model_used] = (
                stats.model_breakdown.get(usage.model_used, 0) + 1
            )
        
        if self.usage_history:
            processing_times = [u.processing_time_ms for u in self.usage_history]
            stats.avg_processing_time_ms = sum(processing_times) / len(processing_times)
        
        return stats
    
    def get_daily_stats(self, date: str = None) -> TokenUsageStats:
        """Get stats for a specific date."""
        if date is None:
            date = datetime.utcnow().date().isoformat()
        
        return self.daily_stats.get(date, TokenUsageStats())
    
    def get_last_request_stats(self) -> TokenUsage | None:
        """Get stats for the last request."""
        return self.usage_history[-1] if self.usage_history else None
    
    def clear_history(self) -> None:
        """Clear usage history."""
        self.usage_history.clear()


def format_token_dashboard(stats: TokenUsageStats) -> str:
    """Format token usage as dashboard display."""
    return f"""📊 **Token Usage Dashboard**

**Current Session:**
- **Prompt Tokens:** {stats.total_prompt_tokens:,}
- **Completion Tokens:** {stats.total_completion_tokens:,}
- **Total Tokens:** {stats.total_tokens:,}

**Cost & Performance:**
- **Estimated Cost:** ${stats.total_cost:.4f}
- **Avg Processing Time:** {stats.avg_processing_time_ms:.0f}ms
- **Requests:** {stats.request_count}

**Model Distribution:**
{chr(10).join(f"- {model}: {count} request(s)" for model, count in stats.model_breakdown.items())}"""


def format_token_usage_compact(usage: TokenUsage | None) -> str:
    """Format last token usage compactly."""
    if not usage:
        return "No requests yet"
    
    return (
        f"⚡ Last Request: {usage.prompt_tokens} + {usage.completion_tokens} = "
        f"{usage.total_tokens} tokens | ${usage.estimated_cost:.4f} | {usage.processing_time_ms:.0f}ms"
    )


class CostEstimator:
    """Estimate costs for different models and token counts."""
    
    # Cost per 1K tokens (in USD)
    MODEL_COSTS = {
        "gemma-7b": {"input": 0.0001, "output": 0.0003},
        "mistral-7b": {"input": 0.00015, "output": 0.0004},
        "mixtral-8x7b": {"input": 0.0002, "output": 0.0006},
        "llama-2-70b": {"input": 0.0005, "output": 0.0015},
        "llama-3-70b": {"input": 0.0008, "output": 0.0024},
        "gpt-4": {"input": 0.003, "output": 0.006},
        "claude-3-opus": {"input": 0.0015, "output": 0.0075},
    }
    
    @staticmethod
    def estimate_cost(
        model_id: str,
        prompt_tokens: int,
        estimated_completion_tokens: int = None
    ) -> float:
        """
        Estimate cost for a request.
        
        Args:
            model_id: Model identifier
            prompt_tokens: Number of prompt tokens
            estimated_completion_tokens: Estimated completion tokens (default: 60% of prompt)
            
        Returns:
            Estimated cost in USD
        """
        if estimated_completion_tokens is None:
            estimated_completion_tokens = int(prompt_tokens * 0.6)
        
        costs = CostEstimator.MODEL_COSTS.get(
            model_id,
            {"input": 0.0001, "output": 0.0003}  # Default costs
        )
        
        input_cost = (prompt_tokens / 1000) * costs["input"]
        output_cost = (estimated_completion_tokens / 1000) * costs["output"]
        
        return round(input_cost + output_cost, 6)
    
    @staticmethod
    def get_cost_comparison(
        prompt_tokens: int,
        completion_tokens: int = None
    ) -> Dict[str, float]:
        """Get cost comparison across all models."""
        if completion_tokens is None:
            completion_tokens = int(prompt_tokens * 0.6)
        
        comparison = {}
        for model_id in CostEstimator.MODEL_COSTS.keys():
            comparison[model_id] = CostEstimator.estimate_cost(
                model_id, prompt_tokens, completion_tokens
            )
        
        return dict(sorted(comparison.items(), key=lambda x: x[1]))
