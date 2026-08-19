"""Low-latency post-generation validation with sentence-sized buffering."""

import re
import logging
from collections.abc import Iterable, Iterator

from .grounding_guard import (
    extract_experience_labels,
    find_ungrounded_experience_references,
)
from .models import SafetyAction, SafetyCategory
from .input_guard import validate_input
from .output_models import OutputAction, OutputCategory, OutputSafetyResult


logger = logging.getLogger(__name__)


_SECRET_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(
        r"\b(?:api[_ -]?key|access[_ -]?token|password|passwd|secret)\s*[:=]\s*['\"]?[^\s'\"]{6,}",
        re.IGNORECASE,
    ),
)
_PROMPT_LEAK = re.compile(
    r"(?:system|developer) (?:prompt|message|instructions?)\s*[:=]"
    r"|BEGIN (?:SYSTEM|DEVELOPER) (?:PROMPT|MESSAGE)"
    r"|# (?:CORE RULES|STUDENT EVIDENCE REFERENCES|USER MESSAGE RELEVANCE)",
    re.IGNORECASE,
)
_INTERNAL_DATA = re.compile(
    r"\b(?:latest\.[a-z0-9_.]+|matching_bachelors_fields|match_score)\b"
    r"|\[(?:latest|matching_bachelors_fields)\.[^\]]+\]",
    re.IGNORECASE,
)
_CIP_CODE = re.compile(r"\bCIP(?:\s+Code)?\s*:?\s*\d{2}\.\d{2}\b", re.IGNORECASE)
_ADMISSION_LABEL = re.compile(
    r"(?:admission|application)\s+(?:category|classification)\s*:\s*(?:reach|target|safety|likely)\b",
    re.IGNORECASE,
)
_EXPERIENCE_MARKER = re.compile(r"\bExperience\s+(\d+)\s*:", re.IGNORECASE)
_EVIDENCE_LINE_PREFIX = re.compile(
    r"(?:Primary Supporting Experience|Secondary Supporting Evidence)\s*:",
    re.IGNORECASE,
)
_STREAM_HOLDBACK_CHARS = 80
_MAX_EXPERIENCE_LINE_CHARS = 500


def _redact(text: str) -> str:
    result = text
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def validate_generated_output(
    text: str,
    *,
    application_type: str,
    reference_text: str = "",
) -> OutputSafetyResult:
    """Validate one not-yet-visible paragraph of generated output."""
    input_safety = validate_input(text, "chat")
    if not input_safety.allowed and input_safety.category is not SafetyCategory.PROMPT_INJECTION:
        return OutputSafetyResult(
            False,
            OutputCategory.POLICY_VIOLATION,
            OutputAction.BLOCK,
            "Generated text contains harmful instructional content.",
            "",
        )
    if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
        return OutputSafetyResult(
            True,
            OutputCategory.PII_SECRET,
            OutputAction.REDACT,
            "A secret or high-risk identifier was removed.",
            _redact(text),
        )
    if _PROMPT_LEAK.search(text):
        return OutputSafetyResult(
            False,
            OutputCategory.PROMPT_LEAK,
            OutputAction.BLOCK,
            "Generated text appears to expose hidden instructions.",
            "",
        )
    if _INTERNAL_DATA.search(text):
        return OutputSafetyResult(
            False,
            OutputCategory.INTERNAL_DATA,
            OutputAction.BLOCK,
            "Generated text exposes internal data fields.",
            "",
        )
    if application_type == "college_major" and (
        _CIP_CODE.search(text) or _ADMISSION_LABEL.search(text)
    ):
        return OutputSafetyResult(
            False,
            OutputCategory.POLICY_VIOLATION,
            OutputAction.BLOCK,
            "Generated college guidance violates a user-facing output rule.",
            "",
        )
    ungrounded = find_ungrounded_experience_references(text, reference_text)
    if ungrounded:
        return OutputSafetyResult(
            False,
            OutputCategory.UNGROUNDED_REFERENCE,
            OutputAction.BLOCK,
            f"Unknown or altered evidence labels: {', '.join(ungrounded)}.",
            "",
        )
    return OutputSafetyResult(
        True,
        OutputCategory.SAFE,
        OutputAction.ALLOW,
        "Output passed deterministic checks.",
        text,
    )


def guarded_output_stream(
    chunks: Iterable[str],
    *,
    application_type: str,
    language: str,
    reference_text: str = "",
) -> Iterator[str]:
    """Continuously release safe text while retaining a small inspection window."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        if _has_unfinished_experience_label(buffer, reference_text):
            if len(buffer) <= _MAX_EXPERIENCE_LINE_CHARS:
                continue
            yield _fallback(language)
            return

        full_result = validate_generated_output(
            buffer,
            application_type=application_type,
            reference_text=reference_text,
        )
        if not full_result.allowed:
            _log_block(full_result, application_type)
            yield _fallback(language)
            return
        if len(buffer) <= _STREAM_HOLDBACK_CHARS:
            continue

        release_at = len(buffer) - _STREAM_HOLDBACK_CHARS
        segment, remaining = buffer[:release_at], buffer[release_at:]
        segment_result = validate_generated_output(
            segment,
            application_type=application_type,
            reference_text=reference_text,
        )
        # A secret may begin in the emitted prefix and end in the retained tail.
        # In that rare case, hold everything until it can be redacted as a unit.
        if (
            full_result.action is OutputAction.REDACT
            and segment_result.action is not OutputAction.REDACT
        ):
            continue
        if not segment_result.allowed:
            _log_block(segment_result, application_type)
            yield _fallback(language)
            return
        yield segment_result.sanitized_text
        buffer = remaining

    if buffer:
        result = validate_generated_output(
            buffer,
            application_type=application_type,
            reference_text=reference_text,
        )
        if not result.allowed:
            _log_block(result, application_type)
            yield _fallback(language)
            return
        yield result.sanitized_text


def _has_unfinished_experience_label(buffer: str, reference_text: str) -> bool:
    """Hold an evidence label only until its exact source title can be checked."""
    labels = extract_experience_labels(reference_text)
    if not labels:
        return False
    prefixes = list(_EVIDENCE_LINE_PREFIX.finditer(buffer))
    if prefixes:
        after_prefix = buffer[prefixes[-1].end():]
        partial_label = " ".join(after_prefix.lower().split())
        if (
            not partial_label
            or "experience".startswith(partial_label)
            or re.fullmatch(r"experience\s*\d*\s*:?", partial_label)
        ):
            return True
    current_line = buffer[buffer.rfind("\n") + 1:]
    marker = _EXPERIENCE_MARKER.search(current_line)
    if _EVIDENCE_LINE_PREFIX.search(current_line) and marker is None:
        return True
    if marker is None:
        return False
    matching_labels = [
        label
        for label in labels
        if re.match(
            rf"Experience\s+{re.escape(marker.group(1))}\s*:",
            label,
            re.IGNORECASE,
        )
    ]
    if any(label in current_line[marker.start():] for label in matching_labels):
        return False
    # Once the line ends, the grounding validator can safely decide whether the
    # referenced number exists without leaking a partial label.
    return "\n" not in current_line[marker.start():]


def _log_block(result: OutputSafetyResult, application_type: str) -> None:
    logger.warning(
        "Output guard blocked generated content: mode=%s category=%s reason=%s",
        application_type,
        result.category.value,
        result.reason,
    )


def _fallback(language: str) -> str:
    return (
        "抱歉，生成内容的一部分没有通过安全性或准确性检查，因此未显示。请重试或换一种更明确的问法。"
        if language == "zh"
        else "Sorry, part of the generated response did not pass safety or accuracy checks, so it was not shown. Please try again or make the request more specific."
    )
