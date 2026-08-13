import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from i18n import output_language_instruction


SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools.json"
CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "scorecard_school_catalog.json"

PROGRAM_FIELDS = {
    "computer": "latest.academics.program_percentage.computer",
    "data science": "latest.academics.program_percentage.computer",
    "engineering": "latest.academics.program_percentage.engineering",
    "business": "latest.academics.program_percentage.business_marketing",
    "psychology": "latest.academics.program_percentage.psychology",
    "biology": "latest.academics.program_percentage.biological",
    "art": "latest.academics.program_percentage.visual_performing",
    "design": "latest.academics.program_percentage.visual_performing",
    "social science": "latest.academics.program_percentage.social_science",
    "计算机": "latest.academics.program_percentage.computer",
    "数据科学": "latest.academics.program_percentage.computer",
    "工程": "latest.academics.program_percentage.engineering",
    "商科": "latest.academics.program_percentage.business_marketing",
    "心理": "latest.academics.program_percentage.psychology",
    "生物": "latest.academics.program_percentage.biological",
    "艺术": "latest.academics.program_percentage.visual_performing",
    "设计": "latest.academics.program_percentage.visual_performing",
    "社会科学": "latest.academics.program_percentage.social_science",
}

UC_SYSTEM_ALIASES = {"uc", "uc schools", "university of california"}

MAJOR_SYSTEM_PROMPT = """You are a college major recommendation assistant.
Use only the supplied student evidence. Recommend five undergraduate major paths,
ranked from strongest to weakest fit.

Evidence rules:
- Cite every supporting experience using its complete first-line label exactly,
  including its number, for example "Experience 2: Computer Science Journey".
- After each experience label, cite 1-3 concrete documented facts as evidence.
- Preserve the source's Evidence Reliability qualification. An intellectual
  interest must not be described as formal research or direct project experience.
- Label a recommendation "Direct fit" only when documented actions support it;
  otherwise label it "Exploration to validate".
- If evidence for a recommendation is weak, say so instead of filling gaps.

For each recommendation provide: major name, fit level, why it fits, supporting
evidence, skills/interests it develops, evidence limitations, and one question
the student should investigate before choosing it. Do not predict admission or
career outcomes, and do not claim experience that is not documented. End with a
short comparison of the top two choices."""

COLLEGE_SYSTEM_PROMPT = """You are a US undergraduate college recommendation
assistant. Use only the supplied student profile, preferences, and College
Scorecard records.

Evidence rules:
- Do not convert overall admission rate into the student's admission chance.
- The requested competition level describes institutional selectivity only.
- Do not label schools Reach, Target, Safety, or Likely. Describe institutional
  selectivity using only the reported overall admission rate.
- A target preference means the student wants the school considered; it does not
  mean the school is an academic match.
- Cite the supplied data fields behind each factual statement. Explicitly write
  "data unavailable" when a needed field is missing.
- Never invent rankings, specific programs, campus qualities, admission policies,
  or requirements.

Return sections for Target Schools and Other Data-Supported Matches. For each
school include: why it was included, verified Scorecard facts, selectivity context,
cost context, fit limitations, and what must be verified on official university
websites. End with Data Limitations, not an admission prediction."""

SCHOOL_MAJOR_SYSTEM_PROMPT = """You are a school-specific undergraduate major
matching assistant. Use only the documented student evidence and the supplied
College Scorecard four-digit CIP records. The records are broad federal fields of
study reported at bachelor's credential level (3); they may not equal the exact
catalog major name or confirm current availability.

For each target college, recommend up to five reported fields that fit the student.
Cite the exact Scorecard title and CIP code, cite exact numbered student experiences
with concrete facts, explain limitations, and tell the user to verify the exact
major/concentration name on the official college catalog. Never invent a program."""


def ask(prompt: str, default: str = "") -> str:
    value = input(f"{prompt}: ").strip()
    return value or default


def stream_response(llm, system_prompt: str, user_prompt: str) -> None:
    for chunk in llm.stream([("system", system_prompt), ("user", user_prompt)]):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print()


def choose_matching_path(language="en") -> str | None:
    if language == "zh":
        print("\n请选择起点：\n")
        print("1. 我有目标大学——帮我选择专业")
        print("2. 我有目标专业——帮我选择大学")
        print("3. 大学和专业都不确定——推荐专业方向")
        choice = input("\n请输入选项（1、2 或 3）：").strip()
    else:
        print("\nChoose your starting point:\n")
        print("1. I have target colleges - help me choose majors")
        print("2. I have a target major - help me choose colleges")
        print("3. I am unsure about both - recommend major directions")
        choice = input("\nEnter choice (1, 2, or 3): ").strip()
    return {"1": "college_first", "2": "major_first", "3": "explore"}.get(choice)


def recommend_majors(llm, student_context: str, evidence_labels: list[str], language="en") -> None:
    prompt = f"""=== DOCUMENTED STUDENT EVIDENCE ===
{student_context}

Recommend five well-supported undergraduate major paths. Include related or
interdisciplinary alternatives where the evidence supports them."""
    print("\n" + "=" * 60)
    print("MAJOR RECOMMENDATIONS")
    print("=" * 60 + "\n")
    print("Evidence loaded from data/student via chroma/student:")
    for label in evidence_labels:
        print(f"- {label}")
    print()
    stream_response(llm, MAJOR_SYSTEM_PROMPT + output_language_instruction(language), prompt)


def fetch_bachelors_fields_for_schools(school_ids: list[int]) -> dict[int, list[dict]]:
    api_key = os.getenv("COLLEGE_SCORECARD_API_KEY")
    if not api_key:
        raise RuntimeError("COLLEGE_SCORECARD_API_KEY is missing from .env.")
    params = {
        "api_key": api_key,
        "id": ",".join(str(school_id) for school_id in school_ids),
        "fields": (
            "id,school.name,latest.programs.cip_4_digit.title,"
            "latest.programs.cip_4_digit.code,"
            "latest.programs.cip_4_digit.credential.level"
        ),
    }
    try:
        with urlopen(f"{SCORECARD_URL}?{urlencode(params)}", timeout=45) as response:
            results = json.load(response).get("results", [])
    except HTTPError as exc:
        raise RuntimeError(f"College Scorecard programs returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not load College Scorecard programs: {exc}") from exc
    fields_by_school = {}
    for school in results:
        programs = school.get("latest.programs.cip_4_digit", []) or []
        bachelors = {
            (str(item.get("code", "")), item.get("title", ""))
            for item in programs
            if item.get("credential", {}).get("level") == 3 and item.get("title")
        }
        fields_by_school[school["id"]] = [
            {"cip_code": code, "title": title} for code, title in sorted(bachelors)
        ]
    return fields_by_school


def fetch_bachelors_fields(school_id: int) -> list[dict]:
    return fetch_bachelors_fields_for_schools([school_id]).get(school_id, [])


def recommend_majors_at_colleges(llm, student_context: str, language="en") -> None:
    raw_targets = ask(
        "目标大学（请使用英文官方名称或常用英文缩写，用逗号分隔）"
        if language == "zh" else "Target colleges, comma-separated"
    )
    if not raw_targets:
        print("\nNo target colleges entered.")
        return
    resolved, _ = resolve_target_names(raw_targets, "")
    if not resolved:
        print("\nNo target colleges could be resolved.")
        return
    catalog = load_school_catalog()
    records = []
    matched_schools = []
    for target in resolved:
        if normalize_school_name(target) in UC_SYSTEM_ALIASES:
            matches = [
                school for school in catalog
                if normalize_school_name(school["school.name"]).startswith("university of california ")
            ]
        else:
            matches = [school for school in catalog if matches_target(school["school.name"], [target])]
        matched_schools.extend(matches)
    unique_schools = {school["id"]: school for school in matched_schools}
    fields_by_school = fetch_bachelors_fields_for_schools(list(unique_schools))
    for school in unique_schools.values():
        records.append(
            {
                "school": school["school.name"],
                "state": school["school.state"],
                "bachelors_fields": fields_by_school.get(school["id"], []),
            }
        )
    prompt = f"""=== DOCUMENTED STUDENT EVIDENCE ===
{student_context}

=== VERIFIED COLLEGE SCORECARD BACHELOR'S FIELDS ===
{json.dumps(records, ensure_ascii=False, indent=2)}

Recommend school-specific fields of study supported by both evidence sets."""
    print("\n" + "=" * 60)
    print("MAJORS AT TARGET COLLEGES")
    print("=" * 60 + "\n")
    stream_response(llm, SCHOOL_MAJOR_SYSTEM_PROMPT + output_language_instruction(language), prompt)


def _number(value: str):
    try:
        return float(value.replace(",", "").strip())
    except (AttributeError, ValueError):
        return None


def collect_college_preferences(language="en") -> dict:
    zh = language == "zh"
    print("\n请输入你已知的信息；可选问题可按 Enter 跳过。" if zh else "\nEnter what you know. Press Enter to skip an optional question.")
    preferences = {
        "sat": _number(ask("SAT 分数（可选）" if zh else "SAT score, optional")),
        "act": _number(ask("ACT 分数（可选）" if zh else "ACT score, optional")),
        "states": ask(
            "偏好的州缩写，用逗号分隔（例如：CA, MI）" if zh else "Preferred state abbreviations, comma-separated (for example: CA, MI)",
            "CA",
        ),
        "max_cost": _number(ask("助学金前的最高年度费用（可选）" if zh else "Maximum annual cost before aid, optional")),
        "size": ask("学校规模：小型、中型、大型或不限" if zh else "Preferred size: small, medium, large, or any", "不限" if zh else "any").lower(),
        "competition": ask(
            "整体竞争程度：低、中、高、均衡或不限" if zh else "Preferred overall competition: low, medium, high, or balanced",
            "均衡" if zh else "balanced",
        ).lower(),
        "major": ask(
            "意向专业或学术领域（请使用英文名称，例如 Computer Science）"
            if zh else "Intended major or academic area",
            "Computer Science",
        ),
        "targets": ask(
            "目标大学或大学系统（请使用英文官方名称或常用英文缩写，例如 UC、UMich；用逗号分隔）"
            if zh else "Target schools/systems, comma-separated (for example: UC, UMich)",
            "No specific target",
        ),
        "other": ask("其他偏好（可选）" if zh else "Other priorities, optional", "无其他偏好" if zh else "No additional preferences"),
    }
    preferences["size"] = {
        "小": "small", "小型": "small", "中": "medium", "中型": "medium",
        "大": "large", "大型": "large", "不限": "any",
    }.get(preferences["size"], preferences["size"])
    preferences["competition"] = {
        "低": "low", "中": "medium", "高": "high", "均衡": "balanced",
        "不限": "balanced",
    }.get(preferences["competition"], preferences["competition"])
    resolved_targets, discovered_states = resolve_target_names(
        preferences["targets"], preferences["states"]
    )
    preferences["targets"] = ", ".join(resolved_targets) or "No specific target"
    entered_states = {
        state.strip().upper()
        for state in preferences["states"].split(",")
        if state.strip()
    }
    preferences["states"] = ", ".join(sorted(entered_states | discovered_states))
    return preferences


def program_field_for(major: str) -> str | None:
    lowered = major.lower()
    return next((field for keyword, field in PROGRAM_FIELDS.items() if keyword in lowered), None)


def normalize_school_name(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def parse_targets(value: str) -> list[str]:
    return [
        normalize_school_name(item)
        for item in value.split(",")
        if normalize_school_name(item)
        and normalize_school_name(item) != "no specific target"
    ]


def matches_target(school_name: str, targets: list[str]) -> bool:
    name = normalize_school_name(school_name)
    for target in targets:
        if target in UC_SYSTEM_ALIASES and name.startswith("university of california "):
            return True
        normalized_target = normalize_school_name(target)
        if normalized_target == name or normalized_target in name:
            return True
    return False


def load_school_catalog() -> list[dict]:
    if CATALOG_PATH.exists():
        with CATALOG_PATH.open(encoding="utf-8") as file:
            return json.load(file)

    api_key = os.getenv("COLLEGE_SCORECARD_API_KEY")
    if not api_key:
        raise RuntimeError("COLLEGE_SCORECARD_API_KEY is missing from .env.")
    params = {
        "api_key": api_key,
        "school.operating": 1,
        "school.degrees_awarded.predominant": 3,
        "fields": "id,school.name,school.city,school.state",
        "per_page": 100,
    }
    catalog = []
    page = 0
    print("Loading the official College Scorecard school catalog...")
    while True:
        params["page"] = page
        try:
            with urlopen(f"{SCORECARD_URL}?{urlencode(params)}", timeout=30) as response:
                payload = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"College Scorecard catalog returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Could not load College Scorecard catalog: {exc}") from exc
        results = payload.get("results", [])
        catalog.extend(results)
        total = payload.get("metadata", {}).get("total", len(catalog))
        if not results or len(catalog) >= total:
            break
        page += 1
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8") as file:
        json.dump(catalog, file, ensure_ascii=False)
    return catalog


def school_name_variants(name: str) -> set[str]:
    normalized = normalize_school_name(name)
    tokens = normalized.split()
    ignored = {"of", "the", "and", "at", "in", "main", "campus"}
    meaningful = [token for token in tokens if token not in ignored]
    variants = {normalized, "".join(tokens), "".join(meaningful)}
    if meaningful:
        variants.add("".join(token[0] for token in meaningful))
    if len(tokens) >= 3 and tokens[0] == "university" and tokens[1] == "of":
        variants.add("u" + "".join(tokens[2:]))
    if "university" in tokens and tokens[0] != "university":
        variants.add(tokens[0][:4] + "u")
    if len(meaningful) >= 2:
        variants.add(meaningful[0][:3] + meaningful[-1][:4])
    return {variant for variant in variants if variant}


def candidate_score(query: str, school: dict, preferred_states: set[str]) -> float:
    normalized_query = normalize_school_name(query)
    compact_query = normalized_query.replace(" ", "")
    variants = school_name_variants(school.get("school.name", ""))
    score = max(
        SequenceMatcher(None, compact_query, variant.replace(" ", "")).ratio()
        for variant in variants
    )
    compact_variants = {variant.replace(" ", "") for variant in variants}
    if compact_query in compact_variants:
        score = max(score, 1.5)
    elif len(compact_query) >= 3 and any(
        variant.startswith(compact_query) for variant in compact_variants
    ):
        score = max(score, 1.15)
    if school.get("school.state") in preferred_states:
        score += 0.12
    return score


def search_school_candidates(query: str, preferred_states: set[str]) -> list[dict]:
    candidates = []
    for school in load_school_catalog():
        candidate = dict(school)
        candidate["_match_score"] = candidate_score(query, candidate, preferred_states)
        candidates.append(candidate)
    return sorted(candidates, key=lambda school: school["_match_score"], reverse=True)


def resolve_target_names(value: str, states_value: str) -> tuple[list[str], set[str]]:
    preferred_states = {
        state.strip().upper() for state in states_value.split(",") if state.strip()
    }
    resolved = []
    discovered_states = set()
    for raw_target in (item.strip() for item in value.split(",") if item.strip()):
        normalized = normalize_school_name(raw_target)
        if normalized == "no specific target":
            continue
        if normalized in UC_SYSTEM_ALIASES:
            resolved.append("UC")
            discovered_states.add("CA")
            continue
        candidates = search_school_candidates(raw_target, preferred_states)
        if not candidates or candidates[0]["_match_score"] < 0.55:
            print(f"\nNo College Scorecard school matched: {raw_target}")
            continue

        top = candidates[0]
        second_score = candidates[1]["_match_score"] if len(candidates) > 1 else -1
        if top["_match_score"] >= 1.4 or (
            top["_match_score"] >= 1.05 and top["_match_score"] - second_score >= 0.2
        ):
            resolved.append(top["school.name"])
            discovered_states.add(top["school.state"])
            print(f"Matched '{raw_target}' to {top['school.name']} ({top['school.state']}).")
            continue

        choices = candidates[:5]
        print(f"\nMultiple schools may match '{raw_target}':")
        for index, school in enumerate(choices, start=1):
            print(
                f"{index}. {school['school.name']} - "
                f"{school.get('school.city', 'Unknown city')}, {school['school.state']}"
            )
        print("0. None of these")
        choice = ask("Choose the intended school by number")
        if choice.isdigit() and 1 <= int(choice) <= len(choices):
            selected = choices[int(choice) - 1]
            resolved.append(selected["school.name"])
            discovered_states.add(selected["school.state"])
        else:
            print(f"'{raw_target}' was not added.")
    return resolved, discovered_states


def unmatched_targets(colleges: Iterable[dict], value: str) -> list[str]:
    names = [college.get("school.name", "") for college in colleges]
    return [target for target in parse_targets(value) if not any(matches_target(name, [target]) for name in names)]


def fetch_colleges(preferences: dict) -> list[dict]:
    api_key = os.getenv("COLLEGE_SCORECARD_API_KEY")
    if not api_key:
        raise RuntimeError(
            "COLLEGE_SCORECARD_API_KEY is missing from .env. Get a free key at "
            "https://api.data.gov/signup/ and add COLLEGE_SCORECARD_API_KEY=..."
        )

    fields = [
        "id",
        "school.name",
        "school.city",
        "school.state",
        "school.school_url",
        "latest.admissions.admission_rate.overall",
        "latest.admissions.sat_scores.average.overall",
        "latest.admissions.act_scores.midpoint.cumulative",
        "latest.student.size",
        "latest.cost.attendance.academic_year",
        "latest.cost.avg_net_price.overall",
        "latest.completion.rate_suppressed.overall",
    ]
    program_field = program_field_for(preferences["major"])
    if program_field:
        fields.append(program_field)
    params = {
        "api_key": api_key,
        "school.operating": 1,
        "school.degrees_awarded.predominant": 3,
        "fields": ",".join(fields),
        "per_page": 100,
    }
    states = [s.strip().upper() for s in preferences["states"].split(",") if s.strip()]
    states = sorted(set(states))
    if states:
        params["school.state"] = ",".join(states)

    colleges = []
    page = 0
    while True:
        params["page"] = page
        try:
            with urlopen(f"{SCORECARD_URL}?{urlencode(params)}", timeout=30) as response:
                payload = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"College Scorecard returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Could not reach College Scorecard: {exc}") from exc

        results = payload.get("results", [])
        colleges.extend(results)
        total = payload.get("metadata", {}).get("total", len(colleges))
        if not results or len(colleges) >= total:
            break
        page += 1

    return colleges


def _size_fit(student_size, preference: str) -> float:
    if preference == "any" or student_size is None:
        return 0.0
    ranges = {"small": (0, 5000), "medium": (5000, 15000), "large": (15000, float("inf"))}
    low, high = ranges.get(preference, (0, float("inf")))
    return 1.0 if low <= student_size < high else -0.5


def _competition_fit(admission_rate, preference: str) -> float:
    if preference == "balanced" or admission_rate is None:
        return 0.0
    if preference == "high":
        return 1.0 if admission_rate < 0.25 else -0.5
    if preference == "medium":
        return 1.0 if 0.25 <= admission_rate < 0.60 else -0.5
    if preference == "low":
        return 1.0 if admission_rate >= 0.60 else -0.5
    return 0.0


def program_match_score(query: str, program: dict) -> float:
    normalized_query = normalize_school_name(query)
    title = normalize_school_name(program.get("title", ""))
    if not normalized_query or not title:
        return 0.0
    if normalized_query in title:
        return 1.0
    return SequenceMatcher(None, normalized_query, title).ratio()


def matching_programs(query: str, programs: list[dict], limit: int = 5) -> list[dict]:
    scored = sorted(
        ((program_match_score(query, program), program) for program in programs),
        key=lambda item: item[0],
        reverse=True,
    )
    return [
        {**program, "match_score": round(score, 3)}
        for score, program in scored[:limit]
        if score >= 0.45
    ]


def rank_colleges(colleges: Iterable[dict], preferences: dict) -> list[dict]:
    ranked = []
    program_field = program_field_for(preferences["major"])
    targets_requested = parse_targets(preferences.get("targets", ""))
    for college in colleges:
        cost = college.get("latest.cost.attendance.academic_year")
        program_share = college.get(program_field, 0) or 0 if program_field else 0
        score = program_share * 20 + _size_fit(college.get("latest.student.size"), preferences["size"])
        if preferences["max_cost"] is not None and cost is not None:
            score += 1 if cost <= preferences["max_cost"] else -1
        admission_rate = college.get("latest.admissions.admission_rate.overall")
        if admission_rate is not None:
            score += _competition_fit(admission_rate, preferences["competition"])
        name = college.get("school.name", "").lower()
        is_target = matches_target(name, targets_requested)
        if is_target:
            score += 5
        ranked.append((is_target, score, college))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

    # Keep every matching target in the model context, then fill the remaining
    # candidate slots with the strongest alternatives.
    targets = [college for is_target, _, college in ranked if is_target]
    alternatives = [college for is_target, _, college in ranked if not is_target]
    return (targets + alternatives)[:30]


def recommend_colleges(llm, student_context: str, language="en") -> None:
    preferences = collect_college_preferences(language)
    colleges = fetch_colleges(preferences)
    candidates = rank_colleges(colleges, preferences)
    if not candidates:
        print("\nNo colleges matched those filters. Try adding more states or fewer constraints.")
        return
    verified_candidates = []
    fields_by_school = fetch_bachelors_fields_for_schools(
        [college["id"] for college in candidates]
    )
    for college in candidates:
        programs = fields_by_school.get(college["id"], [])
        matches = matching_programs(preferences["major"], programs)
        if matches:
            verified_candidates.append({**college, "matching_bachelors_fields": matches})
    if not verified_candidates:
        print(
            "\nNo candidate college had a sufficiently similar reported bachelor's "
            "field. Try a broader major term."
        )
        return

    prompt = f"""=== DOCUMENTED STUDENT EVIDENCE ===
{student_context}

=== STUDENT INPUT ===
{json.dumps(preferences, ensure_ascii=False, indent=2)}

=== COLLEGE SCORECARD CANDIDATES ===
{json.dumps(verified_candidates, ensure_ascii=False, indent=2)}

Select 9-12 useful options when the data supports that many. Explain that the
Scorecard cost is not necessarily the student's net price. Do not derive an
admission probability or Reach, Target, Safety, or Likely label from overall
admission rate. Interpret competition preference only as requested institutional
selectivity."""
    print("\n" + "=" * 60)
    print("COLLEGE RECOMMENDATIONS")
    print("=" * 60 + "\n")
    print(f"Loaded {len(colleges)} matching four-year colleges from College Scorecard.")
    target = preferences.get("targets", "")
    if target and target.lower() != "no specific target":
        print(f"Target preference retained in candidate selection: {target}")
        missing = unmatched_targets(colleges, target)
        if missing:
            print("Warning: these targets were not matched in College Scorecard:")
            for name in missing:
                print(f"- {name}")
    print()
    stream_response(llm, COLLEGE_SYSTEM_PROMPT + output_language_instruction(language), prompt)


def run_college_major_matching(
    llm, student_context: str, evidence_labels: list[str], language="en"
) -> None:
    path = choose_matching_path(language)
    if path == "college_first":
        recommend_majors_at_colleges(llm, student_context, language)
    elif path == "major_first":
        recommend_colleges(llm, student_context, language)
    elif path == "explore":
        recommend_majors(llm, student_context, evidence_labels, language)
    else:
        print("\n选项无效，请输入 1、2 或 3。" if language == "zh" else "\nInvalid choice. Please enter 1, 2, or 3.")
