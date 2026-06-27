"""
Smart Caching, Notifications, and Enterprise Logging.
Enhanced caching strategies and comprehensive audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import hashlib


class NotificationType(Enum):
    """Types of notifications."""
    SECURITY_BLOCKED = "security_blocked"
    MODEL_UPGRADED = "model_upgraded"
    MEMORY_OPTIMIZED = "memory_optimized"
    VERIFICATION_COMPLETED = "verification_completed"
    CACHE_HIT = "cache_hit"
    RETRY_SUCCESS = "retry_success"
    ERROR_RECOVERED = "error_recovered"
    RATE_LIMITED = "rate_limited"


@dataclass
class UINotification:
    """A notification for the UI."""
    type: NotificationType
    title: str
    message: str
    icon: str
    duration_ms: int = 3000
    timestamp: str = ""
    action_text: Optional[str] = None
    action_url: Optional[str] = None
    
    def __post_init__(self):
        """Auto-set timestamp."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class CacheEntry:
    """Single cache entry."""
    key: str
    prompt_hash: str
    response: str
    model_used: str
    confidence: float
    created_at: str
    accessed_count: int = 0
    last_accessed: str = ""
    ttl_seconds: int = 3600  # 1 hour


class SmartCache:
    """Intelligent caching with semantic similarity."""
    
    def __init__(self, max_entries: int = 1000) -> None:
        """Initialize smart cache."""
        self.max_entries = max_entries
        self.entries: Dict[str, CacheEntry] = {}
        self.similarity_threshold = 0.85
    
    def store(
        self,
        prompt: str,
        response: str,
        model_used: str,
        confidence: float,
        ttl_seconds: int = 3600
    ) -> None:
        """Store response in cache."""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        key = prompt_hash
        
        entry = CacheEntry(
            key=key,
            prompt_hash=prompt_hash,
            response=response,
            model_used=model_used,
            confidence=confidence,
            created_at=datetime.utcnow().isoformat(),
            ttl_seconds=ttl_seconds
        )
        
        self.entries[key] = entry
        
        # Evict old entries if at capacity
        if len(self.entries) > self.max_entries:
            self._evict_lru()
    
    def lookup(self, prompt: str) -> Optional[CacheEntry]:
        """Look up similar prompt in cache."""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Direct lookup
        if prompt_hash in self.entries:
            entry = self.entries[prompt_hash]
            
            # Check TTL
            created = datetime.fromisoformat(entry.created_at)
            if datetime.utcnow() - created > timedelta(seconds=entry.ttl_seconds):
                del self.entries[prompt_hash]
                return None
            
            # Update stats
            entry.accessed_count += 1
            entry.last_accessed = datetime.utcnow().isoformat()
            
            return entry
        
        # Semantic similarity lookup
        for key, entry in list(self.entries.items()):
            similarity = self._calculate_similarity(prompt, entry.response)
            if similarity >= self.similarity_threshold:
                # Check TTL
                created = datetime.fromisoformat(entry.created_at)
                if datetime.utcnow() - created > timedelta(seconds=entry.ttl_seconds):
                    del self.entries[key]
                    continue
                
                entry.accessed_count += 1
                entry.last_accessed = datetime.utcnow().isoformat()
                return entry
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simplified)."""
        # Simple word overlap for demo
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        
        return overlap / union if union > 0 else 0.0
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.entries:
            return
        
        lru_key = min(
            self.entries.keys(),
            key=lambda k: (
                self.entries[k].accessed_count,
                self.entries[k].last_accessed or self.entries[k].created_at
            )
        )
        del self.entries[lru_key]
    
    def clear(self) -> None:
        """Clear cache."""
        self.entries.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_accesses = sum(e.accessed_count for e in self.entries.values())
        return {
            "total_entries": len(self.entries),
            "max_entries": self.max_entries,
            "total_accesses": total_accesses,
            "capacity_used": f"{len(self.entries) / self.max_entries * 100:.1f}%"
        }


class NotificationCenter:
    """Manage UI notifications."""
    
    def __init__(self) -> None:
        """Initialize notification center."""
        self.notifications: List[UINotification] = []
        self.max_notifications = 20
    
    def add_notification(self, notification: UINotification) -> None:
        """Add notification."""
        self.notifications.append(notification)
        
        # Keep only recent
        if len(self.notifications) > self.max_notifications:
            self.notifications.pop(0)
    
    def create_security_alert(self, reason: str) -> UINotification:
        """Create security alert notification."""
        return UINotification(
            type=NotificationType.SECURITY_BLOCKED,
            title="🚫 Security Alert",
            message=f"Request blocked: {reason}",
            icon="🚫",
            duration_ms=5000
        )
    
    def create_model_upgrade(self, from_model: str, to_model: str) -> UINotification:
        """Create model upgrade notification."""
        return UINotification(
            type=NotificationType.MODEL_UPGRADED,
            title="⚡ Model Upgraded",
            message=f"Escalated from {from_model} to {to_model}",
            icon="⚡",
            duration_ms=2000
        )
    
    def create_memory_optimized(self) -> UINotification:
        """Create memory optimization notification."""
        return UINotification(
            type=NotificationType.MEMORY_OPTIMIZED,
            title="💾 Memory Optimized",
            message="Conversation context compressed successfully",
            icon="💾",
            duration_ms=2000
        )
    
    def create_cache_hit(self) -> UINotification:
        """Create cache hit notification."""
        return UINotification(
            type=NotificationType.CACHE_HIT,
            title="⚡ Served from Cache",
            message="Response retrieved from cache - response time improved",
            icon="⚡",
            duration_ms=2000
        )
    
    def create_verification_complete(self) -> UINotification:
        """Create verification notification."""
        return UINotification(
            type=NotificationType.VERIFICATION_COMPLETED,
            title="✅ Verification Complete",
            message="Response passed all safety checks",
            icon="✅",
            duration_ms=2000
        )
    
    def get_recent(self, limit: int = 5) -> List[UINotification]:
        """Get recent notifications."""
        return self.notifications[-limit:]


@dataclass
class AuditLogEntry:
    """Enterprise audit log entry."""
    timestamp: str
    user_id: str
    session_id: str
    action: str
    model_used: str
    execution_time_ms: float
    confidence: float
    security_passed: bool
    security_reason: str
    escalation_count: int
    tokens_used: int
    cost: float
    request_prompt: str
    response_summary: str
    error: Optional[str] = None


class EnterpriseLogger:
    """Comprehensive enterprise logging."""
    
    def __init__(self) -> None:
        """Initialize enterprise logger."""
        self.logs: List[AuditLogEntry] = []
        self.max_logs = 10000
    
    def log_request(
        self,
        user_id: str,
        session_id: str,
        prompt: str,
        response: str,
        model_used: str,
        execution_time_ms: float,
        confidence: float,
        security_passed: bool,
        security_reason: str,
        escalation_count: int,
        tokens_used: int,
        cost: float,
        error: Optional[str] = None
    ) -> None:
        """Log a request comprehensively."""
        entry = AuditLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            user_id=user_id,
            session_id=session_id,
            action="process_prompt",
            model_used=model_used,
            execution_time_ms=execution_time_ms,
            confidence=confidence,
            security_passed=security_passed,
            security_reason=security_reason,
            escalation_count=escalation_count,
            tokens_used=tokens_used,
            cost=cost,
            request_prompt=prompt[:500],  # Truncate for storage
            response_summary=response[:500],  # Truncate for storage
            error=error
        )
        
        self.logs.append(entry)
        
        # Maintain max size
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
    
    def get_logs_for_user(self, user_id: str, limit: int = 100) -> List[AuditLogEntry]:
        """Get logs for specific user."""
        user_logs = [log for log in self.logs if log.user_id == user_id]
        return user_logs[-limit:]
    
    def get_logs_for_session(self, session_id: str) -> List[AuditLogEntry]:
        """Get logs for specific session."""
        return [log for log in self.logs if log.session_id == session_id]
    
    def get_statistics(self) -> Dict[str, any]:
        """Get logging statistics."""
        if not self.logs:
            return {
                "total_entries": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "avg_confidence": 0.0,
                "total_cost": 0.0
            }
        
        successful = sum(1 for log in self.logs if log.security_passed and not log.error)
        avg_time = sum(log.execution_time_ms for log in self.logs) / len(self.logs)
        avg_conf = sum(log.confidence for log in self.logs) / len(self.logs)
        total_cost = sum(log.cost for log in self.logs)
        
        return {
            "total_entries": len(self.logs),
            "success_rate": successful / len(self.logs) if self.logs else 0.0,
            "avg_execution_time": avg_time,
            "avg_confidence": avg_conf,
            "total_cost": total_cost
        }
