from __future__ import annotations

"""Enterprise-grade prompt analysis helpers for OtariFlow.

This module keeps reusable heuristics in one place so the request pipeline can
apply security, quality, verification, summarization, and explainability logic
without mixing those concerns into the HTTP handler.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class PromptQuality:
    score: int
    label: str
    suggestions: List[str]


@dataclass(frozen=True)
class VerificationResult:
    status: str
    uncertain: bool
    notes: List[str]


@dataclass(frozen=True)
class SelfEvaluation:
    accuracy: int
    reasoning: int
    completeness: int
    safety: int
    overall: int


QUALITY_LABELS = [
    (85, "Excellent"),
    (70, "Good"),
    (50, "Average"),
    (0, "Poor"),
]


BLOCK_REFUSALS = {
    "prompt_injection": "This request appears to try to override system instructions.",
    "jailbreak": "This request appears to attempt a jailbreak or policy bypass.",
    "system_probe": "This request appears to probe hidden instructions or secrets.",
    "malware": "This request appears to request harmful or malicious behavior.",
    "hacking": "This request appears to request unauthorized access or exploit guidance.",
    "dangerous_content": "This request appears to contain dangerous or violent content.",
}


SAFER_REWRITES = {
    "prompt_injection": "Ask for a legitimate task, such as summarizing a document or drafting a response.",
    "jailbreak": "Ask a normal assistance question without trying to override safety controls.",
    "system_probe": "Ask about the model's public capabilities or how to use the app safely.",
    "malware": "Ask for defensive security guidance, such as malware detection or prevention.",
    "hacking": "Ask about ethical security, hardening, or how to protect a system.",
    "dangerous_content": "Ask for safety, prevention, or de-escalation information instead.",
}


def prompt_hash(prompt: str) -> str:
    """Return a stable SHA-256 hash for prompt auditing."""

    return hashlib.sha256(prompt.encode("utf-8", errors="ignore")).hexdigest()


def classify_prompt_quality(prompt: str) -> PromptQuality:
    """Score the prompt for clarity and suggest how to improve it."""

    cleaned = prompt.strip()
    word_count = len(cleaned.split())
    score = 55
    suggestions: List[str] = []

    if word_count < 4:
        score -= 25
        suggestions.append("Add more detail about the task and expected output.")
    if len(cleaned) > 260:
        score += 10
    if any(token in cleaned.lower() for token in ("please", "format", "example", "constraints")):
        score += 12
    if "?" not in cleaned and word_count < 20:
        score -= 8
        suggestions.append("Frame the request as a direct question or a clear instruction.")
    if re.search(r"\b(it|this|that|they)\b", cleaned, re.IGNORECASE) and word_count < 18:
        score -= 8
        suggestions.append("Replace vague pronouns with the exact subject or target.")
    if any(marker in cleaned.lower() for marker in ("debug", "error", "traceback", "sql", "api", "architecture", "refactor")):
        score += 12
    if any(marker in cleaned.lower() for marker in ("ignore previous", "jailbreak", "reveal prompt", "api key")):
        score = min(score, 20)

    score = max(0, min(100, score))
    label = next((name for threshold, name in QUALITY_LABELS if score >= threshold), "Poor")
    if not suggestions:
        suggestions.append("The prompt is specific enough to execute directly.")
    return PromptQuality(score=score, label=label, suggestions=suggestions)


def verify_response(prompt: str, response: str | None) -> VerificationResult:
    """Run a lightweight contradiction and relevance check on the response."""

    if not response:
        return VerificationResult(status="uncertain", uncertain=True, notes=["No response content was generated."])

    response_text = response.lower()
    prompt_terms = [word for word in re.findall(r"[a-zA-Z]{4,}", prompt.lower()) if word not in {"please", "help", "with", "that", "this", "from", "your"}]
    matched_terms = sum(1 for term in prompt_terms[:8] if term in response_text)
    notes: List[str] = []

    if any(marker in response_text for marker in ("i am not sure", "might be", "cannot verify", "uncertain")):
        notes.append("The response contains explicit uncertainty language.")
    if prompt_terms and matched_terms == 0:
        notes.append("The response does not appear to mention the main prompt terms.")
    if len(response_text.split()) < max(12, len(prompt.split()) // 2):
        notes.append("The response is much shorter than the request and may be incomplete.")

    uncertain = bool(notes)
    status = "verified" if not uncertain else "review"
    return VerificationResult(status=status, uncertain=uncertain, notes=notes or ["The response passed the basic verification check."])


def self_evaluate(confidence: float, verification: VerificationResult, response: str | None, blocked: bool) -> SelfEvaluation:
    """Produce a simple self-evaluation card set."""

    base = int(round(confidence * 100))
    completeness = 92 if response else 35
    safety = 95 if not blocked else 100
    accuracy = max(0, min(100, base + (8 if not verification.uncertain else -18)))
    reasoning = max(0, min(100, base + (4 if "verified" == verification.status else -10)))
    overall = round((accuracy + reasoning + completeness + safety) / 4)
    return SelfEvaluation(
        accuracy=accuracy,
        reasoning=reasoning,
        completeness=completeness,
        safety=safety,
        overall=overall,
    )


def build_refusal(prompt: str, reasons: Iterable[str]) -> Dict[str, str]:
    """Build a user-facing refusal message and a safer rewrite suggestion."""

    labels = list(reasons)
    reason_key = labels[0] if labels else "prompt_injection"
    explanation = BLOCK_REFUSALS.get(reason_key, "This request appears unsafe or disallowed.")
    rewrite = SAFER_REWRITES.get(reason_key, "Please rewrite the request so it asks for safe, legitimate assistance.")
    return {
        "title": "Security Alert",
        "message": (
            "Your request was blocked because it appears to contain malicious or unsafe instructions.\n\n"
            "Reason:\n"
            "Prompt Injection / Jailbreak Attempt Detected\n\n"
            "This interaction has been safely terminated.\n\n"
            "Please enter a valid request."
        ),
        "reason": explanation,
        "rewrite": rewrite,
        "attack_type": reason_key,
    }


def summarize_memory(prompts: List[str], max_items: int = 4) -> str:
    """Compress recent session context into a short summary string."""

    if not prompts:
        return ""
    kept = [item.strip() for item in prompts if item.strip()]
    if len(kept) <= max_items:
        return " | ".join(kept)
    recent = kept[-max_items:]
    return " | ".join(recent)


def explainability_payload(selected_tier: str, routing_reason: str, verification: VerificationResult, quality: PromptQuality) -> Dict[str, Any]:
    """Create a compact explainability payload for the UI."""

    return {
        "selected_tier": selected_tier,
        "why_model_selected": routing_reason,
        "confidence_reasoning": f"Prompt quality {quality.label.lower()} with verification status {verification.status}.",
        "verification_status": verification.status,
        "verification_notes": verification.notes,
        "prompt_quality": {
            "score": quality.score,
            "label": quality.label,
            "suggestions": quality.suggestions,
        },
    }


def now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""

    return datetime.utcnow().isoformat()
