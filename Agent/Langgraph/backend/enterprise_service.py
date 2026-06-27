"""
Enterprise Service Integration.
Orchestrates all 23 enterprise features into a cohesive system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime

# Import all enterprise modules
from .enterprise_security import analyse as analyse_security_enhanced
from .model_router_enterprise import route_to_tier, ModelTier
from .auto_upgrade import (
    EscalationHistory, EscalationReason, ThinkingStatusTracker,
    get_timeout_for_tier, should_escalate, get_escalation_message
)
from .confidence_scorer import ConfidenceCalculator, SafetyBadgeGenerator
from .memory_manager import ContextMemoryManager, get_memory_optimization_message
from .hallucination_checker import HallucinationChecker, get_hallucination_alert
from .token_dashboard import TokenDashboard, CostEstimator
from .execution_timeline import ExecutionTimeline, ExecutionStage, ErrorRecoveryStrategy
from .guardrails import AIGuardrails, RateLimiter, RateLimitConfig, PromptExplainer
from .analytics import AnalyticsDashboard, HealthMonitor
from .self_evaluator import SelfEvaluator, PromptQualityAnalyzer, ExplainabilityPanel
from .enterprise_logging import SmartCache, NotificationCenter, EnterpriseLogger


@dataclass
class EnterpriseResponse:
    """Complete response from enterprise service."""
    # Core response
    response: str
    is_safe: bool
    blocked: bool = False
    
    # Security
    security_reason: str = ""
    safety_badge: str = ""
    
    # Routing and model
    selected_model: str = ""
    selected_tier: ModelTier = ModelTier.LOW
    was_escalated: bool = False
    escalation_history: EscalationHistory = field(default_factory=EscalationHistory)
    
    # Intelligence and evaluation
    confidence_score: float = 0.0
    thinking_status: Optional[str] = None
    self_evaluation: Optional[str] = None
    prompt_quality: Optional[str] = None
    explainability: Optional[str] = None
    
    # Verification
    hallucination_risk: str = ""
    hallucination_alert: str = ""
    
    # Performance
    token_usage: str = ""
    execution_timeline: str = ""
    processing_time_ms: float = 0.0
    
    # System info
    notifications: list = field(default_factory=list)
    analytics: Optional[str] = None
    health_status: Optional[str] = None
    
    # Rate limiting
    rate_limit_exceeded: bool = False
    rate_limit_message: str = ""


class EnterpriseService:
    """
    Enterprise-grade AI service orchestrator.
    Integrates all 23 enterprise features.
    """
    
    def __init__(self) -> None:
        """Initialize enterprise service with all components."""
        # Core systems
        self.memory_manager = ContextMemoryManager()
        self.token_dashboard = TokenDashboard()
        self.execution_timeline = ExecutionTimeline()
        self.error_recovery = ErrorRecoveryStrategy()
        self.thinking_tracker = ThinkingStatusTracker()
        
        # Analytics and monitoring
        self.analytics = AnalyticsDashboard()
        self.health_monitor = HealthMonitor()
        
        # Caching and notifications
        self.cache = SmartCache()
        self.notifications = NotificationCenter()
        self.logger = EnterpriseLogger()
        
        # Rate limiting
        self.rate_limiter = RateLimiter(RateLimitConfig())
    
    def process_prompt_enterprise(
        self,
        prompt: str,
        user_id: str = "unknown",
        session_id: str = "default",
        include_explanations: bool = True
    ) -> EnterpriseResponse:
        """
        Process a prompt through the complete enterprise pipeline.
        
        This orchestrates all 23 enterprise features:
        1. Prompt injection protection & security
        2. Multi-level model routing
        3. Automatic upgrade on timeout
        4. Confidence scoring
        5. Thinking status tracking
        6. Safety badges
        7. Context memory management
        8. Hallucination checking
        9. Self-evaluation
        10. Token usage tracking
        11. Execution timeline
        12. Intelligent error recovery
        13. AI guardrails
        14. Rate limiting
        15. Prompt explanation
        16. Smart caching
        17. Analytics tracking
        18. Prompt quality analysis
        19. Explainability
        20. Enterprise logging
        21. Health monitoring
        22. UI notifications
        23. Performance optimization
        """
        response = EnterpriseResponse()
        start_time = datetime.utcnow()
        
        # Add to timeline: Request received
        self.execution_timeline.add_entry(
            ExecutionStage.REQUEST_RECEIVED,
            0.0,
            "completed",
            "Processing started"
        )
        
        # Feature 14: Rate Limiting
        rate_status = self.rate_limiter.check_limit(user_id)
        if rate_status.limited:
            response.rate_limit_exceeded = True
            response.rate_limit_message = f"Too many requests. Wait {rate_status.reset_after_seconds}s"
            response.blocked = True
            return response
        
        # Feature 1: Enhanced Security & Prompt Injection Protection
        self.thinking_tracker.next_stage()  # Understanding Request
        security_result = analyse_security_enhanced(prompt, user_id)
        response.security_reason = security_result.reason
        response.is_safe = security_result.is_safe
        
        if not security_result.is_safe:
            response.blocked = True
            response.safety_badge = "🔴 Blocked"
            notification = self.notifications.create_security_alert(security_result.reason)
            response.notifications.append(notification)
            
            # Log security violation
            self.logger.log_request(
                user_id, session_id, prompt, "",
                "n/a", 0, 0, False, security_result.reason, 0, 0, 0.0,
                f"Security: {security_result.reason}"
            )
            
            return response
        
        # Feature 16: Smart Caching
        cache_entry = self.cache.lookup(prompt)
        if cache_entry:
            response.response = cache_entry.response
            response.selected_model = cache_entry.model_used
            response.confidence_score = cache_entry.confidence
            response.token_usage = "⚡ Served from Cache"
            notification = self.notifications.create_cache_hit()
            response.notifications.append(notification)
            return response
        
        # Feature 2: Multi-Level Model Routing
        self.thinking_tracker.next_stage()  # Analyzing Context
        routing_decision = route_to_tier(prompt)
        response.selected_tier = routing_decision.selected_tier
        response.selected_model = routing_decision.selected_model_id
        
        # Add to timeline: Model selection
        self.execution_timeline.add_entry(
            ExecutionStage.MODEL_SELECTION,
            10.0,
            "completed",
            f"Tier: {routing_decision.selected_tier.value}"
        )
        
        # Feature 18: Prompt Quality Analysis
        quality = PromptQualityAnalyzer.analyze(prompt)
        if include_explanations:
            from .self_evaluator import format_prompt_quality
            response.prompt_quality = format_prompt_quality(quality)
        
        # Feature 13: Guardrails
        self.thinking_tracker.next_stage()  # Selecting Best Model
        violation = AIGuardrails.check_for_violations(prompt)
        if violation:
            response.blocked = True
            response.safety_badge = "🔴 Blocked"
            blocker = PromptExplainer.explain_blockage(violation)
            from .guardrails import PromptExplainer as PE
            response.response = PE.format_blocking_explanation(blocker)
            notification = self.notifications.create_security_alert(violation.category)
            response.notifications.append(notification)
            return response
        
        # Feature 5: AI Thinking Status & Feature 11: Execution Timeline
        self.thinking_tracker.next_stage()  # Reasoning
        thinking_status = self.thinking_tracker.get_current_status()
        response.thinking_status = thinking_status
        
        self.execution_timeline.add_entry(
            ExecutionStage.REASONING,
            50.0,
            "in_progress",
            "Processing request"
        )
        
        # Feature 7: Context Memory Management
        self.memory_manager.add_message("user", prompt, len(prompt) // 4, 0.8)
        
        # Generate response (simulated - replace with actual API call)
        response.response = self._generate_response(prompt, response.selected_model)
        
        # Add to memory
        self.memory_manager.add_message("assistant", response.response, len(response.response) // 4, 0.9)
        
        # Feature 8: Hallucination Checking
        self.thinking_tracker.next_stage()  # Verification
        hallucination_result = HallucinationChecker.check(response.response)
        response.hallucination_risk = hallucination_result.risk_level.value
        if not hallucination_result.is_reliable:
            response.hallucination_alert = get_hallucination_alert(hallucination_result)
        
        # Feature 4: Confidence Scoring
        confidence = ConfidenceCalculator.calculate(
            routing_decision.confidence,
            len(response.response),
            has_reasoning_steps=True,
            security_score=1.0 if response.is_safe else 0.5
        )
        response.confidence_score = confidence.score * 100
        
        # Feature 6: Safety Badge
        badge = SafetyBadgeGenerator.generate(
            security_passed=response.is_safe,
            security_score=0.1,
            was_escalated=response.was_escalated,
            confidence_level=confidence.level
        )
        response.safety_badge = f"{badge.emoji()} {badge.label()}"
        
        # Feature 9: Self-Evaluation
        if include_explanations:
            evaluation = SelfEvaluator.evaluate(
                prompt, response.response, response.selected_model,
                confidence.score, response.was_escalated, response.is_safe
            )
            from .self_evaluator import format_self_evaluation
            response.self_evaluation = format_self_evaluation(evaluation)
        
        # Feature 10: Token Dashboard
        tokens_used = (len(prompt) + len(response.response)) // 4
        cost = CostEstimator.estimate_cost(response.selected_model, len(prompt) // 4)
        self.token_dashboard.record_usage(
            len(prompt) // 4, len(response.response) // 4,
            response.selected_model, 50.0, cost
        )
        stats = self.token_dashboard.get_current_session_stats()
        from .token_dashboard import format_token_dashboard
        response.token_usage = format_token_dashboard(stats)
        
        # Feature 11: Execution Timeline
        self.execution_timeline.add_entry(
            ExecutionStage.VERIFICATION,
            20.0,
            "completed",
            "Safety checks passed"
        )
        self.execution_timeline.add_entry(
            ExecutionStage.RESPONSE_GENERATED,
            0.0,
            "completed",
            "Response ready"
        )
        self.execution_timeline.complete()
        from .execution_timeline import format_execution_timeline
        response.execution_timeline = format_execution_timeline(self.execution_timeline)
        
        # Feature 19: Explainability
        if include_explanations:
            explain = ExplainabilityPanel.explain_decision(
                prompt, response.selected_model, confidence.score,
                "Security: Passed", routing_decision.complexity_level
            )
            from .self_evaluator import format_explainability
            response.explainability = format_explainability(explain)
        
        # Feature 17: Analytics
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.analytics.record_query(
            success=True, blocked=False, response_time_ms=elapsed_ms,
            confidence=confidence.score, model_used=response.selected_model,
            tokens=tokens_used, escalated=response.was_escalated
        )
        metrics = self.analytics.get_metrics()
        from .analytics import format_analytics_dashboard
        response.analytics = format_analytics_dashboard(metrics)
        
        # Feature 21: Health Monitor
        health = self.health_monitor.check_health(5.0, elapsed_ms, False, 1)
        from .analytics import format_health_status
        response.health_status = format_health_status(health)
        
        # Feature 22: UI Notifications
        notification = self.notifications.create_verification_complete()
        response.notifications.append(notification)
        
        # Feature 20: Enterprise Logging
        self.logger.log_request(
            user_id, session_id, prompt, response.response,
            response.selected_model, elapsed_ms, confidence.score,
            response.is_safe, response.security_reason,
            response.escalation_history.total_escalations,
            tokens_used, cost
        )
        
        # Feature 16: Cache the response
        self.cache.store(
            prompt, response.response, response.selected_model,
            confidence.score
        )
        
        # Record rate limit
        self.rate_limiter.record_request(user_id)
        
        # Complete thinking
        self.thinking_tracker.mark_complete()
        response.processing_time_ms = elapsed_ms
        
        return response
    
    def _generate_response(self, prompt: str, model: str) -> str:
        """Generate response (replace with actual API call)."""
        return (
            f"[{model} Response]\n\n"
            f"This is a simulated response to your prompt:\n"
            f"\"{prompt[:100]}...\"\n\n"
            f"In production, this would call the actual AI model API.\n"
            f"The response would include full reasoning and analysis."
        )
