"""Confirmed, structured additions layered on top of read-only DOCX profiles."""

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schemas import ProfileAddition, ProfileAdditionRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADDITIONS_DIR = PROJECT_ROOT / "data" / "profile_additions"
_EXPERIENCE = re.compile(r"Experience\s+(\d+)\s*:\s*([^,\n*?]+)", re.IGNORECASE)


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


def _path(profile_id: str) -> Path:
    return ADDITIONS_DIR / f"{profile_id}.json"


def load_additions(profile_id: str) -> list[dict]:
    path = _path(profile_id)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write_records(profile_id: str, records: list[dict]) -> None:
    ADDITIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = _path(profile_id)
    fd, temporary = tempfile.mkstemp(dir=ADDITIONS_DIR, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_addition(profile_id: str, addition: ProfileAddition) -> ProfileAdditionRecord:
    """Append a confirmed addition with an atomic file replacement."""
    ADDITIONS_DIR.mkdir(parents=True, exist_ok=True)
    records = load_additions(profile_id)
    record = addition.model_dump()
    duplicate = any(
        all(existing.get(key) == value for key, value in record.items())
        for existing in records
    )
    if not duplicate:
        record["id"] = uuid4().hex
        record["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        records.append(record)
    else:
        record = next(
            existing
            for existing in records
            if all(existing.get(key) == value for key, value in addition.model_dump().items())
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
