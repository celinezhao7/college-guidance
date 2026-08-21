"""Confirmed, structured additions layered on top of read-only DOCX profiles."""

import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from threading import RLock
from uuid import uuid4

from .schemas import ProfileAddition, ProfileAdditionRecord
from .profile_addition_repository import JsonProfileAdditionRepository, ProfileAdditionRepository


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADDITIONS_DIR = PROJECT_ROOT / "data" / "profile_additions"
_EXPERIENCE = re.compile(r"Experience\s+(\d+)\s*:\s*([^,\n*?]+)", re.IGNORECASE)
_repository_override: ProfileAdditionRepository | None = None
_records_lock = RLock()


def configure_profile_addition_repository(repository: ProfileAdditionRepository | None) -> None:
    """Inject a database-backed repository during deployment or testing."""
    global _repository_override
    _repository_override = repository


def _repository() -> ProfileAdditionRepository:
    return _repository_override or JsonProfileAdditionRepository(ADDITIONS_DIR)


def preview_addition(question: str, answer: str) -> ProfileAddition:
    """Extract a conservative structured draft, falling back to the user's words."""
    marker = _EXPERIENCE.search(question)
    fallback = ProfileAddition(
        experience_number=int(marker.group(1)) if marker else None,
        experience_title=marker.group(2).strip() if marker else None,
        action=answer.strip(),
        outcome="",
        reflection="",
        source="user_confirmed",
    )
    if not os.getenv("DASHSCOPE_API_KEY"):
        return fallback
    prompt = """Extract only explicitly stated student evidence from the answer.
Return JSON with keys action, outcome, reflection. Use an empty string when absent.
Do not infer, embellish, or convert plans into completed actions."""
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0,
            timeout=30,
            max_retries=1,
            extra_body={"enable_thinking": False},
        )
        response = llm.invoke(
            [("system", prompt), ("user", f"QUESTION:\n{question}\n\nANSWER:\n{answer}")]
        )
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        return fallback.model_copy(
            update={
                "action": str(data.get("action", "")).strip(),
                "outcome": str(data.get("outcome", "")).strip(),
                "reflection": str(data.get("reflection", "")).strip(),
            }
        )
    except Exception:
        return fallback


def load_additions(profile_id: str) -> list[dict]:
    return _repository().load(profile_id)


def _write_records(profile_id: str, records: list[dict]) -> None:
    _repository().write(profile_id, records)


def _normalized(value: object) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", str(value or "").casefold()).split())


def _same_target(left: dict, right: dict) -> bool:
    left_number, right_number = left.get("experience_number"), right.get("experience_number")
    if left_number is not None and right_number is not None:
        return left_number == right_number
    left_title, right_title = _normalized(left.get("experience_title")), _normalized(right.get("experience_title"))
    return bool(left_title and right_title and SequenceMatcher(None, left_title, right_title).ratio() >= 0.9)


def _near_duplicate(left: dict, right: dict) -> bool:
    if not _same_target(left, right):
        return False
    compared = []
    for field in ("action", "outcome", "reflection"):
        left_value, right_value = _normalized(left.get(field)), _normalized(right.get(field))
        if left_value or right_value:
            compared.append(SequenceMatcher(None, left_value, right_value).ratio())
    return bool(compared) and min(compared) >= 0.94


_NEGATIONS = {"not", "never", "no", "didnt", "didn", "没有", "没", "从未", "不是"}


def _conflicting_text(left: object, right: object) -> bool:
    left_text, right_text = _normalized(left), _normalized(right)
    if not left_text or not right_text:
        return False
    left_tokens, right_tokens = set(left_text.split()), set(right_text.split())
    left_numbers = set(re.findall(r"\d+(?:\.\d+)?", left_text))
    right_numbers = set(re.findall(r"\d+(?:\.\d+)?", right_text))
    without_numbers_left = re.sub(r"\d+(?:\.\d+)?", "", left_text)
    without_numbers_right = re.sub(r"\d+(?:\.\d+)?", "", right_text)
    similar_numeric_claim = (
        left_numbers and right_numbers and left_numbers != right_numbers
        and SequenceMatcher(None, without_numbers_left, without_numbers_right).ratio() >= 0.72
    )
    left_negative = bool(left_tokens & _NEGATIONS)
    right_negative = bool(right_tokens & _NEGATIONS)
    stripped_left = " ".join(token for token in left_text.split() if token not in _NEGATIONS)
    stripped_right = " ".join(token for token in right_text.split() if token not in _NEGATIONS)
    opposite_claim = (
        left_negative != right_negative
        and SequenceMatcher(None, stripped_left, stripped_right).ratio() >= 0.75
    )
    return bool(similar_numeric_claim or opposite_claim)


def addition_conflicts(profile_id: str, addition: ProfileAddition) -> list[str]:
    """Return fields with likely contradictions; this is a confirmation guard, not truth inference."""
    incoming = addition.model_dump()
    conflicts = set()
    for existing in load_additions(profile_id):
        if not _same_target(existing, incoming) or _near_duplicate(existing, incoming):
            continue
        for field in ("action", "outcome", "reflection"):
            if _conflicting_text(existing.get(field), incoming.get(field)):
                conflicts.add(field)
    return sorted(conflicts)


def save_addition(profile_id: str, addition: ProfileAddition) -> ProfileAdditionRecord:
    """Append a confirmed addition with an atomic file replacement."""
    with _records_lock:
        records = load_additions(profile_id)
        record = addition.model_dump()
        duplicate = any(_near_duplicate(existing, record) for existing in records)
        if not duplicate:
            record["id"] = uuid4().hex
            record["confirmed_at"] = datetime.now(timezone.utc).isoformat()
            records.append(record)
        else:
            record = next(
                existing
                for existing in records
                if _near_duplicate(existing, addition.model_dump())
            )
        _write_records(profile_id, records)
    return ProfileAdditionRecord.model_validate(record)


def list_addition_records(profile_id: str) -> list[ProfileAdditionRecord]:
    return [
        ProfileAdditionRecord.model_validate(item)
        for item in load_additions(profile_id)
        if item.get("id") and item.get("confirmed_at")
    ]


def update_addition(
    profile_id: str,
    addition_id: str,
    addition: ProfileAddition,
) -> ProfileAdditionRecord | None:
    with _records_lock:
        records = load_additions(profile_id)
        for index, existing in enumerate(records):
            if existing.get("id") != addition_id:
                continue
            updated = addition.model_dump()
            updated.update(
                id=addition_id,
                confirmed_at=datetime.now(timezone.utc).isoformat(),
            )
            records[index] = updated
            _write_records(profile_id, records)
            return ProfileAdditionRecord.model_validate(updated)
    return None


def delete_addition(profile_id: str, addition_id: str) -> bool:
    with _records_lock:
        records = load_additions(profile_id)
        remaining = [item for item in records if item.get("id") != addition_id]
        if len(remaining) == len(records):
            return False
        _write_records(profile_id, remaining)
        return True


def format_additions(profile_id: str) -> str:
    blocks = []
    for index, item in enumerate(load_additions(profile_id), start=1):
        label = (
            f"Experience {item['experience_number']}: {item.get('experience_title') or 'Confirmed addition'}"
            if item.get("experience_number")
            else f"User-confirmed addition {index}"
        )
        blocks.append(
            "\n".join(
                [
                    label,
                    "Evidence Reliability: User-confirmed session addition.",
                    f"Actions: {item.get('action') or 'Not supplied.'}",
                    f"Outcome: {item.get('outcome') or 'Not supplied.'}",
                    f"Reflection: {item.get('reflection') or 'Not supplied.'}",
                ]
            )
        )
    return "\n\n".join(blocks)
