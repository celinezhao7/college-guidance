"""Deterministic quality-first selection for a four-PIQ portfolio."""

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PiqCandidate:
    piq_number: int
    prompt_fit: float
    evidence_depth: float
    personal_insight: float
    primary_experience: str
    traits: tuple[str, ...]
    story_type: str

    @property
    def score(self) -> float:
        values = [min(10.0, max(0.0, value)) for value in (self.prompt_fit, self.evidence_depth, self.personal_insight)]
        return round(values[0] * 0.35 + values[1] * 0.35 + values[2] * 0.30, 1)


@dataclass(frozen=True)
class PortfolioSelection:
    selected: tuple[PiqCandidate, ...]
    substitution: tuple[int, int, float] | None = None


def _diversity_value(candidates: list[PiqCandidate]) -> int:
    experiences = {item.primary_experience.casefold() for item in candidates if item.primary_experience.strip()}
    traits = {trait.casefold() for item in candidates for trait in item.traits if trait.strip()}
    story_types = {item.story_type.casefold() for item in candidates if item.story_type.strip()}
    return len(experiences) + len(traits) + len(story_types)


def select_four_piq_portfolio(candidates: list[PiqCandidate], comparable_gap: float = 0.5) -> PortfolioSelection:
    unique = {candidate.piq_number: candidate for candidate in candidates if 1 <= candidate.piq_number <= 8}
    ranked = sorted(unique.values(), key=lambda item: (-item.score, item.piq_number))
    if len(ranked) < 4:
        raise ValueError("Four distinct PIQ candidates are required.")
    selected = ranked[:4]
    strongest_outside = ranked[4] if len(ranked) > 4 else None
    substitution = None
    if strongest_outside is not None:
        weakest = selected[-1]
        gap = round(weakest.score - strongest_outside.score, 1)
        proposed = selected[:-1] + [strongest_outside]
        if gap <= comparable_gap and _diversity_value(proposed) > _diversity_value(selected):
            selected = proposed
            substitution = (weakest.piq_number, strongest_outside.piq_number, gap)
    return PortfolioSelection(tuple(selected), substitution)


def _json_payload(value: str) -> object:
    cleaned = value.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    return json.loads(match.group(0) if match else cleaned)


def assess_and_select_portfolio(llm, student_context: str) -> PortfolioSelection | None:
    """Ask the model only for grounded dimensions; calculate scores and select in code."""
    prompt = """Assess all eight UC PIQs independently from the supplied student evidence.
Return only a JSON array of eight objects with keys: piq_number, prompt_fit,
evidence_depth, personal_insight, primary_experience, traits, story_type.
Scores must be numbers from 0 to 10. primary_experience must be one exact documented
Experience label. traits must be a short JSON string array grounded in evidence.
story_type must be one of academic_technical, leadership_community,
challenge_growth, creative_personal, responsibility_service. Do not recommend or
select; this step only creates comparable candidate evidence.

STUDENT EVIDENCE:
""" + student_context
    try:
        response = llm.invoke([
            ("system", "Use only supplied evidence. Return valid JSON and no prose."),
            ("user", prompt),
        ])
        raw = response.content if isinstance(response.content, str) else str(response.content)
        payload = _json_payload(raw)
        if not isinstance(payload, list):
            return None
        candidates = [PiqCandidate(
            piq_number=int(item["piq_number"]),
            prompt_fit=float(item["prompt_fit"]),
            evidence_depth=float(item["evidence_depth"]),
            personal_insight=float(item["personal_insight"]),
            primary_experience=str(item["primary_experience"]),
            traits=tuple(str(value) for value in item.get("traits", [])),
            story_type=str(item["story_type"]),
        ) for item in payload if isinstance(item, dict)]
        if {item.piq_number for item in candidates} != set(range(1, 9)):
            return None
        documented_labels = {
            match.group(0).strip().casefold()
            for match in re.finditer(r"(?m)^Experience\s+\d+\s*:\s*[^\r\n]+", student_context)
        }
        allowed_story_types = {
            "academic_technical", "leadership_community", "challenge_growth",
            "creative_personal", "responsibility_service",
        }
        if any(
            item.primary_experience.strip().casefold() not in documented_labels
            or item.story_type not in allowed_story_types
            for item in candidates
        ):
            return None
        return select_four_piq_portfolio(candidates)
    except Exception:
        return None


def portfolio_instruction(selection: PortfolioSelection) -> str:
    rows = [
        {
            "piq_number": item.piq_number,
            "prompt_fit": min(10, max(0, item.prompt_fit)),
            "evidence_depth": min(10, max(0, item.evidence_depth)),
            "personal_insight": min(10, max(0, item.personal_insight)),
            "match_score": item.score,
            "primary_experience": item.primary_experience,
            "traits": list(item.traits),
            "story_type": item.story_type,
        }
        for item in selection.selected
    ]
    substitution = selection.substitution or "none"
    return f"""

# CODE-ENFORCED FOUR-PIQ SELECTION

When returning four recommendations, use exactly these PIQs in this order and use
the supplied independent dimension scores. The application calculated Match Score
and performed the quality-first diversity comparison in code; do not replace,
reorder, or rescore them.

{json.dumps(rows, ensure_ascii=False)}

Deterministic diversity substitution: {substitution}.
"""
