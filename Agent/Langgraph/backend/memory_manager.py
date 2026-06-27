"""
Context Memory Manager.
Manages conversation context, automatically summarizes when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re


@dataclass
class MemoryEntry:
    """Single conversation memory entry."""
    timestamp: str
    role: str  # "user" or "assistant"
    content: str
    tokens: int
    importance_score: float = 0.5


@dataclass
class MemoryStats:
    """Statistics about current memory state."""
    total_messages: int
    total_tokens: int
    memory_percentage: float  # 0-100
    is_optimized: bool
    last_summary: str = ""
    entries_removed: int = 0


class ContextMemoryManager:
    """Manage conversation context with automatic optimization."""
    
    # Memory thresholds
    MAX_TOKENS = 8000  # Maximum tokens to keep in context
    SUMMARY_THRESHOLD = 0.8  # Start summarization at 80% capacity
    
    def __init__(self) -> None:
        """Initialize memory manager."""
        self.entries: List[MemoryEntry] = []
        self.summaries: List[str] = []
        self.current_token_count = 0
    
    def add_message(
        self,
        role: str,
        content: str,
        tokens: int,
        importance: float = 0.5
    ) -> None:
        """
        Add a message to memory.
        
        Args:
            role: "user" or "assistant"
            content: Message content
            tokens: Token count
            importance: Importance score (0-1)
        """
        entry = MemoryEntry(
            timestamp=datetime.utcnow().isoformat(),
            role=role,
            content=content,
            tokens=tokens,
            importance_score=importance
        )
        self.entries.append(entry)
        self.current_token_count += tokens
        
        # Auto-optimize if needed
        if self._should_optimize():
            self.optimize()
    
    def _should_optimize(self) -> bool:
        """Check if memory needs optimization."""
        capacity_ratio = self.current_token_count / self.MAX_TOKENS
        return capacity_ratio >= self.SUMMARY_THRESHOLD
    
    def optimize(self) -> str:
        """
        Optimize memory by summarizing old, low-importance messages.
        
        Returns:
            Summary of removed content
        """
        if len(self.entries) < 3:
            return ""
        
        # Calculate importance scores
        for entry in self.entries:
            entry.importance_score = self._calculate_importance(entry)
        
        # Identify entries to remove (oldest, lowest importance)
        entries_sorted = sorted(
            self.entries,
            key=lambda e: (e.importance_score, e.timestamp)
        )
        
        # Remove oldest, least important entries until under threshold
        removed_entries = []
        while self.current_token_count > self.MAX_TOKENS * 0.7 and len(entries_sorted) > 2:
            entry = entries_sorted.pop(0)
            removed_entries.append(entry)
            self.current_token_count -= entry.tokens
            self.entries.remove(entry)
        
        # Generate summary
        summary = self._generate_summary(removed_entries)
        self.summaries.append(summary)
        
        return summary
    
    def _calculate_importance(self, entry: MemoryEntry) -> float:
        """Calculate importance score for an entry."""
        score = entry.importance_score
        
        # Boost importance for recent messages
        time_diff = datetime.utcnow() - datetime.fromisoformat(entry.timestamp)
        recency_boost = max(0, 1.0 - (time_diff.total_seconds() / 3600.0))  # Decay over hour
        
        # Boost importance for responses vs user messages
        role_boost = 0.1 if entry.role == "assistant" else 0.0
        
        # Longer responses are more important
        length_boost = min(0.3, len(entry.content) / 1000.0)
        
        return min(1.0, score + recency_boost * 0.2 + role_boost + length_boost)
    
    def _generate_summary(self, entries: List[MemoryEntry]) -> str:
        """Generate summary of removed entries."""
        if not entries:
            return ""
        
        # Extract key points (simplified)
        key_points = []
        for entry in entries:
            # Simple extraction of first 100 chars of substantive content
            content = entry.content.strip()
            if len(content) > 20:
                key_points.append(f"- {entry.role}: {content[:80]}...")
        
        summary = "Previous conversation summary:\n" + "\n".join(key_points[:5])
        return summary
    
    def get_context(self) -> str:
        """Get current conversation context as string."""
        context_parts = []
        
        # Add summaries first
        if self.summaries:
            context_parts.append("\n".join(self.summaries[-2:]))  # Last 2 summaries
            context_parts.append("---")
        
        # Add recent entries
        for entry in self.entries[-10:]:  # Last 10 messages
            prefix = "User:" if entry.role == "user" else "Assistant:"
            context_parts.append(f"{prefix} {entry.content}")
        
        return "\n".join(context_parts)
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        capacity_ratio = self.current_token_count / self.MAX_TOKENS
        
        return MemoryStats(
            total_messages=len(self.entries),
            total_tokens=self.current_token_count,
            memory_percentage=int(capacity_ratio * 100),
            is_optimized=capacity_ratio < self.SUMMARY_THRESHOLD,
            last_summary=self.summaries[-1] if self.summaries else "",
            entries_removed=sum(1 for entry in self.entries if entry not in self.entries)
        )
    
    def clear(self) -> None:
        """Clear all memory."""
        self.entries.clear()
        self.summaries.clear()
        self.current_token_count = 0


def get_memory_optimization_message(stats: MemoryStats) -> str:
    """Generate message for memory optimization."""
    return f"""💾 **Memory Optimized**

Conversation compressed successfully.

**Stats:**
- Messages: {stats.total_messages}
- Tokens: {stats.total_tokens}/{ContextMemoryManager.MAX_TOKENS}
- Capacity: {stats.memory_percentage}%
- Status: {"✅ Optimized" if stats.is_optimized else "⚠️ Near capacity"}

*Important context preserved. Older messages summarized.*"""
