"""Context-aware first-pass safety checks for chat and student evidence.

This module deliberately distinguishes harmful requests from personal disclosures.
It is deterministic, makes no network calls, and is suitable as a pre-check before
a later model-based classifier is added.
"""

import re

from .models import SafetyAction, SafetyCategory, SafetyResult, SafetySource


_PROMPT_INJECTION = re.compile(
    r"(?:ignore|disregard|forget|override).{0,40}(?:previous|prior|system|developer|instructions?)"
    r"|(?:reveal|show|print|repeat).{0,30}(?:system prompt|hidden instructions?|developer message)"
    r"|忽略.{0,20}(?:之前|以上|系统|开发者).{0,12}(?:指令|提示|要求)"
    r"|(?:显示|泄露|输出).{0,20}(?:系统提示|隐藏指令|开发者消息)",
    re.IGNORECASE | re.DOTALL,
)

_SECRET_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(
        r"\b(?:api[_ -]?key|access[_ -]?token|password|passwd|secret)\s*[:=]\s*['\"]?[^\s'\"]{6,}",
        re.IGNORECASE,
    ),
)

_REQUEST_INTENT = re.compile(
    r"\b(?:how (?:do|can|could|would) i|how to|tell me how|give me (?:steps|instructions)|"
    r"help me|best way to|instructions? for)\b"
    r"|(?:怎么|如何|教我|告诉我).{0,15}(?:做|制作|伤害|攻击|杀|偷|骗|入侵)",
    re.IGNORECASE,
)

_SELF_HARM = re.compile(
    r"\b(?:kill myself|hurt myself|harm myself|suicide|end my life|self[- ]harm)\b"
    r"|(?:自杀|伤害自己|自残|结束生命)",
    re.IGNORECASE,
)
_VIOLENCE = re.compile(
    r"\b(?:kill|murder|shoot|stab|attack|bomb|poison)\b"
    r"|(?:杀死|谋杀|枪击|刺伤|袭击|炸弹|投毒)",
    re.IGNORECASE,
)
_SEXUAL_HARM = re.compile(
    r"\b(?:sexual assault|rape|exploit(?:ation)?|groom(?:ing)?|child pornography|csam)\b"
    r"|(?:性侵|强奸|性剥削|诱骗未成年人|儿童色情)",
    re.IGNORECASE,
)
_HATE_HARASSMENT = re.compile(
    r"\b(?:harass|doxx|threaten).{0,30}(?:person|people|classmate|teacher|group)\b"
    r"|(?:骚扰|人肉|威胁).{0,20}(?:同学|老师|某人|群体)",
    re.IGNORECASE,
)
_ILLEGAL_HARMFUL = re.compile(
    r"\b(?:hack|phish|steal|fraud|scam|malware|ransomware|make (?:a )?drug)\b"
    r"|(?:入侵|钓鱼|盗取|诈骗|恶意软件|勒索软件|制毒)",
    re.IGNORECASE,
)

_SENSITIVE_EXPERIENCE = re.compile(
    r"\b(?:died|death|grief|illness|disease|immigrat(?:e|ed|ion)|refugee|"
    r"mental health|anxiety|depression|family conflict|trauma|abuse|bully(?:ing|ied)|"
    r"suicidal thoughts?|self[- ]harm(?:ed)?|sexual assault)\b"
    r"|(?:去世|死亡|丧亲|疾病|生病|移民|难民|心理压力|心理健康|焦虑|抑郁|"
    r"家庭冲突|创伤|虐待|霸凌|自杀念头|曾经自残|性侵经历)",
    re.IGNORECASE,
)


def _redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _result(
    source: SafetySource,
    category: SafetyCategory,
    action: SafetyAction,
    reason: str,
    *,
    sanitized_text: str | None = None,
) -> SafetyResult:
    return SafetyResult(
        allowed=action in {SafetyAction.ALLOW, SafetyAction.REDACT, SafetyAction.WARN},
        category=category,
        action=action,
        reason=reason,
        source_type=source,
        sanitized_text=sanitized_text,
    )


def validate_input(text: str, source_type: str | SafetySource) -> SafetyResult:
    """Classify input using source-aware policy without treating sensitivity as harm."""
    try:
        source = SafetySource(source_type)
    except ValueError as exc:
        raise ValueError("source_type must be 'chat' or 'student_kb'") from exc

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        return _result(source, SafetyCategory.SAFE, SafetyAction.ALLOW, "Empty input.")

    if _PROMPT_INJECTION.search(text):
        return _result(
            source,
            SafetyCategory.PROMPT_INJECTION,
            SafetyAction.BLOCK,
            "The text attempts to override or expose system instructions.",
        )

    if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
        if source is SafetySource.STUDENT_KB:
            return _result(
                source,
                SafetyCategory.PII_SECRET,
                SafetyAction.BLOCK,
                "High-risk personal or secret data must not enter the knowledge base.",
            )
        return _result(
            source,
            SafetyCategory.PII_SECRET,
            SafetyAction.REDACT,
            "High-risk personal or secret data was detected and should be redacted.",
            sanitized_text=_redact_secrets(text),
        )

    harmful_categories = (
        (SafetyCategory.SELF_HARM, _SELF_HARM),
        (SafetyCategory.VIOLENCE, _VIOLENCE),
        (SafetyCategory.SEXUAL, _SEXUAL_HARM),
        (SafetyCategory.HATE_HARASSMENT, _HATE_HARASSMENT),
        (SafetyCategory.ILLEGAL_HARMFUL, _ILLEGAL_HARMFUL),
    )
    for category, pattern in harmful_categories:
        if pattern.search(text) and _REQUEST_INTENT.search(text):
            action = SafetyAction.BLOCK if source is SafetySource.CHAT else SafetyAction.WARN
            return _result(
                source,
                category,
                action,
                "Potentially harmful instructional intent requires a safety response."
                if source is SafetySource.CHAT
                else "Potentially harmful content was found in student evidence and requires review.",
            )

    if _SENSITIVE_EXPERIENCE.search(text) or any(
        pattern.search(text) for _, pattern in harmful_categories
    ):
        return _result(
            source,
            SafetyCategory.SENSITIVE_ALLOWED,
            SafetyAction.ALLOW,
            "Sensitive personal experience or discussion without a harmful request.",
        )

    return _result(
        source,
        SafetyCategory.SAFE,
        SafetyAction.ALLOW,
        "No sensitive or harmful content detected.",
    )


def validate_sensitive_content(text: str) -> SafetyResult:
    """Backward-compatible convenience wrapper for chat input."""
    return validate_input(text, SafetySource.CHAT)

