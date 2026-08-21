"""Small, reviewed registry of school-official verification pages.

This deliberately avoids generic crawling. Every school, domain, and page type must
be reviewed and added to the registry before it can appear in recommendation output.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "official_school_sources.json"
ALLOWED_PAGE_KINDS = {"majors", "first_year_requirements", "cost"}


def _normalize(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def validated_official_url(url: str, allowed_domains: list[str]) -> str | None:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").casefold().rstrip(".")
    except ValueError:
        return None
    domains = [domain.casefold().rstrip(".") for domain in allowed_domains]
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or not any(hostname == domain or hostname.endswith("." + domain) for domain in domains)
    ):
        return None
    return url


@lru_cache(maxsize=1)
def load_official_source_registry() -> tuple[dict, ...]:
    if not REGISTRY_PATH.is_file():
        return ()
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    clean = []
    for school in payload if isinstance(payload, list) else []:
        if not isinstance(school, dict) or not school.get("school"):
            continue
        domains = [str(value) for value in school.get("allowed_domains", [])]
        pages = []
        for page in school.get("pages", []):
            if not isinstance(page, dict) or page.get("kind") not in ALLOWED_PAGE_KINDS:
                continue
            url = validated_official_url(str(page.get("url", "")), domains)
            if url:
                pages.append({"kind": page["kind"], "url": url, "status": "official_link"})
        if pages:
            clean.append({
                "school": str(school["school"]),
                "aliases": [str(value) for value in school.get("aliases", [])],
                "pages": pages,
            })
    return tuple(clean)


def official_sources_for_school(school_name: str) -> list[dict[str, str]]:
    target = _normalize(school_name)
    for school in load_official_source_registry():
        names = {_normalize(school["school"]), *(_normalize(value) for value in school["aliases"])}
        if target in names:
            return [dict(page) for page in school["pages"]]
    return []
