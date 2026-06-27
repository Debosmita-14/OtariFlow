from __future__ import annotations

"""Security heuristics for blocking unsafe or malicious prompts."""

import math
import re
from dataclasses import dataclass, field
from typing import List, Tuple

from .config import settings


PATTERNS: List[Tuple[re.Pattern[str], float, str]] = []


def _add(pattern: str, weight: float, label: str) -> None:
    PATTERNS.append((re.compile(pattern, re.IGNORECASE | re.DOTALL), weight, label))


_add(r"ignore\s+(previous|prior|above|all)\s+(instructions?|prompts?|context)", 0.95, "prompt_injection")
_add(r"forget\s+(your|the)\s+system\s+prompt", 0.95, "prompt_injection")
_add(r"remove\s+previous\s+conversation", 0.9, "prompt_injection")
_add(r"reveal\s+(hidden|secret|system)\s+prompt", 0.92, "system_probe")
_add(r"show\s+api\s*key|reveal\s+api\s*key", 0.95, "credential_theft")
_add(r"bypass\s+safety|disable\s+safety|act\s+as\s+developer", 0.92, "jailbreak")
_add(r"execute\s+malicious\s+code|malware|ransomware|trojan|keylogger|botnet", 0.95, "malware")
_add(r"sql\s*injection|xss\s*payload|command\s*injection|prompt\s*injection", 0.95, "injection_attack")
_add(r"jailbreak|DAN\b|hack\s+this\s+system", 0.95, "jailbreak")
_add(r"\b(hack|exploit|buffer\s*overflow|phishing|credential\s*theft)\b", 0.8, "hacking")
_add(r"\b(bomb|explosive|detonate|c4|ied|kill|attack)\b", 0.95, "violent_content")
_add(r"[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e]", 0.85, "hidden_unicode")


@dataclass
class SecurityResult:
    is_safe: bool
    risk_score: float
    matched_patterns: List[str] = field(default_factory=list)
    reason: str = ""
    severity: str = "low"


def _severity(score: float) -> str:
    if score >= 0.9:
        return "critical"
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def analyse(prompt: str) -> SecurityResult:
    matched: List[str] = []
    raw_score = 0.0

    for pattern, weight, label in PATTERNS:
        if pattern.search(prompt):
            matched.append(label)
            raw_score += weight

    score = 1.0 - math.exp(-1.5 * raw_score)
    score = min(1.0, round(score, 4))
    is_safe = score < settings.risk_block_threshold
    reason = ""
    severity = _severity(score)

    if not is_safe:
        reason = f"High-risk patterns detected: {', '.join(sorted(set(matched)))}"

    return SecurityResult(
        is_safe=is_safe,
        risk_score=score,
        matched_patterns=sorted(set(matched)),
        reason=reason,
        severity=severity,
    )
