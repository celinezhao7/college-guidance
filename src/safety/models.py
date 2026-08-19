"""Data models for context-aware input safety decisions."""

from dataclasses import dataclass
from enum import Enum


class SafetyCategory(str, Enum):
    SAFE = "SAFE"
    SENSITIVE_ALLOWED = "SENSITIVE_ALLOWED"
    SELF_HARM = "SELF_HARM"
    VIOLENCE = "VIOLENCE"
    SEXUAL = "SEXUAL"
    HATE_HARASSMENT = "HATE_HARASSMENT"
    ILLEGAL_HARMFUL = "ILLEGAL_HARMFUL"
    PII_SECRET = "PII_SECRET"
    PROMPT_INJECTION = "PROMPT_INJECTION"


class SafetyAction(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    REDACT = "REDACT"
    BLOCK = "BLOCK"


class SafetySource(str, Enum):
    CHAT = "chat"
    STUDENT_KB = "student_kb"


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    category: SafetyCategory
    action: SafetyAction
    reason: str
    source_type: SafetySource
    sanitized_text: str | None = None

