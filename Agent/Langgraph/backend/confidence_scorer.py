"""
Confidence Scoring and Safety Badge System.
Calculates confidence levels and generates safety indicators.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List
from datetime import datetime


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    HIGH = "high"  # 90-100%
    MEDIUM = "medium"  # 70-89%
    LOW = "low"  # Below 70%


class SafetyStatus(Enum):
    """Safety status indicators."""
    SAFE = "safe"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


@dataclass
class ConfidenceScore:
    """Confidence assessment for a response."""
    score: float  # 0.0 to 1.0
    level: ConfidenceLevel
    reasoning: List[str]
    can_verify: bool = True
    
    def percentage(self) -> int:
        """Get confidence as percentage."""
        return int(self.score * 100)
    
    def emoji(self) -> str:
        """Get emoji representation."""
        emojis = {
            ConfidenceLevel.HIGH: "🟢",
            ConfidenceLevel.MEDIUM: "🟡",
            ConfidenceLevel.LOW: "🔴"
        }
        return emojis.get(self.level, "⚪")


@dataclass
class SafetyBadge:
    """Safety status badge for a response."""
    status: SafetyStatus
    timestamp: str
    reason: str = ""
    escalation_count: int = 0
    security_passed: bool = True
    
    def emoji(self) -> str:
        """Get emoji representation."""
        emojis = {
            SafetyStatus.SAFE: "🟢",
            SafetyStatus.NEEDS_REVIEW: "🟡",
            SafetyStatus.BLOCKED: "🔴"
        }
        return emojis.get(self.status, "⚪")
    
    def label(self) -> str:
        """Get readable label."""
        labels = {
            SafetyStatus.SAFE: "Safe",
            SafetyStatus.NEEDS_REVIEW: "Needs Review",
            SafetyStatus.BLOCKED: "Blocked"
        }
        return labels.get(self.status, "Unknown")


class ConfidenceCalculator:
    """Calculate confidence scores based on multiple factors."""
    
    @staticmethod
    def calculate(
        model_capability: float,
        response_length: int,
        has_reasoning_steps: bool = False,
        was_escalated: bool = False,
        security_score: float = 1.0,
        execution_errors: int = 0
    ) -> ConfidenceScore:
        """
        Calculate confidence score based on multiple factors.
        
        Args:
            model_capability: Capability score of selected model (0-1)
            response_length: Length of generated response in characters
            has_reasoning_steps: Whether response includes reasoning
            was_escalated: Whether request was escalated
            security_score: Security analysis score (0-1)
            execution_errors: Number of errors during execution
            
        Returns:
            ConfidenceScore with calculated score and level
        """
        # Base score from model capability
        base_score = model_capability * 0.4
        
        # Response length factor (penalize very short responses)
        length_factor = min(1.0, response_length / 1000.0) * 0.25
        
        # Reasoning factor
        reasoning_factor = 0.15 if has_reasoning_steps else 0.0
        
        # Escalation penalty
        escalation_penalty = 0.1 if was_escalated else 0.0
        
        # Security factor
        security_factor = security_score * 0.15
        
        # Error penalty
        error_penalty = min(0.1, execution_errors * 0.05)
        
        # Calculate final score
        score = (
            base_score +
            length_factor +
            reasoning_factor +
            security_factor -
            escalation_penalty -
            error_penalty
        )
        
        # Normalize to 0-1 range
        score = max(0.0, min(1.0, score))
        
        # Determine level
        if score >= 0.90:
            level = ConfidenceLevel.HIGH
        elif score >= 0.70:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        # Build reasoning
        reasoning = ConfidenceCalculator._build_reasoning(
            score, level, model_capability, response_length,
            has_reasoning_steps, was_escalated, execution_errors
        )
        
        return ConfidenceScore(
            score=round(score, 4),
            level=level,
            reasoning=reasoning,
            can_verify=score < 0.85  # Flag for verification if not very confident
        )
    
    @staticmethod
    def _build_reasoning(
        score: float,
        level: ConfidenceLevel,
        model_capability: float,
        response_length: int,
        has_reasoning: bool,
        escalated: bool,
        errors: int
    ) -> List[str]:
        """Build reasoning explanation for confidence score."""
        reasons = []
        
        # Positive factors
        if model_capability > 0.8:
            reasons.append("Processed by high-capability model")
        if response_length > 500:
            reasons.append("Comprehensive response generated")
        if has_reasoning:
            reasons.append("Includes detailed reasoning steps")
        if errors == 0:
            reasons.append("Completed without errors")
        
        # Negative factors
        if escalated:
            reasons.append("Request required model escalation")
        if errors > 0:
            reasons.append(f"Encountered {errors} processing issue(s)")
        if response_length < 100:
            reasons.append("Response is relatively brief")
        if level == ConfidenceLevel.LOW:
            reasons.append("Recommend human verification")
        
        return reasons


class SafetyBadgeGenerator:
    """Generate safety badges for responses."""
    
    @staticmethod
    def generate(
        security_passed: bool,
        security_score: float,
        was_escalated: bool = False,
        has_review_flags: bool = False,
        confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    ) -> SafetyBadge:
        """
        Generate safety badge for a response.
        
        Args:
            security_passed: Whether security checks passed
            security_score: Security risk score (0-1, lower is better)
            was_escalated: Whether request was escalated
            has_review_flags: Whether response has review flags
            confidence_level: Confidence level of the response
            
        Returns:
            SafetyBadge with appropriate status
        """
        if not security_passed:
            return SafetyBadge(
                status=SafetyStatus.BLOCKED,
                timestamp=datetime.utcnow().isoformat(),
                reason="Security check failed",
                security_passed=False
            )
        
        if has_review_flags or confidence_level == ConfidenceLevel.LOW:
            return SafetyBadge(
                status=SafetyStatus.NEEDS_REVIEW,
                timestamp=datetime.utcnow().isoformat(),
                reason="Response requires human verification",
                escalation_count=1 if was_escalated else 0,
                security_passed=True
            )
        
        return SafetyBadge(
            status=SafetyStatus.SAFE,
            timestamp=datetime.utcnow().isoformat(),
            reason="All safety checks passed",
            escalation_count=1 if was_escalated else 0,
            security_passed=True
        )


def format_confidence_display(confidence: ConfidenceScore) -> str:
    """Format confidence score for display."""
    bar_length = 20
    filled = int((confidence.score / 1.0) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    return f"""**Confidence Score**

{confidence.emoji()} **{confidence.percentage()}%**

[{bar}]

**Level:** {confidence.level.value.title()}

**Reasoning:**
{chr(10).join(f"• {r}" for r in confidence.reasoning)}

{"⚠️ *This answer may require human verification.*" if confidence.can_verify else "✅ *High confidence answer*"}"""


def format_safety_badge(badge: SafetyBadge) -> str:
    """Format safety badge for display."""
    status_label = badge.label()
    reason_text = f"*{badge.reason}*" if badge.reason else ""
    
    return f"{badge.emoji()} **{status_label}** {reason_text}"
