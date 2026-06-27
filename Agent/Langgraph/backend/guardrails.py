"""
AI Guardrails and Rate Limiting System.
Enforces safety policies and prevents abuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import re


@dataclass
class GuardrailViolation:
    """A detected guardrail violation."""
    category: str
    severity: str
    pattern_matched: str
    reason: str


class AIGuardrails:
    """Comprehensive guardrails for AI responses and user inputs."""
    
    # Patterns for prohibited content
    PROHIBITED_PATTERNS = {
        "hate_speech": [
            r"\b(racist|sexist|homophobic|transphobic|xenophobic)\b",
            r"\b(slur|slurs|derogatory|epithet)\b",
        ],
        "violence_instructions": [
            r"how.{1,10}(kill|hurt|harm|torture|poison|exploit)",
            r"create.{1,10}(weapon|bomb|explosive|toxin)",
            r"instructions?.{1,10}(kill|attack|bomb)",
        ],
        "malware_requests": [
            r"(malware|ransomware|virus|trojan|keylogger|botnet|worm)",
            r"execute.{1,10}(malicious|harmful|destructive)",
            r"create.{1,10}(backdoor|exploit|vulnerability)",
        ],
        "credential_theft": [
            r"(phishing|spear.?phishing|credential harvest|credential theft)",
            r"social.{1,10}engineer",
            r"fake.{1,10}(email|website|login|credential)",
        ],
        "illegal_activity": [
            r"(drug|cocaine|heroin|methamphetamine|fentanyl).{1,10}(synthesis|cook|produce|manufacture)",
            r"(hack|breach|exploit).{1,10}(bank|credit|financial)",
            r"money.{1,10}(launder|laundering)",
        ]
    }
    
    @staticmethod
    def check_for_violations(content: str) -> Optional[GuardrailViolation]:
        """
        Check content for guardrail violations.
        
        Args:
            content: Content to check
            
        Returns:
            GuardrailViolation if found, None otherwise
        """
        for category, patterns in AIGuardrails.PROHIBITED_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return GuardrailViolation(
                        category=category,
                        severity="high",
                        pattern_matched=pattern,
                        reason=f"Detected prohibited content: {category}"
                    )
        
        return None
    
    @staticmethod
    def get_refusal_message(violation: GuardrailViolation) -> str:
        """Generate a friendly refusal message."""
        messages = {
            "hate_speech": (
                "I can't assist with that request as it contains hateful content. "
                "I'm designed to be respectful to all people. "
                "Is there something constructive I can help you with instead?"
            ),
            "violence_instructions": (
                "I can't provide instructions for harming people or creating weapons. "
                "If you're interested in security or safety topics, I'd be happy to discuss those "
                "in an educational context instead."
            ),
            "malware_requests": (
                "I can't help with creating malicious software or exploits. "
                "However, I can discuss cybersecurity concepts, defensive strategies, "
                "or ethical hacking practices if you're interested."
            ),
            "credential_theft": (
                "I can't help with phishing or credential theft schemes. "
                "I can help you understand how to protect against these threats instead."
            ),
            "illegal_activity": (
                "I can't assist with illegal activities. "
                "If you have questions about legal topics or legitimate uses, I'm happy to help."
            ),
        }
        
        return messages.get(
            violation.category,
            "I can't assist with that request. Is there something else I can help you with?"
        )


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 20
    time_window_seconds: int = 60
    burst_size: int = 5


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    remaining_requests: int
    reset_after_seconds: int
    limited: bool


class RateLimiter:
    """Rate limiting to prevent abuse."""
    
    def __init__(self, config: RateLimitConfig = RateLimitConfig()) -> None:
        """Initialize rate limiter."""
        self.config = config
        self.request_history: Dict[str, List[datetime]] = defaultdict(list)
    
    def check_limit(self, user_id: str) -> RateLimitStatus:
        """
        Check if request is within rate limits.
        
        Args:
            user_id: User identifier
            
        Returns:
            RateLimitStatus with current state
        """
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.config.time_window_seconds)
        
        # Clean old requests
        if user_id in self.request_history:
            self.request_history[user_id] = [
                req_time for req_time in self.request_history[user_id]
                if req_time > cutoff_time
            ]
        
        recent_requests = len(self.request_history[user_id])
        limited = recent_requests >= self.config.max_requests
        
        # Calculate reset time
        if self.request_history[user_id]:
            oldest_request = self.request_history[user_id][0]
            reset_after = (oldest_request + timedelta(seconds=self.config.time_window_seconds) - now).total_seconds()
            reset_after = max(0, int(reset_after))
        else:
            reset_after = 0
        
        return RateLimitStatus(
            remaining_requests=max(0, self.config.max_requests - recent_requests),
            reset_after_seconds=reset_after,
            limited=limited
        )
    
    def record_request(self, user_id: str) -> None:
        """Record a request for rate limiting."""
        self.request_history[user_id].append(datetime.utcnow())
    
    def get_limit_exceeded_message(self, status: RateLimitStatus) -> str:
        """Generate rate limit exceeded message."""
        return (
            f"⏸️ Too Many Requests\n\n"
            f"You've made too many requests in a short time.\n"
            f"Please wait **{status.reset_after_seconds} seconds** before trying again.\n\n"
            f"*Rate Limit: {self.config.max_requests} requests per {self.config.time_window_seconds} seconds*"
        )


@dataclass
class PromptBlockingReason:
    """Reason why a prompt was blocked with suggestions."""
    is_unsafe: bool
    reason: str
    category: str
    suggestions: List[str]


class PromptExplainer:
    """Explain why a prompt was blocked and suggest alternatives."""
    
    @staticmethod
    def explain_blockage(violation: GuardrailViolation) -> PromptBlockingReason:
        """
        Explain why a prompt was blocked and provide suggestions.
        
        Args:
            violation: The detected violation
            
        Returns:
            PromptBlockingReason with explanation and suggestions
        """
        suggestions_map = {
            "hate_speech": [
                "Focus on the actual topic without derogatory language",
                "Use respectful language when discussing any group",
                "Ask about the issue objectively"
            ],
            "violence_instructions": [
                "Ask about defensive security instead",
                "Learn about the topic in an educational context",
                "Discuss prevention and protection measures"
            ],
            "malware_requests": [
                "Ask about cybersecurity principles",
                "Learn about how systems are protected",
                "Discuss ethical security practices"
            ],
            "credential_theft": [
                "Learn about security best practices",
                "Ask how to protect your accounts",
                "Understand authentication systems"
            ],
            "illegal_activity": [
                "Ask about the legal aspects",
                "Learn about legitimate uses",
                "Understand the topic from an educational perspective"
            ],
        }
        
        suggestions = suggestions_map.get(violation.category, [
            "Rephrase your question more carefully",
            "Ask about the topic in a different way",
            "Focus on legitimate use cases"
        ])
        
        return PromptBlockingReason(
            is_unsafe=True,
            reason=f"Your request appears to involve {violation.category.replace('_', ' ')}",
            category=violation.category,
            suggestions=suggestions
        )
    
    @staticmethod
    def format_blocking_explanation(reason: PromptBlockingReason) -> str:
        """Format blocking explanation for display."""
        message = f"""🚫 **Request Blocked**

**Why:** {reason.reason}

**This interaction has been safely terminated.**

**How to rewrite safely:**
"""
        for i, suggestion in enumerate(reason.suggestions[:3], 1):
            message += f"\n{i}. {suggestion}"
        
        message += "\n\nPlease enter a valid request."
        
        return message
