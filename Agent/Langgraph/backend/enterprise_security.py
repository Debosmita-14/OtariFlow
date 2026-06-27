"""
Enterprise-grade security layer with enhanced protection.
Includes prompt injection detection, guardrails, and detailed logging.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple
from enum import Enum

from .config import settings


class AttackType(Enum):
    """Categorize types of security threats."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    CREDENTIAL_THEFT = "credential_theft"
    MALWARE = "malware"
    INJECTION_ATTACK = "injection_attack"
    VIOLENT_CONTENT = "violent_content"
    HATE_SPEECH = "hate_speech"
    PHISHING = "phishing"
    HIDDEN_UNICODE = "hidden_unicode"
    XSS_PAYLOAD = "xss_payload"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    CREDENTIAL_EXPOSURE = "credential_exposure"
    ILLEGAL_ACTIVITY = "illegal_activity"


class Severity(Enum):
    """Severity levels for detected threats."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Enhanced pattern library with more comprehensive detection
SECURITY_PATTERNS: List[Tuple[re.Pattern[str], AttackType, float, str]] = []


def _register_pattern(pattern: str, attack_type: AttackType, weight: float, description: str) -> None:
    """Register a security pattern with metadata."""
    SECURITY_PATTERNS.append((
        re.compile(pattern, re.IGNORECASE | re.DOTALL),
        attack_type,
        weight,
        description
    ))


# Prompt Injection Patterns
_register_pattern(r"ignore\s+(previous|prior|above|all)\s+(instructions?|prompts?|context)", 
                  AttackType.PROMPT_INJECTION, 0.95, "Ignore instructions")
_register_pattern(r"forget\s+(your|the)\s+system\s+prompt", 
                  AttackType.PROMPT_INJECTION, 0.95, "Forget system prompt")
_register_pattern(r"remove\s+previous\s+conversation", 
                  AttackType.PROMPT_INJECTION, 0.90, "Remove conversation history")
_register_pattern(r"override\s+safety|disable\s+safety|turn\s+off\s+safety", 
                  AttackType.PROMPT_INJECTION, 0.92, "Override safety")

# System Probing Patterns
_register_pattern(r"reveal\s+(hidden|secret|system)\s+prompt|show\s+me\s+the\s+system\s+prompt", 
                  AttackType.CREDENTIAL_THEFT, 0.92, "System prompt exposure")
_register_pattern(r"what\s+are\s+your\s+instructions", 
                  AttackType.CREDENTIAL_THEFT, 0.85, "Instructions revelation")

# Credential Theft Patterns
_register_pattern(r"show\s+api\s*key|reveal\s+api\s*key|expose\s+credentials?|display\s+token", 
                  AttackType.CREDENTIAL_THEFT, 0.95, "Credential exposure attempt")
_register_pattern(r"database\s+password|db\s+credentials|secret\s+key", 
                  AttackType.CREDENTIAL_THEFT, 0.90, "Database credential exposure")

# Jailbreak Patterns
_register_pattern(r"\bDAN\b|\bCAN\b|Do\s+Anything\s+Now", 
                  AttackType.JAILBREAK, 0.95, "DAN jailbreak attempt")
_register_pattern(r"ignore.*restrictions|no\s+restrictions|unrestricted\s+mode", 
                  AttackType.JAILBREAK, 0.92, "Unrestricted mode request")
_register_pattern(r"act\s+as\s+(developer|admin|hacker|god)", 
                  AttackType.JAILBREAK, 0.90, "Role assumption attack")
_register_pattern(r"jailbreak|break.*out.*of.*sandbox", 
                  AttackType.JAILBREAK, 0.95, "Direct jailbreak reference")

# Malware Patterns
_register_pattern(r"execute\s+malicious\s+code|malware|ransomware|trojan|keylogger|botnet|worm|virus", 
                  AttackType.MALWARE, 0.95, "Malware request")
_register_pattern(r"create.*backdoor|reverse.*shell|payload", 
                  AttackType.MALWARE, 0.92, "Malicious code creation")

# Injection Attack Patterns
_register_pattern(r"sql\s*injection|union\s+select|drop\s+table|insert\s+into", 
                  AttackType.SQL_INJECTION, 0.95, "SQL injection attempt")
_register_pattern(r"xss|javascript:|onclick=|onerror=|<script>", 
                  AttackType.XSS_PAYLOAD, 0.95, "XSS payload attempt")
_register_pattern(r"command\s*injection|shell\s+command|\`.*\`|&&|\|\||;\s*rm\s*-rf", 
                  AttackType.COMMAND_INJECTION, 0.95, "Command injection attempt")

# Hacking/Exploitation Patterns
_register_pattern(r"\b(hack|exploit|buffer\s*overflow|privilege\s+escalation)\b", 
                  AttackType.MALWARE, 0.85, "Hacking/exploitation")
_register_pattern(r"denial\s+of\s+service|dos\s+attack|ddos", 
                  AttackType.MALWARE, 0.90, "DoS attack request")

# Violent Content Patterns
_register_pattern(r"\b(bomb|explosive|detonate|c4|ied|kill|attack|murder|assassin)\b", 
                  AttackType.VIOLENT_CONTENT, 0.95, "Violent content")
_register_pattern(r"how\s+to\s+(kill|hurt|harm|poison|torture)", 
                  AttackType.VIOLENT_CONTENT, 0.95, "Violence instructions")

# Hate Speech Patterns
_register_pattern(r"\b(racist|sexist|homophobic|transphobic|slur|hatred)\b", 
                  AttackType.HATE_SPEECH, 0.92, "Hate speech")
_register_pattern(r"(nigger|faggot|kike|dyke)\b", 
                  AttackType.HATE_SPEECH, 0.98, "Explicit slur")

# Phishing/Credential Theft
_register_pattern(r"phishing|spoof|fake.*email|fake.*website|credential.*harvest", 
                  AttackType.PHISHING, 0.92, "Phishing attempt")

# Hidden Unicode Attack
_register_pattern(r"[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e]", 
                  AttackType.HIDDEN_UNICODE, 0.85, "Hidden unicode injection")

# Illegal Activity Patterns
_register_pattern(r"\b(drug.*synth|bomb.*making|weapon.*craft|illegal.*hack)\b", 
                  AttackType.ILLEGAL_ACTIVITY, 0.95, "Illegal activity request")


@dataclass
class SecurityThreat:
    """Represents a detected security threat."""
    attack_type: AttackType
    severity: Severity
    pattern_matched: str
    weight: float
    description: str


@dataclass
class EnterpriseSecurityResult:
    """Comprehensive security analysis result."""
    is_safe: bool
    risk_score: float
    threats: List[SecurityThreat] = field(default_factory=list)
    primary_threat: SecurityThreat | None = None
    reason: str = ""
    severity: str = "low"
    prompt_hash: str = ""
    suggestions: List[str] = field(default_factory=list)
    timestamp: str = ""


def _calculate_severity(risk_score: float) -> Severity:
    """Calculate severity based on risk score."""
    if risk_score >= 0.90:
        return Severity.CRITICAL
    if risk_score >= 0.75:
        return Severity.HIGH
    if risk_score >= 0.50:
        return Severity.MEDIUM
    return Severity.LOW


def _generate_suggestions(attack_type: AttackType) -> List[str]:
    """Generate helpful suggestions for rewriting unsafe prompts."""
    suggestions_map = {
        AttackType.PROMPT_INJECTION: [
            "Ask your question directly without trying to modify instructions",
            "Be specific about what information you need",
            "Use clear, straightforward language"
        ],
        AttackType.JAILBREAK: [
            "Ask for information within safety guidelines",
            "Request legitimate assistance instead of trying to bypass restrictions",
            "Explain what you're trying to accomplish"
        ],
        AttackType.CREDENTIAL_THEFT: [
            "Never ask for API keys, passwords, or credentials",
            "Ask about security best practices instead",
            "Learn how to manage credentials securely"
        ],
        AttackType.MALWARE: [
            "Ask about cybersecurity concepts in an educational context",
            "Request information about how systems are protected",
            "Learn about ethical security practices"
        ],
        AttackType.VIOLENT_CONTENT: [
            "Ask about conflict resolution instead",
            "Learn about peace and cooperation",
            "Request information about safety and well-being"
        ],
        AttackType.HATE_SPEECH: [
            "Ask about diversity and inclusion",
            "Learn about different cultures and perspectives",
            "Request information about combating discrimination"
        ],
    }
    return suggestions_map.get(attack_type, [
        "Rephrase your question to be more specific",
        "Ask about legitimate uses of the topic",
        "Request educational information instead"
    ])


def analyse(prompt: str, user_id: str = "unknown") -> EnterpriseSecurityResult:
    """
    Perform comprehensive security analysis on a prompt.
    
    Args:
        prompt: The user prompt to analyze
        user_id: Optional user identifier for logging
        
    Returns:
        EnterpriseSecurityResult with detailed threat information
    """
    threats: List[SecurityThreat] = []
    max_threat_weight = 0.0
    primary_threat: SecurityThreat | None = None
    
    # Check each security pattern
    for pattern, attack_type, weight, description in SECURITY_PATTERNS:
        if pattern.search(prompt):
            severity = _calculate_severity(weight)
            threat = SecurityThreat(
                attack_type=attack_type,
                severity=severity,
                pattern_matched=pattern.pattern,
                weight=weight,
                description=description
            )
            threats.append(threat)
            
            if weight > max_threat_weight:
                max_threat_weight = weight
                primary_threat = threat
    
    # Determine overall safety
    is_safe = len(threats) == 0
    risk_score = max_threat_weight if threats else 0.0
    
    # Generate reason and suggestions
    reason = ""
    suggestions = []
    if not is_safe and primary_threat:
        reason = f"{primary_threat.attack_type.value}: {primary_threat.description}"
        suggestions = _generate_suggestions(primary_threat.attack_type)
    
    # Generate prompt hash
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    # Create result
    result = EnterpriseSecurityResult(
        is_safe=is_safe,
        risk_score=round(risk_score, 4),
        threats=threats,
        primary_threat=primary_threat,
        reason=reason,
        severity=_calculate_severity(risk_score).value,
        prompt_hash=prompt_hash,
        suggestions=suggestions,
        timestamp=datetime.utcnow().isoformat()
    )
    
    return result


def get_security_alert_message(result: EnterpriseSecurityResult) -> str:
    """Generate a user-friendly security alert message."""
    if result.is_safe:
        return "✅ Security check passed"
    
    severity_emoji = {
        "critical": "🚫",
        "high": "⚠️",
        "medium": "⚡",
        "low": "ℹ️"
    }
    
    emoji = severity_emoji.get(result.severity, "🚫")
    
    message = f"""{emoji} Security Alert

Your request was blocked because it appears to contain unsafe or malicious instructions.

**Threat Type:** {result.primary_threat.attack_type.value if result.primary_threat else 'Unknown'}

**Reason:** {result.reason or 'Policy violation detected'}

This interaction has been safely terminated.

**How to rewrite safely:**
"""
    
    if result.suggestions:
        for i, suggestion in enumerate(result.suggestions[:3], 1):
            message += f"\n{i}. {suggestion}"
    else:
        message += "\nPlease ask your question in a different way."
    
    return message
