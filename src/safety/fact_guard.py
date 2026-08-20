"""Deterministic grounding checks for College Scorecard facts."""

import re


_RANKED_HEADING = re.compile(r"^###\s+\d+\s*[.):-]\s*(.+?)\s*$", re.MULTILINE)
_PERCENT = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%")
_DOLLARS = re.compile(r"\$\s*([\d,]+)(?![\d,])")
_STUDENT_SIZE = re.compile(
    r"(?<!\d)([\d,]+)\s*(?:undergraduates?|undergraduate students?|本科生)(?!\w)",
    re.IGNORECASE,
)
_FIELD_LINE = re.compile(
    r"^(?:[-*]\s*)?(?:\*\*)?(?:Matching (?:reported )?field|Reported field|"
    r"匹配(?:的)?(?:本科)?专业领域|相关(?:本科)?专业领域)(?:\*\*)?\s*[:：]\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def find_ungrounded_college_facts(
    text: str,
    fact_reference: dict | None,
    *,
    final: bool,
) -> tuple[str, ...]:
    if not fact_reference or not fact_reference.get("schools"):
        return ()

    checked_text = text if final or text.endswith(("\n", "\r")) else text.rpartition("\n")[0]
    if not checked_text:
        return ()

    schools = fact_reference["schools"]
    normalized_names = {
        _normalize(school.get("name", "")) for school in schools if school.get("name")
    }
    allowed_percentages = {
        float(school["admission_rate"]) * 100
        for school in schools
        if school.get("admission_rate") is not None
    }
    allowed_costs = {
        round(float(value))
        for school in schools
        for value in (school.get("cost"), school.get("net_price"))
        if value is not None
    }
    allowed_sizes = {
        round(float(school["size"]))
        for school in schools
        if school.get("size") is not None
    }
    allowed_fields = {
        _normalize(field)
        for school in schools
        for field in school.get("fields", [])
        if field
    }

    issues: list[str] = []
    for heading in _RANKED_HEADING.findall(checked_text):
        normalized_heading = _normalize(heading)
        if normalized_names and not any(name in normalized_heading for name in normalized_names):
            issues.append(f"unrecognized school heading: {heading}")

    for raw in _PERCENT.findall(checked_text):
        value = float(raw)
        if allowed_percentages and not any(abs(value - expected) <= 0.11 for expected in allowed_percentages):
            issues.append(f"unsupported percentage: {raw}%")

    for raw in _DOLLARS.findall(checked_text):
        value = int(raw.replace(",", ""))
        if allowed_costs and value not in allowed_costs:
            issues.append(f"unsupported cost: ${raw}")

    for raw in _STUDENT_SIZE.findall(checked_text):
        value = int(raw.replace(",", ""))
        if allowed_sizes and value not in allowed_sizes:
            issues.append(f"unsupported undergraduate size: {raw}")

    for raw in _FIELD_LINE.findall(checked_text):
        field = _normalize(raw.strip("*_` "))
        if allowed_fields and field not in allowed_fields:
            issues.append(f"unsupported reported field: {raw}")

    return tuple(dict.fromkeys(issues))


def _normalize(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())
