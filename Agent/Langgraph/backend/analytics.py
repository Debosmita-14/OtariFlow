"""
Analytics Dashboard and Health Monitoring.
Tracks system performance and user metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any
from enum import Enum
from collections import defaultdict


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnalyticsMetrics:
    """Aggregated analytics metrics."""
    total_queries: int = 0
    successful_queries: int = 0
    blocked_queries: int = 0
    failed_queries: int = 0
    avg_response_time_ms: float = 0.0
    avg_confidence: float = 0.0
    model_distribution: Dict[str, int] = field(default_factory=dict)
    token_consumption: int = 0
    escalation_count: int = 0
    cache_hit_ratio: float = 0.0
    
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100
    
    def block_rate(self) -> float:
        """Calculate block rate percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.blocked_queries / self.total_queries) * 100


@dataclass
class HealthMetrics:
    """System health metrics."""
    api_latency_ms: float
    avg_response_time_ms: float
    failure_rate: float
    active_users: int
    model_availability: Dict[str, bool] = field(default_factory=dict)
    last_check: str = ""
    
    def overall_status(self) -> HealthStatus:
        """Determine overall health status."""
        failure_critical = self.failure_rate > 0.1  # > 10%
        latency_high = self.api_latency_ms > 5000  # > 5s
        unavailable_models = sum(1 for available in self.model_availability.values() if not available)
        
        if failure_critical or latency_high or unavailable_models > 1:
            return HealthStatus.CRITICAL
        
        if self.failure_rate > 0.05 or self.api_latency_ms > 3000 or unavailable_models == 1:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY


class AnalyticsDashboard:
    """Track and report on system analytics."""
    
    def __init__(self) -> None:
        """Initialize analytics dashboard."""
        self.metrics = AnalyticsMetrics()
        self.hourly_data: Dict[str, AnalyticsMetrics] = {}
        self.response_times: List[float] = []
        self.confidence_scores: List[float] = []
    
    def record_query(
        self,
        success: bool,
        blocked: bool,
        response_time_ms: float,
        confidence: float = 0.0,
        model_used: str = "unknown",
        tokens: int = 0,
        escalated: bool = False,
        cache_hit: bool = False
    ) -> None:
        """Record query metrics."""
        self.metrics.total_queries += 1
        
        if blocked:
            self.metrics.blocked_queries += 1
        elif success:
            self.metrics.successful_queries += 1
        else:
            self.metrics.failed_queries += 1
        
        self.response_times.append(response_time_ms)
        self.confidence_scores.append(confidence)
        
        self.metrics.model_distribution[model_used] = (
            self.metrics.model_distribution.get(model_used, 0) + 1
        )
        
        self.metrics.token_consumption += tokens
        
        if escalated:
            self.metrics.escalation_count += 1
        
        # Update averages
        self.metrics.avg_response_time_ms = sum(self.response_times) / len(self.response_times)
        self.metrics.avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores)
        
        # Update cache hit ratio
        if cache_hit:
            cache_hits = sum(1 for _ in self.response_times if _ == 0)  # Simplified
            self.metrics.cache_hit_ratio = cache_hits / self.metrics.total_queries if self.metrics.total_queries > 0 else 0.0
    
    def get_metrics(self) -> AnalyticsMetrics:
        """Get current analytics metrics."""
        return self.metrics
    
    def get_hourly_metrics(self) -> Dict[str, AnalyticsMetrics]:
        """Get metrics by hour."""
        return self.hourly_data


class HealthMonitor:
    """Monitor AI system health."""
    
    def __init__(self) -> None:
        """Initialize health monitor."""
        self.api_latencies: List[float] = []
        self.response_times: List[float] = []
        self.failures: int = 0
        self.total_checks: int = 0
        self.model_status: Dict[str, bool] = {
            "gemma-7b": True,
            "mixtral-8x7b": True,
            "llama-3-70b": True,
            "gpt-4": True,
        }
    
    def check_health(
        self,
        api_latency_ms: float,
        response_time_ms: float,
        failed: bool = False,
        active_users: int = 0
    ) -> HealthMetrics:
        """
        Perform health check.
        
        Args:
            api_latency_ms: API response latency
            response_time_ms: Model response time
            failed: Whether request failed
            active_users: Number of active users
            
        Returns:
            HealthMetrics for current state
        """
        self.api_latencies.append(api_latency_ms)
        self.response_times.append(response_time_ms)
        self.total_checks += 1
        
        if failed:
            self.failures += 1
        
        # Keep only last 100 measurements
        if len(self.api_latencies) > 100:
            self.api_latencies.pop(0)
            self.response_times.pop(0)
        
        failure_rate = self.failures / self.total_checks if self.total_checks > 0 else 0.0
        avg_latency = sum(self.api_latencies) / len(self.api_latencies) if self.api_latencies else 0.0
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        return HealthMetrics(
            api_latency_ms=avg_latency,
            avg_response_time_ms=avg_response_time,
            failure_rate=failure_rate,
            active_users=active_users,
            model_availability=self.model_status.copy(),
            last_check=datetime.utcnow().isoformat()
        )
    
    def set_model_status(self, model: str, available: bool) -> None:
        """Update model availability status."""
        if model in self.model_status:
            self.model_status[model] = available


def format_analytics_dashboard(metrics: AnalyticsMetrics) -> str:
    """Format analytics for display."""
    success_rate = metrics.success_rate()
    block_rate = metrics.block_rate()
    
    model_list = "\n".join(
        f"- {model}: {count}" for model, count in metrics.model_distribution.items()
    )
    
    return f"""📊 **AI Analytics Dashboard**

**Query Statistics:**
- **Total Queries:** {metrics.total_queries}
- **Successful:** {metrics.successful_queries} ({success_rate:.1f}%)
- **Blocked:** {metrics.blocked_queries} ({block_rate:.1f}%)
- **Failed:** {metrics.failed_queries}

**Performance:**
- **Avg Response Time:** {metrics.avg_response_time_ms:.0f}ms
- **Avg Confidence:** {metrics.avg_confidence:.1%}
- **Escalations:** {metrics.escalation_count}
- **Cache Hit Ratio:** {metrics.cache_hit_ratio:.1%}

**Resource Usage:**
- **Total Tokens:** {metrics.token_consumption:,}

**Model Distribution:**
{model_list if model_list else "- No data yet"}"""


def format_health_status(health: HealthMetrics) -> str:
    """Format health status for display."""
    status = health.overall_status()
    status_emoji = {
        HealthStatus.HEALTHY: "🟢",
        HealthStatus.WARNING: "🟡",
        HealthStatus.CRITICAL: "🔴"
    }.get(status, "⚪")
    
    model_status_str = "\n".join(
        f"{'✅' if available else '❌'} {model}"
        for model, available in health.model_availability.items()
    )
    
    return f"""{status_emoji} **AI System Health**

**Status:** {status.value.upper()}

**Metrics:**
- **API Latency:** {health.api_latency_ms:.0f}ms
- **Avg Response Time:** {health.avg_response_time_ms:.0f}ms
- **Failure Rate:** {health.failure_rate:.1%}
- **Active Users:** {health.active_users}

**Model Status:**
{model_status_str}

*Last checked: {health.last_check}*"""
