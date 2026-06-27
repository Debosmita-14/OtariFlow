from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


DETECTORS: List[Tuple[str, str | None, float]] = [
    ("chain_of_thought", r"\b(step[\s-]by[\s-]step|think\s+through|reasoning|explain\s+how)\b", 0.2),
    ("multi_step", r"\b(first.+then.+finally|multiple\s+steps?|step\s+\d+)\b", 0.2),
    ("research", r"\b(research|analyse|analyze|compare|evaluate|review|survey|literature)\b", 0.15),
    ("code", r"```|def |class |function|import |SELECT\s+\w|<[a-z]+>", 0.25),
    ("code", r"\b(debug|bug|error|fix|stack trace|exception|jsx|tsx|react|javascript|typescript|python|sql|html|css)\b", 0.25),
    ("math", r"\b(calcul|integr|deriv|equation|formula|proof|theorem|algebra|matrix)\b", 0.2),
    ("json_structured", r"\b(json|xml|yaml|csv|schema|structured\s+output|parse)\b", 0.1),
    ("document", r"\b(summarise|summarize|document|report|essay|article|contract)\b", 0.1),
    ("translation", r"\b(translat|in\s+french|in\s+spanish|in\s+german)\b", 0.1),
    ("creative", r"\b(write\s+a\s+(story|poem|song|script)|creative|fiction|narrative)\b", 0.1),
    ("few_shot", r"example\s*\d?[:\-]|e\.g\.|for\s+instance", 0.05),
    ("long_context", None, 0.0),
]


@dataclass
class ComplexityResult:
    score: float
    level: str
    tags: List[str] = field(default_factory=list)
    word_count: int = 0
    est_input_tokens: int = 0
    est_output_tokens: int = 0
    est_total_tokens: int = 0
    tag_scores: Dict[str, float] = field(default_factory=dict)


def _word_count(text: str) -> int:
    return len(text.split())


def _estimate_tokens(text: str) -> int:
    return max(1, int(_word_count(text) * 0.75))


def _output_multiplier(tags: List[str]) -> float:
    if "code" in tags or "research" in tags or "document" in tags:
        return 3.0
    if "math" in tags or "chain_of_thought" in tags:
        return 2.5
    if "creative" in tags:
        return 4.0
    if "translation" in tags:
        return 1.2
    return 1.5


def analyse(prompt: str) -> ComplexityResult:
    words = _word_count(prompt)
    input_tokens = _estimate_tokens(prompt)
    raw_score = 0.0
    tags: List[str] = []
    tag_scores: Dict[str, float] = {}

    for name, pattern, weight in DETECTORS:
        if name == "long_context":
            boost = 0.0
            if words > 500:
                boost = 0.25
            elif words > 200:
                boost = 0.15
            elif words > 80:
                boost = 0.05
            if boost:
                tags.append("long_context")
                tag_scores["long_context"] = boost
                raw_score += boost
            continue

        if pattern and re.search(pattern, prompt, re.IGNORECASE | re.DOTALL):
            tags.append(name)
            tag_scores[name] = weight
            raw_score += weight

    score = 1.0 - math.exp(-2.0 * raw_score)
    score = round(min(1.0, score), 4)

    if score >= 0.65:
        level = "high"
    elif score >= 0.35:
        level = "medium"
    else:
        level = "low"

    output_tokens = int(input_tokens * _output_multiplier(tags))
    total_tokens = input_tokens + output_tokens

    return ComplexityResult(
        score=score,
        level=level,
        tags=tags,
        word_count=words,
        est_input_tokens=input_tokens,
        est_output_tokens=output_tokens,
        est_total_tokens=total_tokens,
        tag_scores=tag_scores,
    )
