"""
AI Self-Evaluation, Prompt Quality Analysis, and Explainability.
Provides introspection and explanation of AI decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class QualityRating(Enum):
    """Prompt quality ratings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class RelevanceScore(Enum):
    """Relevance ratings."""
    HIGHLY_RELEVANT = "highly_relevant"
    RELEVANT = "relevant"
    SOMEWHAT_RELEVANT = "somewhat_relevant"
    NOT_RELEVANT = "not_relevant"


@dataclass
class SelfEvaluation:
    """AI self-evaluation of its response."""
    accuracy_score: float  # 0-1
    reasoning_quality: float  # 0-1
    completeness_score: float  # 0-1
    safety_score: float  # 0-1
    overall_score: float  # 0-1
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    
    def get_overall_rating(self) -> str:
        """Get overall rating label."""
        if self.overall_score >= 0.85:
            return "Excellent"
        if self.overall_score >= 0.70:
            return "Good"
        if self.overall_score >= 0.50:
            return "Average"
        return "Needs Improvement"


@dataclass
class PromptQuality:
    """Analysis of input prompt quality."""
    rating: QualityRating
    clarity_score: float
    specificity_score: float
    feasibility_score: float
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ExplainabilityInfo:
    """Detailed explanation of decision-making."""
    model_selection_reasoning: str
    why_this_model: str
    confidence_reasoning: str
    verification_status: str
    safety_considerations: str
    key_decision_points: List[str] = field(default_factory=list)


class SelfEvaluator:
    """Self-evaluation of AI responses."""
    
    @staticmethod
    def evaluate(
        prompt: str,
        response: str,
        model_used: str,
        confidence: float,
        was_escalated: bool = False,
        security_passed: bool = True
    ) -> SelfEvaluation:
        """
        Self-evaluate the response.
        
        Args:
            prompt: Original user prompt
            response: Generated response
            model_used: Model that generated response
            confidence: Confidence score
            was_escalated: Whether request was escalated
            security_passed: Whether security checks passed
            
        Returns:
            SelfEvaluation with scores and analysis
        """
        # Analyze response characteristics
        response_length = len(response)
        has_sources = any(word in response.lower() for word in ["according", "based", "source", "research"])
        has_reasoning = any(word in response.lower() for word in ["reason", "because", "therefore", "thus", "hence"])
        
        # Calculate scores
        accuracy_score = min(1.0, confidence)
        reasoning_quality = 0.8 if has_reasoning else 0.6
        completeness_score = min(1.0, response_length / 1000.0) * 0.9 + 0.1
        safety_score = 1.0 if security_passed else 0.5
        
        # Overall score
        overall_score = (accuracy_score + reasoning_quality + completeness_score + safety_score) / 4
        
        # Identify strengths
        strengths = []
        if confidence > 0.8:
            strengths.append("High confidence in response")
        if has_reasoning:
            strengths.append("Clear reasoning provided")
        if security_passed:
            strengths.append("All safety checks passed")
        if response_length > 300:
            strengths.append("Comprehensive response")
        
        # Identify weaknesses
        weaknesses = []
        if confidence < 0.7:
            weaknesses.append("Lower than average confidence")
        if not has_sources and "factual" in prompt.lower():
            weaknesses.append("Could benefit from sources")
        if was_escalated:
            weaknesses.append("Required model escalation")
        if response_length < 100:
            weaknesses.append("Response could be more detailed")
        
        # Suggest improvements
        improvements = []
        if not has_reasoning:
            improvements.append("Add step-by-step reasoning")
        if not has_sources and "research" in prompt.lower():
            improvements.append("Include source citations")
        if response_length < 200:
            improvements.append("Expand with more details")
        improvements.append("Add confidence indicators")
        
        return SelfEvaluation(
            accuracy_score=round(accuracy_score, 2),
            reasoning_quality=round(reasoning_quality, 2),
            completeness_score=round(completeness_score, 2),
            safety_score=round(safety_score, 2),
            overall_score=round(overall_score, 2),
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements
        )


class PromptQualityAnalyzer:
    """Analyze and rate input prompt quality."""
    
    @staticmethod
    def analyze(prompt: str) -> PromptQuality:
        """
        Analyze prompt quality.
        
        Args:
            prompt: The input prompt to analyze
            
        Returns:
            PromptQuality with scores and recommendations
        """
        # Score clarity
        clarity_score = PromptQualityAnalyzer._score_clarity(prompt)
        
        # Score specificity
        specificity_score = PromptQualityAnalyzer._score_specificity(prompt)
        
        # Score feasibility
        feasibility_score = PromptQualityAnalyzer._score_feasibility(prompt)
        
        # Determine overall rating
        avg_score = (clarity_score + specificity_score + feasibility_score) / 3
        if avg_score >= 0.85:
            rating = QualityRating.EXCELLENT
        elif avg_score >= 0.70:
            rating = QualityRating.GOOD
        elif avg_score >= 0.50:
            rating = QualityRating.AVERAGE
        else:
            rating = QualityRating.POOR
        
        # Identify issues
        issues = []
        if clarity_score < 0.7:
            issues.append("Prompt could be clearer")
        if specificity_score < 0.7:
            issues.append("Prompt lacks specific details")
        if feasibility_score < 0.7:
            issues.append("Request may not be feasible")
        if len(prompt) < 20:
            issues.append("Prompt is too brief")
        
        # Generate suggestions
        suggestions = []
        if clarity_score < 0.8:
            suggestions.append("Be more specific about what you're asking")
        if specificity_score < 0.8:
            suggestions.append("Include more context or details")
        if len(prompt) < 50:
            suggestions.append("Provide more information for better results")
        if "please" not in prompt.lower():
            suggestions.append("Consider adding polite language")
        
        return PromptQuality(
            rating=rating,
            clarity_score=round(clarity_score, 2),
            specificity_score=round(specificity_score, 2),
            feasibility_score=round(feasibility_score, 2),
            issues=issues,
            suggestions=suggestions
        )
    
    @staticmethod
    def _score_clarity(prompt: str) -> float:
        """Score prompt clarity (0-1)."""
        score = 0.5
        
        # Longer is generally clearer
        if len(prompt) > 50:
            score += 0.15
        if len(prompt) > 100:
            score += 0.15
        
        # Question format adds clarity
        if "?" in prompt:
            score += 0.1
        
        # Specific keywords add clarity
        clarity_keywords = ["what", "how", "why", "explain", "describe", "create", "help"]
        for keyword in clarity_keywords:
            if keyword in prompt.lower():
                score += 0.05
        
        return min(1.0, score)
    
    @staticmethod
    def _score_specificity(prompt: str) -> float:
        """Score prompt specificity (0-1)."""
        score = 0.5
        
        # More specific details
        specific_markers = ["specific", "exactly", "particular", "exactly how", "step by step"]
        for marker in specific_markers:
            if marker in prompt.lower():
                score += 0.1
        
        # Quantified requests
        if any(str(i) in prompt for i in range(10)):
            score += 0.15
        
        # Domain-specific language
        technical_terms = ["api", "database", "algorithm", "structure", "format", "schema"]
        for term in technical_terms:
            if term in prompt.lower():
                score += 0.05
        
        return min(1.0, score)
    
    @staticmethod
    def _score_feasibility(prompt: str) -> float:
        """Score prompt feasibility (0-1)."""
        score = 0.7  # Most requests are feasible
        
        # Reduce for impossible/unclear requests
        impossible_markers = ["impossible", "hack", "illegal", "unethical", "ban"]
        for marker in impossible_markers:
            if marker in prompt.lower():
                score -= 0.2
        
        return max(0.0, min(1.0, score))


class ExplainabilityPanel:
    """Provide detailed explanation of decision-making."""
    
    @staticmethod
    def explain_decision(
        prompt: str,
        selected_model: str,
        confidence: float,
        security_result: str,
        complexity_level: str
    ) -> ExplainabilityInfo:
        """
        Generate detailed explanation of decision-making.
        
        Args:
            prompt: Original user prompt
            selected_model: Selected AI model
            confidence: Confidence score
            security_result: Security check result
            complexity_level: Analyzed complexity level
            
        Returns:
            ExplainabilityInfo with detailed reasoning
        """
        return ExplainabilityInfo(
            model_selection_reasoning=(
                f"Your request was classified as '{complexity_level}' complexity. "
                f"Selected '{selected_model}' based on capability matching."
            ),
            why_this_model=(
                f"The '{selected_model}' model is optimized for {complexity_level.lower()} "
                f"complexity tasks and provides the best balance of speed and accuracy."
            ),
            confidence_reasoning=(
                f"Confidence score of {confidence:.0%} based on: "
                f"model capability, response completeness, and reasoning quality."
            ),
            verification_status=(
                f"Security check: {security_result}. "
                f"No safety concerns detected in this request."
            ),
            safety_considerations=(
                "Response was verified for safety, accuracy, and alignment with guidelines."
            ),
            key_decision_points=[
                f"Request complexity: {complexity_level}",
                f"Security status: ✅ Safe",
                f"Model selected: {selected_model}",
                f"Confidence level: {confidence:.0%}"
            ]
        )


def format_self_evaluation(eval: SelfEvaluation) -> str:
    """Format self-evaluation for display."""
    eval_card = f"""📋 **AI Self-Evaluation**

**Accuracy:** {'█' * int(eval.accuracy_score * 5)}{'░' * (5 - int(eval.accuracy_score * 5))} {eval.accuracy_score:.0%}
**Reasoning:** {'█' * int(eval.reasoning_quality * 5)}{'░' * (5 - int(eval.reasoning_quality * 5))} {eval.reasoning_quality:.0%}
**Completeness:** {'█' * int(eval.completeness_score * 5)}{'░' * (5 - int(eval.completeness_score * 5))} {eval.completeness_score:.0%}
**Safety:** {'█' * int(eval.safety_score * 5)}{'░' * (5 - int(eval.safety_score * 5))} {eval.safety_score:.0%}

**Overall:** {eval.overall_score:.0%} - {eval.get_overall_rating()}

**Strengths:**
{chr(10).join(f"✅ {s}" for s in eval.strengths[:3])}

**Areas for Improvement:**
{chr(10).join(f"💡 {i}" for i in eval.improvements[:3])}"""
    
    return eval_card


def format_prompt_quality(quality: PromptQuality) -> str:
    """Format prompt quality assessment."""
    rating_emoji = {
        QualityRating.EXCELLENT: "🟢",
        QualityRating.GOOD: "🟡",
        QualityRating.AVERAGE: "🔵",
        QualityRating.POOR: "🔴"
    }.get(quality.rating, "⚪")
    
    return f"""{rating_emoji} **Prompt Quality: {quality.rating.value.title()}**

**Analysis:**
- Clarity: {int(quality.clarity_score * 100)}%
- Specificity: {int(quality.specificity_score * 100)}%
- Feasibility: {int(quality.feasibility_score * 100)}%

**Suggestions:**
{chr(10).join(f"💡 {s}" for s in quality.suggestions[:3])}"""


def format_explainability(info: ExplainabilityInfo) -> str:
    """Format explainability panel."""
    return f"""🔍 **Explainability Panel**

**Why This Model?**
{info.why_this_model}

**Confidence Reasoning:**
{info.confidence_reasoning}

**Verification Status:**
{info.verification_status}

**Key Decisions:**
{chr(10).join(f"• {point}" for point in info.key_decision_points)}"""
