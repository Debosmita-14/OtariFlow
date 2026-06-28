"""
Execution Timeline and Error Recovery System.
Tracks request processing pipeline and handles errors gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class ExecutionStage(Enum):
    """Stages in request execution pipeline."""
    REQUEST_RECEIVED = "Request Received"
    SECURITY_CHECK = "Security Check"
    INTENT_CLASSIFICATION = "Intent Classification"
    MODEL_SELECTION = "Model Selection"
    REASONING = "Reasoning"
    VERIFICATION = "Verification"
    RESPONSE_GENERATED = "Response Generated"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TimelineEntry:
    """Single entry in execution timeline."""
    stage: ExecutionStage
    timestamp: str
    duration_ms: float
    status: str  # "pending", "in_progress", "completed", "failed"
    details: str = ""
    error: Optional[str] = None


@dataclass
class ExecutionTimeline:
    """Complete execution timeline for a request."""
    entries: List[TimelineEntry] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    total_duration_ms: float = 0.0
    
    def add_entry(
        self,
        stage: ExecutionStage,
        duration_ms: float,
        status: str,
        details: str = "",
        error: Optional[str] = None
    ) -> None:
        """Add timeline entry."""
        entry = TimelineEntry(
            stage=stage,
            timestamp=datetime.utcnow().isoformat(),
            duration_ms=duration_ms,
            status=status,
            details=details,
            error=error
        )
        self.entries.append(entry)
        
        if not self.start_time and entry.status == "in_progress":
            self.start_time = entry.timestamp
    
    def complete(self) -> None:
        """Mark timeline as complete."""
        self.end_time = datetime.utcnow().isoformat()
        if self.entries:
            # Calculate total duration
            self.total_duration_ms = sum(e.duration_ms for e in self.entries)


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_type: str
    message: str
    severity: ErrorSeverity
    model_attempted: Optional[str] = None
    retry_count: int = 0
    suggestions: List[str] = field(default_factory=list)


class ErrorRecoveryStrategy:
    """Strategy for handling and recovering from errors."""
    
    def __init__(self) -> None:
        """Initialize error recovery."""
        self.max_retries = 3
        self.error_history: List[ErrorContext] = []
    
    def handle_error(
        self,
        error_type: str,
        message: str,
        model_attempted: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle an error and determine recovery strategy.
        
        Returns:
            Dictionary with recovery action and details
        """
        # Classify error severity
        severity = self._classify_severity(error_type)
        
        # Determine retry strategy
        can_retry = severity != ErrorSeverity.CRITICAL
        should_escalate = len(self.error_history) > 0 or severity == ErrorSeverity.CRITICAL
        
        # Generate recovery suggestions
        suggestions = self._get_recovery_suggestions(error_type)
        
        context = ErrorContext(
            error_type=error_type,
            message=message,
            severity=severity,
            model_attempted=model_attempted,
            suggestions=suggestions
        )
        self.error_history.append(context)
        
        return {
            "can_retry": can_retry,
            "should_escalate": should_escalate,
            "suggestions": suggestions,
            "error_severity": severity.value,
            "message": self._get_user_message(severity, error_type)
        }
    
    def _classify_severity(self, error_type: str) -> ErrorSeverity:
        """Classify error severity."""
        critical_errors = {
            "auth_failed", "invalid_key", "quota_exceeded",
            "service_down", "malicious_request"
        }
        high_errors = {
            "timeout", "rate_limit", "model_unavailable"
        }
        
        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        if error_type in high_errors:
            return ErrorSeverity.HIGH
        if error_type == "invalid_input":
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    def _get_recovery_suggestions(self, error_type: str) -> List[str]:
        """Get recovery suggestions for error type."""
        suggestions_map = {
            "timeout": [
                "Try with a simpler query",
                "Request will be escalated to a higher-tier model",
                "Split your request into smaller parts"
            ],
            "rate_limit": [
                "Wait a few seconds before retrying",
                "Reduce frequency of requests",
                "Contact support for higher rate limits"
            ],
            "model_unavailable": [
                "Trying alternative model...",
                "Service should be restored shortly",
                "Please try again in a moment"
            ],
            "invalid_input": [
                "Check your input format",
                "Ensure you're not using restricted patterns",
                "Simplify your request"
            ],
            "api_error": [
                "This appears to be a temporary issue",
                "Our team has been notified",
                "Please try again shortly"
            ]
        }
        
        return suggestions_map.get(error_type, ["Please try again"])
    
    def _get_user_message(self, severity: ErrorSeverity, error_type: str) -> str:
        """Get user-friendly error message."""
        if severity == ErrorSeverity.CRITICAL:
            return "⚠️ The AI service is temporarily unavailable. Please try again shortly."
        
        if severity == ErrorSeverity.HIGH:
            return f"⏳ The service is experiencing high load. Attempting recovery..."
        
        return f"ℹ️ {error_type}: Retrying with alternative approach..."
    
    def should_retry(self) -> bool:
        """Determine if retry should be attempted."""
        if not self.error_history:
            return True
        
        recent_errors = self.error_history[-3:]
        retry_count = len(recent_errors)
        
        return retry_count < self.max_retries
    
    def clear_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()


def format_execution_timeline(timeline: ExecutionTimeline) -> str:
    """Format execution timeline for display."""
    lines = ["⚙️ **Execution Timeline**\n"]
    
    for entry in timeline.entries:
        # Status indicator
        indicator = {
            "completed": "✅",
            "in_progress": "⏳",
            "failed": "❌",
            "pending": "⏹️"
        }.get(entry.status, "•")
        
        # Format entry
        lines.append(
            f"{indicator} **{entry.stage.value}** "
            f"({entry.duration_ms:.0f}ms)"
        )
        
        if entry.details:
            lines.append(f"   └─ {entry.details}")
        
        if entry.error:
            lines.append(f"   ❌ Error: {entry.error}")
    
    if timeline.total_duration_ms > 0:
        lines.append(f"\n⏱️ **Total Time:** {timeline.total_duration_ms:.0f}ms")
    
    return "\n".join(lines)


def format_error_message(recovery: Dict[str, Any]) -> str:
    """Format error recovery message."""
    message = recovery["message"] + "\n\n"
    
    if recovery["suggestions"]:
        message += "**Try this:**\n"
        for suggestion in recovery["suggestions"][:3]:
            message += f"• {suggestion}\n"
    
    return message
