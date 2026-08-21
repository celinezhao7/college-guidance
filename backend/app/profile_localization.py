"""Language-specific display copies of structured profiles.

Translations are never used as recommendation evidence. The source DOCX and
confirmed additions remain unchanged.
"""

import hashlib
import json
import os
from collections import OrderedDict
from threading import Lock

from langchain_openai import ChatOpenAI

from .schemas import StructuredStudentProfile


_cache: OrderedDict[str, StructuredStudentProfile] = OrderedDict()
_cache_lock = Lock()


def _translatable_values(profile: StructuredStudentProfile) -> list[str]:
    values = [profile.profile_name]
    values.extend(profile.academic_interests)
    values.extend(profile.background)
    values.extend(profile.core_themes)
    for experience in profile.experiences:
        values.extend([
            experience.experience_title,
            experience.category,
            experience.background,
            experience.challenge,
            experience.action,
            experience.outcome,
            experience.reflection,
        ])
        values.extend(experience.traits)
    return values


def _apply_translations(profile: StructuredStudentProfile, translated: list[str]) -> StructuredStudentProfile:
    localized = profile.model_copy(deep=True)
    iterator = iter(translated)
    localized.profile_name = next(iterator)
    localized.academic_interests = [next(iterator) for _ in localized.academic_interests]
    localized.background = [next(iterator) for _ in localized.background]
    localized.core_themes = [next(iterator) for _ in localized.core_themes]
    for experience in localized.experiences:
        experience.experience_title = next(iterator)
        experience.category = next(iterator)
        experience.background = next(iterator)
        experience.challenge = next(iterator)
        experience.action = next(iterator)
        experience.outcome = next(iterator)
        experience.reflection = next(iterator)
        experience.traits = [next(iterator) for _ in experience.traits]
    return localized


def localize_profile(profile: StructuredStudentProfile, language: str) -> StructuredStudentProfile:
    """Return a Chinese display copy while preserving all structural metadata."""
    if language != "zh" or not os.getenv("DASHSCOPE_API_KEY"):
        return profile
    source_values = _translatable_values(profile)
    fingerprint = hashlib.sha256(
        json.dumps(source_values, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    with _cache_lock:
        cached = _cache.get(fingerprint)
        if cached is not None:
            _cache.move_to_end(fingerprint)
    if cached is not None:
        return cached.model_copy(deep=True)

    prompt = """Translate every item in the JSON array into concise, natural Simplified Chinese.
Preserve factual meaning, qualifiers, numbers, and line breaks exactly. Do not strengthen claims.
Keep proper technical abbreviations such as AI when natural. Return only a JSON array of strings
with exactly the same number and order of items. Empty strings must remain empty strings."""
    try:
        llm = ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen3.5-flash-2026-02-23"),
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0,
            timeout=60,
            max_retries=1,
            extra_body={"enable_thinking": False},
        )
        response = llm.invoke([
            ("system", prompt),
            ("user", json.dumps(source_values, ensure_ascii=False)),
        ])
        content = response.content if isinstance(response.content, str) else str(response.content)
        translated = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        if not isinstance(translated, list) or len(translated) != len(source_values) or not all(isinstance(item, str) for item in translated):
            return profile
        localized = _apply_translations(profile, translated)
        with _cache_lock:
            _cache[fingerprint] = localized.model_copy(deep=True)
            _cache.move_to_end(fingerprint)
            while len(_cache) > 64:
                _cache.popitem(last=False)
        return localized
    except Exception:
        return profile
