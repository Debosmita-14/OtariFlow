"""
Hallucination Checker.
Verifies responses for contradictions and uncertain information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any
import re


class HallucinationRisk(Enum):
    """Risk levels for hallucinations."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Contradiction:
    """Detected contradiction in response."""
    type: str
    severity: str
    quote_1: str
    quote_2: str
    explanation: str


@dataclass
class HallucinationCheckResult:
    """Result of hallucination verification."""
    is_reliable: bool
    risk_level: HallucinationRisk
    contradictions: List[Contradiction] = field(default_factory=list)
    uncertain_phrases: List[str] = field(default_factory=list)
    confidence_reduction: float = 0.0  # Percentage reduction
    recommendation: str = ""


class HallucinationChecker:
    """Check responses for hallucinations and inconsistencies."""
    
    # Uncertainty phrases that indicate potential hallucination
    UNCERTAINTY_PATTERNS = [
        r"I think",
        r"It seems",
        r"Maybe",
        r"Possibly",
        r"Allegedly",
        r"Rumor has it",
        r"I assume",
        r"From my understanding",
        r"Could be",
        r"Might be",
        r"Probably",
        r"Apparently",
        r"I'm not sure",
        r"I don't know",
        r"I can't verify",
    ]
    
    # Contradiction indicators
    CONTRADICTION_PATTERNS = [
        (r"however.*(?:but|yet|though)", "logical_contradiction"),
        (r"although.*(?:nevertheless|nonetheless)", "opposing_statements"),
        (r"previously.*(?:now|currently|later)", "temporal_contradiction"),
    ]
    
    @staticmethod
    def check(response: str, expected_type: str = "general") -> HallucinationCheckResult:
        """
        Check a response for hallucinations and inconsistencies.
        
        Args:
            response: The generated response to verify
            expected_type: Type of expected response
            
        Returns:
            HallucinationCheckResult with findings
        """
        contradictions = HallucinationChecker._find_contradictions(response)
        uncertain_phrases = HallucinationChecker._find_uncertain_language(response)
        
        # Calculate risk level
        risk_level = HallucinationChecker._assess_risk(
            contradictions, uncertain_phrases
        )
        
        # Determine reliability
        is_reliable = risk_level in [HallucinationRisk.NONE, HallucinationRisk.LOW]
        
        # Calculate confidence reduction
        confidence_reduction = HallucinationChecker._calculate_confidence_reduction(
            risk_level
        )
        
        # Generate recommendation
        recommendation = HallucinationChecker._generate_recommendation(
            risk_level, contradictions
        )
        
        return HallucinationCheckResult(
            is_reliable=is_reliable,
            risk_level=risk_level,
            contradictions=contradictions,
            uncertain_phrases=uncertain_phrases,
            confidence_reduction=confidence_reduction,
            recommendation=recommendation
        )
    
    @staticmethod
    def _find_contradictions(response: str) -> List[Contradiction]:
        """Find logical contradictions in response."""
        contradictions = []
        sentences = re.split(r'[.!?]+', response)
        
        # Simple contradiction detection
        for pattern, c_type in HallucinationChecker.CONTRADICTION_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                # Extract surrounding context
                start = max(0, match.start() - 50)
                end = min(len(response), match.end() + 50)
                context = response[start:end].strip()
                
                # Create a dummy contradiction for demonstration
                contradictions.append(Contradiction(
                    type=c_type,
                    severity="medium",
                    quote_1=context[:30],
                    quote_2=context[30:60],
                    explanation=f"Found {c_type} in response"
                ))
        
        return contradictions[:3]  # Limit to 3
    
    @staticmethod
    def _find_uncertain_language(response: str) -> List[str]:
        """Find phrases indicating uncertainty."""
        uncertain = []
        for pattern in HallucinationChecker.UNCERTAINTY_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 20)
                end = min(len(response), match.end() + 40)
                phrase = response[start:end].strip()
                if phrase not in uncertain:
                    uncertain.append(phrase)
        
        return uncertain[:5]  # Return top 5
    
    @staticmethod
    def _assess_risk(
        contradictions: List[Contradiction],
        uncertain_phrases: List[str]
    ) -> HallucinationRisk:
        """Assess hallucination risk based on findings."""
        if not contradictions and not uncertain_phrases:
            return HallucinationRisk.NONE
        
        risk_score = 0
        risk_score += len(contradictions) * 2
        risk_score += len(uncertain_phrases) * 0.5
        
        if risk_score == 0:
            return HallucinationRisk.NONE
        if risk_score < 2:
            return HallucinationRisk.LOW
        if risk_score < 5:
            return HallucinationRisk.MEDIUM
        return HallucinationRisk.HIGH
    
    @staticmethod
    def _calculate_confidence_reduction(risk_level: HallucinationRisk) -> float:
        """Calculate confidence score reduction based on risk."""
        reductions = {
            HallucinationRisk.NONE: 0.0,
            HallucinationRisk.LOW: 0.05,
            HallucinationRisk.MEDIUM: 0.15,
            HallucinationRisk.HIGH: 0.30
        }
        return reductions.get(risk_level, 0.0)
    
    @staticmethod
    def _generate_recommendation(
        risk_level: HallucinationRisk,
        contradictions: List[Contradiction]
    ) -> str:
        """Generate recommendation based on findings."""
        if risk_level == HallucinationRisk.NONE:
            return "✅ Response appears consistent and reliable"
        
        if risk_level == HallucinationRisk.HIGH:
            return "🚨 This response contains uncertain information. Verify before relying on it."
        
        if contradictions:
            return "⚠️ This response may contain inconsistencies. Review carefully."
        
        return "ℹ️ This response uses uncertain language. Additional verification recommended."


def get_hallucination_alert(result: HallucinationCheckResult) -> str:
    """Generate alert message for hallucination risks."""
    if result.is_reliable:
        return ""
    
    message = "⚠️ **Verification Alert**\n\n"
    
    if result.risk_level == HallucinationRisk.HIGH:
        message += "This response contains uncertain information.\n"
        message += "**Verify before relying on it.**\n\n"
    
    if result.contradictions:
        message += "**Potential Inconsistencies Found:**\n"
        for c in result.contradictions[:2]:
            message += f"- {c.explanation}\n"
        message += "\n"
    
    if result.uncertain_phrases:
        message += "**Uncertain Language Detected:**\n"
        for phrase in result.uncertain_phrases[:3]:
            message += f"- \"{phrase}\"\n"
    
    message += f"\n*Confidence reduced by {int(result.confidence_reduction * 100)}%*"
    
    return message
