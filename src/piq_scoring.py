"""Deterministic formatting for generated UC PIQ match scores."""

import re
from collections.abc import Iterable, Iterator
from decimal import Decimal, ROUND_HALF_UP


_UC_MATCH_SCORE = re.compile(
    r"(?P<prefix>(?:Match Score|匹配评分)\s*[:：]\s*)"
    r"(?P<score>[+-]?\d+(?:\.\d+)?)\s*(?:/\s*10)?",
    re.IGNORECASE,
)
_SCORE_BREAKDOWN = re.compile(
    r"(?P<prefix>.*?(?:Score Breakdown|评分明细)\s*[:：](?:\*\*)?\s*)"
    r"(?:Prompt Fit|题目契合度)\s*(?P<prompt>[+-]?\d+(?:\.\d+)?)\s*/\s*10\s*;\s*"
    r"(?:Evidence Depth|证据深度)\s*(?P<evidence>[+-]?\d+(?:\.\d+)?)\s*/\s*10\s*;\s*"
    r"(?:Personal Insight|个人洞察)\s*(?P<insight>[+-]?\d+(?:\.\d+)?)\s*/\s*10",
    re.IGNORECASE,
)


def _bounded_score(value: str) -> Decimal:
    return min(Decimal("10"), max(Decimal("0"), Decimal(value)))


def _display_dimension(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return str(int(rounded)) if rounded == rounded.to_integral() else str(rounded)


def calculated_uc_match_score(prompt: str, evidence: str, insight: str) -> Decimal:
    """Calculate the authoritative weighted PIQ score from its dimensions."""
    result = (
        _bounded_score(prompt) * Decimal("0.35")
        + _bounded_score(evidence) * Decimal("0.35")
        + _bounded_score(insight) * Decimal("0.30")
    )
    return result.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def normalize_uc_match_score(text: str) -> str:
    """Clamp a generated UC match score and render it consistently."""

    def replace(match: re.Match[str]) -> str:
        score = Decimal(match.group("score"))
        score = min(Decimal("10"), max(Decimal("0"), score))
        rounded = score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{match.group('prefix')}{rounded} / 10"

    return _UC_MATCH_SCORE.sub(replace, text)


def normalize_uc_match_score_stream(chunks: Iterable[str]) -> Iterator[str]:
    """Recompute scores from breakdowns and remove generated scratch arithmetic."""
    pending = ""
    held_score_line: str | None = None
    held_after_score: list[str] = []
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
            if held_score_line is None and _UC_MATCH_SCORE.search(line):
                held_score_line = line
                continue
            if held_score_line is not None:
                breakdown = _SCORE_BREAKDOWN.search(line)
                if breakdown:
                    prompt = _bounded_score(breakdown.group("prompt"))
                    evidence = _bounded_score(breakdown.group("evidence"))
                    insight = _bounded_score(breakdown.group("insight"))
                    calculated = calculated_uc_match_score(
                        str(prompt), str(evidence), str(insight)
                    )
                    score_line = _UC_MATCH_SCORE.sub(
                        lambda match: f"{match.group('prefix')}{calculated} / 10",
                        held_score_line,
                    )
                    yield score_line
                    yield from held_after_score
                    line_ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                    chinese = "评分明细" in breakdown.group("prefix")
                    if chinese:
                        yield (
                            f"**评分明细：** 题目契合度 {_display_dimension(prompt)}/10；"
                            f"证据深度 {_display_dimension(evidence)}/10；"
                            f"个人洞察 {_display_dimension(insight)}/10{line_ending}"
                        )
                    else:
                        yield (
                            f"**Score Breakdown:** Prompt Fit {_display_dimension(prompt)}/10; "
                            f"Evidence Depth {_display_dimension(evidence)}/10; "
                            f"Personal Insight {_display_dimension(insight)}/10{line_ending}"
                        )
                    held_score_line = None
                    held_after_score = []
                    continue
                held_after_score.append(line)
                if len(held_after_score) >= 4:
                    yield normalize_uc_match_score(held_score_line)
                    yield from held_after_score
                    held_score_line = None
                    held_after_score = []
                continue
            yield normalize_uc_match_score(line)
    if pending:
        if held_score_line is not None:
            held_after_score.append(pending)
        else:
            yield normalize_uc_match_score(pending)
    if held_score_line is not None:
        yield normalize_uc_match_score(held_score_line)
        yield from held_after_score
