"""Deterministic unified view of original and user-confirmed profile evidence."""

import re
from functools import lru_cache
from pathlib import Path

from docx import Document

from .profile_service import StudentProfile, get_profile_directory
from .schemas import ProfileAdditionRecord, ProfileEvidenceSource, StructuredExperience, StructuredStudentProfile


_EXPERIENCE = re.compile(r"^Experience\s+(\d+)\s*:\s*(.+)$", re.IGNORECASE)
_FIELD = re.compile(r"^([A-Za-z][A-Za-z /-]+):\s*(.*)$")
_WRAPPER_HEADINGS = {
    "the student",
    "the student learned",
    "the student demonstrated",
    "the student realized",
    "the student taught",
    "the student balanced",
    "students gained",
}


@lru_cache(maxsize=64)
def _cached_docx_text(path_value: str, modified_ns: int) -> str:
    # modified_ns invalidates the cache when a profile file is replaced.
    path = Path(path_value)
    return "\n".join(p.text.strip() for p in Document(path).paragraphs if p.text.strip())


def _docx_text(path: Path) -> str:
    return _cached_docx_text(str(path.resolve()), path.stat().st_mtime_ns)


def _clean_lines(value: str) -> list[str]:
    return [line.strip().removeprefix("- ").strip() for line in value.splitlines() if line.strip() and not line.strip().lower().startswith("the student:")]


def _parse_fields(block: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current = ""
    for raw_line in block.splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        marker = _FIELD.match(line)
        if marker:
            heading = marker.group(1).strip().lower()
            if heading in _WRAPPER_HEADINGS:
                continue
            current = heading
            fields.setdefault(current, [])
            if marker.group(2).strip():
                fields[current].append(marker.group(2).strip())
        elif current:
            fields[current].append(line)
    return {key: "\n".join(_clean_lines("\n".join(value))) for key, value in fields.items()}


def _field(fields: dict[str, str], *names: str) -> str:
    return "\n".join(fields[name] for name in names if fields.get(name)).strip()


def _summary_list(summary: str, heading: str) -> list[str]:
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}:\s*\n(.*?)(?=^[A-Za-z][A-Za-z ]+:\s*$|\Z)")
    match = pattern.search(summary)
    return _clean_lines(match.group(1)) if match else []


def _append_unique(base: str, additions: list[str]) -> str:
    values = [line for line in base.splitlines() if line.strip()]
    fingerprints = {line.strip().casefold() for line in values}
    for addition in additions:
        for line in addition.splitlines():
            clean = line.strip()
            if clean and clean.casefold() not in fingerprints:
                values.append(clean)
                fingerprints.add(clean.casefold())
    return "\n".join(values)


def build_structured_profile(profile: StudentProfile, additions: list[ProfileAdditionRecord]) -> StructuredStudentProfile:
    text = _docx_text(get_profile_directory() / profile.filename)
    blocks = [block.strip() for block in text.split("@@@") if block.strip()]
    summary = blocks[0] if blocks else ""
    experiences: list[StructuredExperience] = []
    by_number: dict[int, StructuredExperience] = {}
    for block in blocks[1:]:
        marker = _EXPERIENCE.match(block.splitlines()[0].strip())
        if not marker:
            continue
        number = int(marker.group(1))
        fields = _parse_fields(block)
        experience = StructuredExperience(
            experience_number=number, experience_title=marker.group(2).strip(),
            category=fields.get("category", ""), background=fields.get("background", ""),
            challenge=fields.get("challenge", ""),
            action=_field(fields, "actions", "activities", "responsibilities"),
            outcome=_field(fields, "outcome", "impact"), reflection=fields.get("reflection", ""),
            traits=[item.strip() for item in fields.get("themes", "").split(",") if item.strip()],
            status="documented", sources=[ProfileEvidenceSource(kind="original_profile", label=profile.filename)],
        )
        experiences.append(experience)
        by_number[number] = experience

    unnumbered: list[ProfileAdditionRecord] = []
    for addition in additions:
        target = by_number.get(addition.experience_number or -1)
        if target is None:
            unnumbered.append(addition)
            continue
        target.action = _append_unique(target.action, [addition.action])
        target.outcome = _append_unique(target.outcome, [addition.outcome])
        target.reflection = _append_unique(target.reflection, [addition.reflection])
        target.status = "enriched"
        target.additions.append(addition)
        target.sources.append(ProfileEvidenceSource(kind="user_confirmed", label="User-confirmed addition", record_id=addition.id, confirmed_at=addition.confirmed_at))

    for addition in unnumbered:
        experiences.append(StructuredExperience(
            experience_number=addition.experience_number,
            experience_title=addition.experience_title or "User-confirmed experience",
            action=addition.action, outcome=addition.outcome, reflection=addition.reflection,
            status="user_confirmed", additions=[addition],
            sources=[ProfileEvidenceSource(kind="user_confirmed", label="User-confirmed addition", record_id=addition.id, confirmed_at=addition.confirmed_at)],
        ))
    for experience in experiences:
        experience.missing_fields = [field for field in ("action", "outcome", "reflection") if not getattr(experience, field).strip()]
    return StructuredStudentProfile(
        profile_id=profile.id, profile_name=profile.display_name,
        academic_interests=_summary_list(summary, "Academic Interest"),
        background=_summary_list(summary, "Background"), core_themes=_summary_list(summary, "Core Themes"),
        experiences=experiences,
    )
