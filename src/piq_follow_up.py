"""Deterministic state helpers for UC PIQ evidence follow-ups."""

import re
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass


def _max_follow_up_rounds() -> int:
    try:
        configured = int(os.getenv("PIQ_MAX_FOLLOW_UP_ROUNDS", "5"))
    except ValueError:
        configured = 5
    return min(10, max(1, configured))


PIQ_MAX_FOLLOW_UP_ROUNDS = _max_follow_up_rounds()


_FOLLOW_UP_MARKER = re.compile(
    r"(?:Information Needed\s*(?:[—-]\s*Question\s*(\d+)"
    r"|\(\s*Round\s*(\d+)\s*/\s*\d+\s*\))"
    r"|需要补充的信息\s*(?:[—-]\s*第?\s*(\d+)\s*个?问题"
    r"|[（(]\s*第?\s*(\d+)\s*/\s*\d+\s*轮?\s*[）)]))",
    re.IGNORECASE,
)

_DIRECT_RECOMMENDATION = re.compile(
    r"(?:\b(?:skip all|skip (?:the )?(?:remaining )?questions?|skip and recommend|"
    r"recommend now|just recommend|direct(?:ly)? recommend|"
    r"continue anyway|continue with current|no more questions?|don'?t ask|do not ask)\b"
    r"|全部跳过|跳过所有|直接推荐|不用问|不要再问|不想补充|无法补充|就这样推荐)",
    re.IGNORECASE,
)

_SKIP_CURRENT_QUESTION = re.compile(
    r"(?:^\s*(?:skip|pass)\s*$|\bskip (?:this|current|that) question\b|"
    r"\bask (?:a )?different question\b|跳过这(?:一)?题|跳过当前问题|换一个问题|"
    r"^\s*(?:跳过|不知道)\s*$)",
    re.IGNORECASE,
)

_ADD_INFORMATION = re.compile(
    r"(?:\b(?:add (?:more |missing )?information|provide (?:more |missing )?information|"
    r"improve (?:the )?recommendations?)\b|补充信息|完善推荐|改善推荐)",
    re.IGNORECASE,
)

_EVIDENCE_WARNING = re.compile(
    r"(?:More Information Recommended|建议补充更多信息)",
    re.IGNORECASE,
)

_EXPERIENCE_START = re.compile(r"(?m)^Experience\s+\d+\s*:\s*[^\r\n]+")
_ACTION_EVIDENCE = re.compile(
    r"(?im)^(?:Actions?|Activities|Responsibilities|Role)\s*:"
)
_OUTCOME_EVIDENCE = re.compile(
    r"(?im)^(?:Outcome|Impact|Skills Developed|Leadership Evidence)\s*:"
)
_REFLECTION_EVIDENCE = re.compile(r"(?im)^Reflection\s*:")
_MATERIAL_LIMITATION = re.compile(
    r"(?:not provided|not documented|self-reported interest only|"
    r"no related (?:course|research|service|activity)|no independent|"
    r"no broader|one-time activity|course-based interest|occasionally|"
    r"has not yet|\buncertain\b|\bunsure\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PiqEvidenceSummary:
    experience_count: int
    well_supported_count: int
    requested_count: int

    @property
    def requires_initial_follow_up(self) -> bool:
        return self.well_supported_count < self.requested_count


@dataclass(frozen=True)
class PiqEvidenceGap:
    experience_label: str
    field: str
    priority: int


def _field_content(block: str, marker: re.Pattern[str]) -> str:
    match = marker.search(block)
    if not match:
        return ""
    tail = block[match.end():]
    next_heading = re.search(r"(?m)^[A-Za-z][A-Za-z /-]+\s*:", tail)
    return tail[:next_heading.start() if next_heading else None].strip()


def _usable_field(block: str, marker: re.Pattern[str]) -> bool:
    content = _field_content(block, marker)
    return bool(content) and not bool(_MATERIAL_LIMITATION.search(content))


def rank_piq_evidence_gaps(student_context: str) -> list[PiqEvidenceGap]:
    """Rank missing facts by likelihood of changing recommendation viability."""
    starts = list(_EXPERIENCE_START.finditer(student_context))
    gaps: list[PiqEvidenceGap] = []
    field_rules = (
        ("action", _ACTION_EVIDENCE, 30),
        ("reflection", _REFLECTION_EVIDENCE, 20),
        ("outcome", _OUTCOME_EVIDENCE, 10),
    )
    for index, match in enumerate(starts):
        block = student_context[match.start(): starts[index + 1].start() if index + 1 < len(starts) else None]
        present_count = sum(_usable_field(block, marker) for _, marker, _ in field_rules)
        # An experience missing only one key field is closer to becoming a viable
        # candidate, so its answer has greater expected decision value.
        completeness_bonus = present_count * 10
        for field, marker, field_priority in field_rules:
            if not _usable_field(block, marker):
                gaps.append(PiqEvidenceGap(match.group(0).strip(), field, completeness_bonus + field_priority))
    return sorted(gaps, key=lambda gap: (-gap.priority, gap.experience_label, gap.field))


def summarize_piq_profile_evidence(
    student_context: str,
    requested_count: int,
) -> PiqEvidenceSummary:
    """Count experiences that have action, outcome, and reflection evidence."""
    starts = list(_EXPERIENCE_START.finditer(student_context))
    blocks = [
        student_context[match.start() : starts[index + 1].start() if index + 1 < len(starts) else None]
        for index, match in enumerate(starts)
    ]
    well_supported = sum(
        _usable_field(block, _ACTION_EVIDENCE)
        and _usable_field(block, _OUTCOME_EVIDENCE)
        and _usable_field(block, _REFLECTION_EVIDENCE)
        for block in blocks
    )
    return PiqEvidenceSummary(
        experience_count=len(blocks),
        well_supported_count=well_supported,
        requested_count=max(1, requested_count),
    )


def piq_follow_up_round(history: list[dict[str, str]]) -> int:
    """Return the highest completed PIQ follow-up round recorded in history."""
    highest = 0
    for turn in history:
        if turn.get("role") != "assistant":
            continue
        for match in _FOLLOW_UP_MARKER.finditer(turn.get("content", "")):
            value = next(group for group in match.groups() if group is not None)
            highest = max(highest, int(value))
    return min(highest, PIQ_MAX_FOLLOW_UP_ROUNDS)


def requests_direct_piq_recommendation(message: str) -> bool:
    """Detect an explicit request to stop follow-ups and recommend now."""
    if _SKIP_CURRENT_QUESTION.search(message):
        return False
    return bool(_DIRECT_RECOMMENDATION.search(message))


def requests_skip_current_piq_question(message: str) -> bool:
    """Detect a request to skip one gap while continuing the follow-up flow."""
    return bool(_SKIP_CURRENT_QUESTION.search(message))


def requests_piq_information_follow_up(message: str) -> bool:
    """Detect a user's choice to improve recommendations with more evidence."""
    return bool(_ADD_INFORMATION.search(message))


def has_piq_evidence_warning(history: list[dict[str, str]]) -> bool:
    """Return whether the latest assistant response offered an evidence choice."""
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            return bool(_EVIDENCE_WARNING.search(turn.get("content", "")))
    return False


def normalize_piq_follow_up_heading(text: str, language: str) -> str:
    """Render a generated follow-up marker in the requested interface language."""
    def replace(match: re.Match[str]) -> str:
        round_number = next(group for group in match.groups() if group is not None)
        if language == "zh":
            return f"需要补充的信息 — 第 {round_number} 个问题"
        return f"Information Needed — Question {round_number}"

    normalized = _FOLLOW_UP_MARKER.sub(replace, text)
    warning_heading = (
        "建议补充更多信息" if language == "zh" else "More Information Recommended"
    )
    return _EVIDENCE_WARNING.sub(warning_heading, normalized)


def normalize_piq_follow_up_heading_stream(
    chunks: Iterable[str],
    language: str,
) -> Iterator[str]:
    """Normalize complete follow-up headings while preserving streaming."""
    pending = ""
    for chunk in chunks:
        if not isinstance(chunk, str):
            continue
        pending += chunk
        lines = pending.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            pending = lines.pop()
        else:
            pending = ""
        for line in lines:
            yield normalize_piq_follow_up_heading(line, language)
    if pending:
        yield normalize_piq_follow_up_heading(pending, language)
