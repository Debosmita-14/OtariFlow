"""
Automatic Model Upgrade System.
Escalates requests to higher-tier models if they timeout.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from .model_router_enterprise import ModelTier, TIER_PROFILES


class EscalationReason(Enum):
    """Reasons for model escalation."""
    TIMEOUT = "timeout"
    PARTIAL_RESPONSE = "partial_response"
    QUALITY_THRESHOLD = "quality_threshold"
    ERROR = "error"


@dataclass
class EscalationConfig:
    """Configuration for auto-escalation."""
    # Timeout thresholds in seconds
    low_tier_timeout: float = 8.0
    medium_tier_timeout: float = 12.0
    high_tier_timeout: float = 20.0
    
    # Quality thresholds
    min_confidence_score: float = 0.6
    min_response_length: int = 50
    
    # Escalation limits
    max_escalations: int = 2
    escalation_backoff_ms: int = 500


@dataclass
class EscalationStep:
    """Represents an escalation event."""
    from_tier: ModelTier
    to_tier: ModelTier
    reason: EscalationReason
    timestamp: str
    elapsed_ms: float
    message: str


@dataclass
class EscalationHistory:
    """Track escalation events during processing."""
    steps: List[EscalationStep] = field(default_factory=list)
    total_escalations: int = 0
    final_tier: ModelTier = ModelTier.LOW
    total_time_ms: float = 0.0
    
    def add_escalation(
        self,
        from_tier: ModelTier,
        to_tier: ModelTier,
        reason: EscalationReason,
        elapsed_ms: float,
        message: str = ""
    ) -> None:
        """Record an escalation step."""
        step = EscalationStep(
            from_tier=from_tier,
            to_tier=to_tier,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
            elapsed_ms=elapsed_ms,
            message=message
        )
        self.steps.append(step)
        self.total_escalations += 1
        self.final_tier = to_tier


def get_timeout_for_tier(tier: ModelTier, config: EscalationConfig = EscalationConfig()) -> float:
    """Get timeout duration for a model tier."""
    timeout_map = {
        ModelTier.LOW: config.low_tier_timeout,
        ModelTier.MEDIUM: config.medium_tier_timeout,
        ModelTier.HIGH: config.high_tier_timeout
    }
    return timeout_map.get(tier, config.low_tier_timeout)


def get_next_tier(current_tier: ModelTier) -> Optional[ModelTier]:
    """Get the next tier up for escalation."""
    escalation_path = {
        ModelTier.LOW: ModelTier.MEDIUM,
        ModelTier.MEDIUM: ModelTier.HIGH,
        ModelTier.HIGH: None  # No tier above HIGH
    }
    return escalation_path.get(current_tier)


def should_escalate(
    current_tier: ModelTier,
    elapsed_ms: float,
    config: EscalationConfig = EscalationConfig()
) -> bool:
    """
    Determine if a request should be escalated based on timeout.
    
    Args:
        current_tier: The current model tier
        elapsed_ms: Time elapsed in milliseconds
        config: Escalation configuration
        
    Returns:
        True if escalation is needed
    """
    timeout_sec = get_timeout_for_tier(current_tier, config)
    elapsed_sec = elapsed_ms / 1000.0
    
    return elapsed_sec >= timeout_sec


def get_escalation_message(from_tier: ModelTier, reason: EscalationReason) -> str:
    """Generate a user-friendly escalation message."""
    from_profile = TIER_PROFILES[from_tier]
    reason_text = {
        EscalationReason.TIMEOUT: "taking longer than expected",
        EscalationReason.PARTIAL_RESPONSE: "needing deeper analysis",
        EscalationReason.QUALITY_THRESHOLD: "requiring higher accuracy",
        EscalationReason.ERROR: "encountering a processing issue"
    }.get(reason, "needing optimization")
    
    return f"""⚡ Optimizing Response

The current model is {reason_text}.

Upgrading to a more capable AI model for faster and more accurate reasoning...

*Processing will continue automatically without any delay.*"""


@dataclass
class ThinkingStage:
    """Represents a thinking/processing stage."""
    stage_name: str
    emoji: str
    description: str
    is_complete: bool = False
    duration_ms: float = 0.0


class ThinkingStatusTracker:
    """Track and display thinking stages during processing."""
    
    STAGES = [
        ThinkingStage("Understanding Request", "🔍", "Parsing your input..."),
        ThinkingStage("Analyzing Context", "📊", "Gathering relevant information..."),
        ThinkingStage("Selecting Best Model", "🤖", "Choosing optimal AI model..."),
        ThinkingStage("Reasoning", "⚙️", "Processing with intelligence..."),
        ThinkingStage("Generating Response", "✍️", "Formulating answer..."),
        ThinkingStage("Verification", "✅", "Ensuring quality and safety..."),
        ThinkingStage("Completed", "🎉", "Ready to display!")
    ]
    
    def __init__(self) -> None:
        """Initialize thinking tracker."""
        self.stages = [stage for stage in self.STAGES]
        self.current_index = 0
        self.start_times: dict[str, float] = {}
    
    def next_stage(self) -> Optional[ThinkingStage]:
        """Advance to next stage."""
        if self.current_index < len(self.stages):
            stage = self.stages[self.current_index]
            self.start_times[stage.stage_name] = datetime.utcnow().timestamp()
            self.current_index += 1
            return stage
        return None
    
    def get_current_status(self) -> str:
        """Get current thinking status as formatted string."""
        lines = ["🧠 **AI Thinking Status:**\n"]
        for i, stage in enumerate(self.stages):
            if i < self.current_index:
                symbol = "✅"
                status = "Complete"
            elif i == self.current_index:
                symbol = "⏳"
                status = "In Progress..."
            else:
                symbol = "⏹️"
                status = "Pending"
            
            lines.append(f"{symbol} **{stage.stage_name}** - {status}")
        
        return "\n".join(lines)
    
    def get_progress_percentage(self) -> int:
        """Get progress as percentage."""
        return int((self.current_index / len(self.stages)) * 100)
    
    def mark_complete(self) -> None:
        """Mark all stages as complete."""
        self.current_index = len(self.stages)


# Animation frames for thinking indicators
THINKING_FRAMES = [
    "⠋",
    "⠙",
    "⠹",
    "⠸",
    "⠼",
    "⠴",
    "⠦",
    "⠧",
    "⠇",
    "⠏"
]


def get_animated_thinking(frame_index: int = 0) -> str:
    """Get animated thinking indicator."""
    frame = THINKING_FRAMES[frame_index % len(THINKING_FRAMES)]
    return f"{frame} Processing..."
