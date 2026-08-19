"""Models returned by post-generation output validation."""

from dataclasses import dataclass
from enum import Enum


class OutputCategory(str, Enum):
    SAFE = "SAFE"
    PII_SECRET = "PII_SECRET"
    PROMPT_LEAK = "PROMPT_LEAK"
    INTERNAL_DATA = "INTERNAL_DATA"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    UNGROUNDED_REFERENCE = "UNGROUNDED_REFERENCE"


class OutputAction(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class OutputSafetyResult:
    allowed: bool
    category: OutputCategory
    action: OutputAction
    reason: str
    sanitized_text: str

