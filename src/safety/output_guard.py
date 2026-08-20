"""Low-latency post-generation validation with sentence-sized buffering."""

import re
import logging
from collections.abc import Callable, Iterable, Iterator

from .grounding_guard import (
    extract_experience_labels,
    find_ungrounded_experience_references,
)
from .fact_guard import find_ungrounded_college_facts
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
_MAX_BUFFER_CHARS = 250_000
_RETRYABLE_CATEGORIES = {
    OutputCategory.INTERNAL_DATA,
    OutputCategory.POLICY_VIOLATION,
    OutputCategory.UNGROUNDED_REFERENCE,
    OutputCategory.UNGROUNDED_FACT,
}


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
    fact_reference: dict | None = None,
    final: bool = True,
) -> OutputSafetyResult:
    """Validate one not-yet-visible paragraph of generated output."""
    input_safety = validate_input(text, "chat")
    if input_safety.category is SafetyCategory.PROMPT_INJECTION:
        return OutputSafetyResult(
            False,
            OutputCategory.PROMPT_LEAK,
            OutputAction.BLOCK,
            "Generated text contains instruction-override or prompt-exfiltration content.",
            "",
        )
    if not input_safety.allowed:
        return OutputSafetyResult(
            False,
            OutputCategory.SENSITIVE_CONTENT,
            OutputAction.BLOCK,
            "Generated text contains harmful instructional content.",
            "",
        )
    if input_safety.action is SafetyAction.REDACT:
        return OutputSafetyResult(
            True,
            OutputCategory.PII_SECRET,
            OutputAction.REDACT,
            "A secret or high-risk identifier was removed.",
            input_safety.sanitized_text or "[REDACTED]",
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
    ungrounded_facts = find_ungrounded_college_facts(
        text,
        fact_reference,
        final=final,
    )
    if ungrounded_facts:
        return OutputSafetyResult(
            False,
            OutputCategory.UNGROUNDED_FACT,
            OutputAction.BLOCK,
            f"Generated college facts are not present in the supplied records: {'; '.join(ungrounded_facts)}.",
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
    retry_factory: Callable[[], Iterable[str]] | None = None,
    fact_reference: dict | None = None,
) -> Iterator[str]:
    """Stream validated text while retaining a small cross-chunk safety window."""
    buffer = ""
    released_any = False
    for chunk in chunks:
        if not isinstance(chunk, str):
            continue
        buffer += chunk
        if len(buffer) > _MAX_BUFFER_CHARS:
            logger.warning("Output guard rejected oversized generated content: mode=%s", application_type)
            yield _fallback(language, OutputCategory.POLICY_VIOLATION)
            return

        if _has_unfinished_experience_label(buffer, reference_text):
            if len(buffer) <= _MAX_EXPERIENCE_LINE_CHARS:
                continue
            yield _fallback(language, OutputCategory.UNGROUNDED_REFERENCE)
            return

        full_result = validate_generated_output(
            buffer,
            application_type=application_type,
            reference_text=reference_text,
            fact_reference=fact_reference,
            final=False,
        )
        if not full_result.allowed:
            _log_block(full_result, application_type)
            if (
                not released_any
                and retry_factory is not None
                and full_result.category in _RETRYABLE_CATEGORIES
            ):
                yield from guarded_output_stream(
                    retry_factory(),
                    application_type=application_type,
                    language=language,
                    reference_text=reference_text,
                    fact_reference=fact_reference,
                )
                return
            yield _fallback(language, full_result.category)
            return
        if len(buffer) <= _STREAM_HOLDBACK_CHARS:
            continue

        release_at = len(buffer) - _STREAM_HOLDBACK_CHARS
        segment, remaining = buffer[:release_at], buffer[release_at:]
        segment_result = validate_generated_output(
            segment,
            application_type=application_type,
            reference_text=reference_text,
            fact_reference=fact_reference,
            final=False,
        )
        if (
            full_result.action is OutputAction.REDACT
            and segment_result.action is not OutputAction.REDACT
        ):
            continue
        if not segment_result.allowed:
            _log_block(segment_result, application_type)
            yield _fallback(language, segment_result.category)
            return
        if segment_result.sanitized_text:
            released_any = True
            yield segment_result.sanitized_text
        buffer = remaining

    if buffer:
        result = validate_generated_output(
            buffer,
            application_type=application_type,
            reference_text=reference_text,
            fact_reference=fact_reference,
            final=True,
        )
        if not result.allowed:
            _log_block(result, application_type)
            if (
                not released_any
                and retry_factory is not None
                and result.category in _RETRYABLE_CATEGORIES
            ):
                yield from guarded_output_stream(
                    retry_factory(),
                    application_type=application_type,
                    language=language,
                    reference_text=reference_text,
                    fact_reference=fact_reference,
                )
                return
            yield _fallback(language, result.category)
            return
        if result.sanitized_text:
            yield result.sanitized_text


def _has_unfinished_experience_label(buffer: str, reference_text: str) -> bool:
    """Hold a partial evidence label until its experience number can be checked."""
    labels = extract_experience_labels(reference_text)
    if not labels:
        return False
    prefixes = list(_EVIDENCE_LINE_PREFIX.finditer(buffer))
    if prefixes:
        after_prefix = buffer[prefixes[-1].end():]
        partial_label = " ".join(after_prefix.lower().split())
        if not partial_label or "experience".startswith(partial_label) or re.fullmatch(
            r"experience\s*\d*\s*:?", partial_label
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
    return "\n" not in current_line[marker.start():]


def _log_block(result: OutputSafetyResult, application_type: str) -> None:
    logger.warning(
        "Output guard blocked generated content: mode=%s category=%s reason=%s",
        application_type,
        result.category.value,
        result.reason,
    )


def _fallback(language: str, category: OutputCategory) -> str:
    accuracy_failure = category in {
        OutputCategory.UNGROUNDED_REFERENCE,
        OutputCategory.UNGROUNDED_FACT,
    }
    if language == "zh":
        return (
            "抱歉，我无法根据现有学生资料验证这份答案，因此没有显示可能不准确的内容。请补充资料或换一种更明确的问法。"
            if accuracy_failure
            else "抱歉，生成的答案没有通过安全检查，因此未显示。请调整问题后重试。"
        )
    return (
        "Sorry, I could not verify this answer against the available student evidence, so potentially inaccurate content was not shown. Add supporting information or make the request more specific."
        if accuracy_failure
        else "Sorry, the generated answer did not pass the safety check, so it was not shown. Please revise the request and try again."
    )
