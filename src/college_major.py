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

CHINESE_FIELD_ALIASES = {
    "计算机": "Computer Science",
    "计算机科学": "Computer Science",
    "数据科学": "Data Science",
    "人工智能": "Artificial Intelligence",
    "软件工程": "Software Engineering",
    "信息科学": "Information Science",
    "电气工程": "Electrical Engineering",
    "电子工程": "Electrical Engineering",
    "机械工程": "Mechanical Engineering",
    "土木工程": "Civil Engineering",
    "化学工程": "Chemical Engineering",
    "生物医学工程": "Biomedical Engineering",
    "生物": "Biology",
    "生物学": "Biology",
    "化学": "Chemistry",
    "物理": "Physics",
    "数学": "Mathematics",
    "心理学": "Psychology",
    "经济学": "Economics",
    "商科": "Business",
    "社会学": "Sociology",
    "政治学": "Political Science",
    "传媒": "Communication and Media Studies",
    "传播学": "Communication and Media Studies",
    "艺术": "Visual and Performing Arts",
    "设计": "Design and Applied Arts",
}

# College Scorecard exposes the 2021 Carnegie Basic Classification. Code 21 is
# "Baccalaureate Colleges: Arts & Sciences Focus," used here as a transparent
# proxy for a liberal arts college rather than a definitive institutional label.
LIBERAL_ARTS_CARNEGIE_CODES = {21}
UNIVERSITY_CARNEGIE_CODES = {15, 16, 17, 18, 19, 20}

MAJOR_SYSTEM_PROMPT = """You are an undergraduate field-of-study exploration assistant.
Use only the supplied student evidence. Recommend five broad undergraduate fields,
ranked from strongest to weakest fit.

These are exploratory academic directions, not exact university catalog majors.
Never claim that a particular university offers a specific major, concentration,
track, curriculum, or resource.

Evidence rules:
- Cite every supporting experience using its complete first-line label exactly,
  including its number, for example "Experience 2: Computer Science Journey".
- After each experience label, cite 1-3 concrete documented facts as evidence.
- Preserve the source's Evidence Reliability qualification. An intellectual
  interest must not be described as formal research or direct project experience.
- Label a recommendation "Direct fit" only when documented actions support it;
  otherwise label it "Exploration to validate".
- If evidence for a recommendation is weak, say so instead of filling gaps.

For each recommendation provide: field name, fit level, why it fits, supporting
evidence, skills/interests it develops, evidence limitations, and one question
the student should investigate while exploring specific majors within the field.
Do not predict admission or career outcomes, and do not claim experience that is
not documented. End with a short comparison of the top two fields and one concise
next step telling the student to explore exact majors on university websites."""

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
- Use the supplied records to support factual statements, but present them as
  clean user-facing facts. Do not append source-field citations or bracketed
  implementation references. Omit a metric when its value is unavailable.
- Never invent rankings, specific programs, campus qualities, admission policies,
  or requirements.

Create a concise, user-facing report rather than a database audit.
- Recommend exactly the number requested in the user prompt. Never add weak or
  unsupported schools merely to increase the count.
- A school may appear under Target School only if its name matches a target in
  STUDENT INPUT. Never place alternatives in that section.
- If a requested target is absent from the candidates or conflicts with filters,
  explain that clearly in one sentence; do not silently replace it.
- For each school show only: location; plain-language reason for inclusion;
  overall admission rate as a percentage when available; undergraduate size;
  average net price or cost, clearly labeled; and matching reported field.
- Add a school-specific caution only when the supplied data shows a concrete
  missing value or conflict with the user's stated budget, size, location,
  selectivity, target-school, or field preference. Otherwise omit it. Never make
  generic or speculative suggestions about faculty quality, laboratories,
  research depth, internships, course quality, student support, or resources.
- Translate internal preference values (small, low, any, etc.) into natural
  language in the requested output language.
- Never display CIP codes, raw API field names, JSON, null, match_score, internal
  preference keys, candidate counts, bracketed field references, or implementation
  details. In particular, never output text such as [latest.*],
  [matching_bachelors_fields.*], or any similar source-field annotation. Show only
  the human-readable reported field title.
- Avoid repeating disclaimers for every school. End with exactly three short
  shared cautions: Scorecard costs are not the student's actual price; overall
  admission rate is not an individual admission probability; and CIP categories
  are broad federal fields rather than exact catalog major names. Tell the student
  to use the recommended field as a starting point for exploring specific majors
  on official university websites. Do not add cautions about the
  student's background, cultural adjustment, activities, or academic readiness.
- Title the final section "说明" when writing in Chinese and "Notes and
  limitations" when writing in English. Never expose internal field names such as
  matching_bachelors_fields.
- Do not repeat the entire student profile or explain the report-generation process.
End with the localized caution section, not an admission prediction."""

SCHOOL_MAJOR_SYSTEM_PROMPT = """You are a school-specific undergraduate
field-of-study exploration assistant. Use only the documented student evidence and
the supplied College Scorecard four-digit CIP records. These records are broad
federal fields reported at bachelor's credential level (3), not exact catalog
majors and not confirmation of a particular concentration or track.

For each target college, recommend up to five reported fields that fit the student.
Cite the exact human-readable Scorecard field title and exact numbered student
experiences with concrete facts. Do not display CIP codes. Never say the school
offers a specific major; say it reports a related bachelor's field. End with one
concise next step asking the student to explore exact majors within those fields on
the official undergraduate catalog. Never invent a program."""


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
        print("1. 我有目标大学——帮我探索相关专业领域")
        print("2. 我有目标专业领域——帮我选择大学")
        print("3. 大学和专业领域都不确定——推荐探索方向")
        choice = input("\n请输入选项（1、2 或 3）：").strip()
    else:
        print("\nChoose your starting point:\n")
        print("1. I have target colleges - help me explore related fields")
        print("2. I have a target field - help me choose colleges")
        print("3. I am unsure about both - recommend fields to explore")
        choice = input("\nEnter choice (1, 2, or 3): ").strip()
    return {"1": "college_first", "2": "major_first", "3": "explore"}.get(choice)


def recommend_majors(llm, student_context: str, evidence_labels: list[str], language="en") -> None:
    prompt = f"""=== DOCUMENTED STUDENT EVIDENCE ===
{student_context}

Recommend five well-supported undergraduate fields to explore. Include related or
interdisciplinary alternatives where the evidence supports them."""
    print("\n" + "=" * 60)
    print("专业领域探索建议" if language == "zh" else "FIELDS OF STUDY TO EXPLORE")
    print("=" * 60 + "\n")
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
    print("目标大学相关专业领域" if language == "zh" else "FIELDS AT TARGET COLLEGES")
    print("=" * 60 + "\n")
    stream_response(llm, SCHOOL_MAJOR_SYSTEM_PROMPT + output_language_instruction(language), prompt)


def _number(value: str):
    try:
        return float(value.replace(",", "").strip())
    except (AttributeError, ValueError):
        return None


def ask_optional_number(
    prompt: str,
    language="en",
    minimum: float | None = None,
    maximum: float | None = None,
    whole_number: bool = False,
):
    while True:
        raw_value = ask(prompt)
        if not raw_value:
            return None
        value = _number(raw_value)
        valid = value is not None
        if valid and whole_number:
            valid = value.is_integer()
        if valid and minimum is not None:
            valid = value >= minimum
        if valid and maximum is not None:
            valid = value <= maximum
        if valid:
            return int(value) if whole_number else value

        if minimum is not None and maximum is not None:
            message = (
                f"请输入 {minimum:g} 到 {maximum:g} 之间的数字，或按 Enter 跳过。"
                if language == "zh"
                else f"Enter a number from {minimum:g} to {maximum:g}, or press Enter to skip."
            )
        elif minimum is not None:
            message = (
                f"请输入不小于 {minimum:g} 的数字，或按 Enter 跳过。"
                if language == "zh"
                else f"Enter a number of at least {minimum:g}, or press Enter to skip."
            )
        else:
            message = (
                "请输入有效数字，或按 Enter 跳过。"
                if language == "zh"
                else "Enter a valid number, or press Enter to skip."
            )
        print(message)


def ask_school_size(language="en") -> list[str]:
    if language == "zh":
        print("\n学校规模：")
        print("1. 小型")
        print("2. 中型")
        print("3. 大型")
        prompt = "请输入选项（可多选，用逗号分隔；不限请按 Enter）"
    else:
        print("\nSchool size:")
        print("1. Small")
        print("2. Medium")
        print("3. Large")
        prompt = "Enter one or more choices separated by commas; press Enter for any size"
    choices = {"1": "small", "2": "medium", "3": "large"}
    while True:
        value = ask(prompt)
        if not value:
            return ["any"]
        selected = [item for item in re.split(r"[,，\s]+", value) if item]
        if selected and all(item in choices for item in selected):
            return [choices[item] for item in choices if item in selected]
        print(
            "请输入 1、2 或 3；多选时请用逗号分隔。"
            if language == "zh"
            else "Please use 1, 2, or 3, separating multiple choices with commas."
        )


def ask_school_ownership(language="en") -> list[str]:
    if language == "zh":
        print("\n学校性质：")
        print("1. 公立")
        print("2. 私立非营利")
        print("3. 私立营利")
        prompt = "请输入选项（可多选，用逗号分隔；不限请按 Enter）"
    else:
        print("\nSchool type:")
        print("1. Public")
        print("2. Private nonprofit")
        print("3. Private for-profit")
        prompt = "Enter one or more choices separated by commas; press Enter for any"
    choices = {
        "1": "public",
        "2": "private_nonprofit",
        "3": "private_for_profit",
    }
    while True:
        value = ask(prompt)
        if not value:
            return ["any"]
        selected = [item for item in re.split(r"[,，\s]+", value) if item]
        if selected and all(item in choices for item in selected):
            return [choices[item] for item in choices if item in selected]
        print(
            "请输入 1、2 或 3；多选时请用逗号分隔。"
            if language == "zh"
            else "Please use 1, 2, or 3, separating multiple choices with commas."
        )


def ask_selectivity(language="en") -> list[str]:
    if language == "zh":
        print("\n学校竞争程度偏好（按学校整体录取率衡量，不代表个人录取概率）：")
        print("1. 竞争较低（整体录取率 60% 或以上）")
        print("2. 竞争中等（整体录取率至少 25% 且低于 60%）")
        print("3. 竞争较高（整体录取率低于 25%）")
        prompt = "请输入选项（可多选，用逗号分隔；不限请按 Enter）"
    else:
        print("\nSchool competition preference (based on overall admission rate, not your personal admission probability):")
        print("1. Lower competition (overall admission rate of 60% or more)")
        print("2. Medium competition (overall admission rate at least 25% and below 60%)")
        print("3. Higher competition (overall admission rate below 25%)")
        prompt = "Enter one or more choices separated by commas; press Enter for any"
    choices = {"1": "low", "2": "medium", "3": "high"}
    while True:
        value = ask(prompt)
        if not value:
            return ["any"]
        selected = [item for item in re.split(r"[,，\s]+", value) if item]
        if selected and all(item in choices for item in selected):
            return [choices[item] for item in choices if item in selected]
        print(
            "请输入 1、2 或 3；多选时请用逗号分隔。"
            if language == "zh"
            else "Please use 1, 2, or 3, separating multiple choices with commas."
        )


def ask_institution_format(language="en") -> list[str]:
    if language == "zh":
        print("\n学校类型偏好：")
        print("1. 文理学院")
        print("2. 综合性大学")
        prompt = "请输入选项（可多选，用逗号分隔；均可请按 Enter）"
    else:
        print("\nInstitution format preference:")
        print("1. Liberal arts college")
        print("2. University")
        prompt = "Enter one or more choices separated by commas; press Enter for either"
    choices = {"1": "liberal_arts", "2": "university"}
    while True:
        value = ask(prompt)
        if not value:
            return ["either"]
        selected = [item for item in re.split(r"[,，\s]+", value) if item]
        if selected and all(item in choices for item in selected):
            return [choices[item] for item in choices if item in selected]
        print(
            "请输入 1 或 2；多选时请用逗号分隔。"
            if language == "zh"
            else "Please use 1 or 2, separating multiple choices with commas."
        )


def collect_college_preferences(language="en") -> dict:
    zh = language == "zh"
    print("\n请输入你已知的信息；可选问题可按 Enter 跳过。" if zh else "\nEnter what you know. Press Enter to skip an optional question.")
    preferences = {
        "sat": ask_optional_number(
            "SAT 分数（可选）" if zh else "SAT score, optional",
            language,
            minimum=400,
            maximum=1600,
            whole_number=True,
        ),
        "act": ask_optional_number(
            "ACT 分数（可选）" if zh else "ACT score, optional",
            language,
            minimum=1,
            maximum=36,
            whole_number=True,
        ),
        "states": ask(
            "偏好的州缩写，用逗号分隔（例如：CA, MI）" if zh else "Preferred state abbreviations, comma-separated (for example: CA, MI)",
            "CA",
        ),
        "max_cost": ask_optional_number(
            "助学金前的最高年度费用（可选）"
            if zh
            else "Maximum annual cost before aid, optional",
            language,
            minimum=1,
        ),
        "size": ask_school_size(language),
        "ownership": ask_school_ownership(language),
        "institution_format": ask_institution_format(language),
        "competition": ask_selectivity(language),
        "field": ask(
            "意向专业领域（可输入中文或英文，例如：计算机科学 / Computer Science）"
            if zh else "Intended field of study (Chinese or English)",
            "Computer Science",
        ),
        "targets": ask(
            "目标大学或大学系统（请使用英文官方名称或常用英文缩写，例如 UC、UMich；用逗号分隔）"
            if zh else "Target schools/systems, comma-separated (for example: UC, UMich)",
            "No specific target",
        ),
    }
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


def resolve_field_query(llm, field_query: str, language="en") -> str:
    """Translate a Chinese field query to a confirmed English search term."""
    current = field_query.strip()
    while re.search(r"[\u3400-\u9fff]", current):
        translated = CHINESE_FIELD_ALIASES.get(current)
        if not translated:
            try:
                response = llm.invoke(
                    [
                        (
                            "system",
                            "Translate the user's Chinese academic field into one concise, standard English field-of-study name suitable for matching U.S. federal CIP field titles. Return only the English name, with no explanation, quotation marks, list, or punctuation at the end.",
                        ),
                        ("user", current),
                    ]
                )
                translated = str(response.content).strip().strip('"\'').rstrip(".")
            except Exception as exc:
                if os.getenv("COLLEGE_GUIDANCE_DEBUG", "").lower() == "true":
                    print(f"Field translation failed: {exc}")
                translated = ""

        if not translated or re.search(r"[\u3400-\u9fff]", translated):
            current = ask(
                "暂时无法可靠翻译该领域，请输入英文名称"
                if language == "zh"
                else "The field could not be translated reliably; please enter its English name"
            )
            continue

        print(
            f"已识别为：{translated}"
            if language == "zh"
            else f"Recognized field: {translated}"
        )
        correction = ask(
            "按 Enter 确认，或输入修改后的名称"
            if language == "zh"
            else "Press Enter to confirm, or enter a corrected field name"
        )
        current = correction or translated
    return current


def reconcile_known_target_conflicts(preferences: dict, language="en") -> bool:
    """Offer a clear resolution for known system-wide target conflicts."""
    targets = parse_targets(preferences.get("targets", ""))
    if not any(target in UC_SYSTEM_ALIASES for target in targets):
        return True

    conflicts = []
    if "any" not in preferences["ownership"] and "public" not in preferences["ownership"]:
        conflicts.append("ownership")
    if (
        "either" not in preferences["institution_format"]
        and "university" not in preferences["institution_format"]
    ):
        conflicts.append("institution_format")
    if not conflicts:
        return True

    if language == "zh":
        print("\n目标大学系统 UC 与当前筛选条件冲突：")
        if "ownership" in conflicts:
            print("- UC 属于公立大学系统，但学校性质未选择“公立”。")
        if "institution_format" in conflicts:
            print("- UC 校区属于综合性大学，但学校类型未选择“综合性大学”。")
        prompt = "输入 1 自动加入所需类别，输入 2 保留条件并排除 UC，输入 0 重新填写条件"
    else:
        print("\nThe UC target conflicts with the current filters:")
        if "ownership" in conflicts:
            print('- UC is a public university system, but "Public" was not selected.')
        if "institution_format" in conflicts:
            print('- UC campuses are universities, but "University" was not selected.')
        prompt = "Enter 1 to add the required categories, 2 to keep the filters and exclude UC, or 0 to re-enter the filters"

    while True:
        choice = ask(prompt)
        if choice == "1":
            if "ownership" in conflicts:
                preferences["ownership"].append("public")
            if "institution_format" in conflicts:
                preferences["institution_format"].append("university")
            return True
        if choice == "2":
            return True
        if choice == "0":
            return False
        print("请输入 1、2 或 0。" if language == "zh" else "Please enter 1, 2, or 0.")


def program_field_for(field_name: str) -> str | None:
    lowered = field_name.lower()
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
        "school.ownership",
        "school.carnegie_basic",
        "latest.admissions.admission_rate.overall",
        "latest.admissions.sat_scores.average.overall",
        "latest.admissions.act_scores.midpoint.cumulative",
        "latest.student.size",
        "latest.cost.attendance.academic_year",
        "latest.cost.avg_net_price.overall",
        "latest.completion.rate_suppressed.overall",
    ]
    program_field = program_field_for(preferences["field"])
    if program_field:
        fields.append(program_field)
    params = {
        "api_key": api_key,
        "school.operating": 1,
        "school.degrees_awarded.predominant": 3,
        "fields": ",".join(fields),
        "per_page": 100,
    }
    ownership = preferences.get("ownership")
    if "any" not in ownership:
        ownership_codes = {
            "public": "1",
            "private_nonprofit": "2",
            "private_for_profit": "3",
        }
        params["school.ownership"] = ",".join(
            ownership_codes[item] for item in ownership
        )
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


def filter_by_institution_format(
    colleges: Iterable[dict], preferences: list[str]
) -> list[dict]:
    colleges = list(colleges)
    if "either" in preferences:
        return colleges
    accepted_codes = set()
    if "liberal_arts" in preferences:
        accepted_codes.update(LIBERAL_ARTS_CARNEGIE_CODES)
    if "university" in preferences:
        accepted_codes.update(UNIVERSITY_CARNEGIE_CODES)
    return [
        college for college in colleges
        if college.get("school.carnegie_basic") in accepted_codes
    ]


def filter_by_selectivity(
    colleges: Iterable[dict], preferences: list[str]
) -> list[dict]:
    """Apply the user's admission-rate category as a strict data filter."""
    colleges = list(colleges)
    if "any" in preferences:
        return colleges

    def matches(college: dict) -> bool:
        admission_rate = college.get("latest.admissions.admission_rate.overall")
        if admission_rate is None:
            return False
        return any(
            (preference == "high" and admission_rate < 0.25)
            or (preference == "medium" and 0.25 <= admission_rate < 0.60)
            or (preference == "low" and admission_rate >= 0.60)
            for preference in preferences
        )

    return [college for college in colleges if matches(college)]


def filter_by_size(
    colleges: Iterable[dict], preferences: list[str]
) -> list[dict]:
    """Keep schools whose reported undergraduate size matches any selected size."""
    colleges = list(colleges)
    if "any" in preferences:
        return colleges
    ranges = {
        "small": (0, 5000),
        "medium": (5000, 15000),
        "large": (15000, float("inf")),
    }
    selected_ranges = [ranges[preference] for preference in preferences]
    return [
        college
        for college in colleges
        if college.get("latest.student.size") is not None
        and any(
            low <= college["latest.student.size"] < high
            for low, high in selected_ranges
        )
    ]


def filter_by_max_cost(
    colleges: Iterable[dict], maximum_cost: float | None
) -> list[dict]:
    """Treat the user's stated pre-aid maximum as a strict attendance-cost cap."""
    colleges = list(colleges)
    if maximum_cost is None:
        return colleges
    return [
        college
        for college in colleges
        if college.get("latest.cost.attendance.academic_year") is not None
        and college["latest.cost.attendance.academic_year"] <= maximum_cost
    ]


def _size_fit(student_size, preferences: list[str]) -> float:
    if "any" in preferences or student_size is None:
        return 0.0
    ranges = {"small": (0, 5000), "medium": (5000, 15000), "large": (15000, float("inf"))}
    matches_preference = any(
        low <= student_size < high
        for preference in preferences
        for low, high in [ranges[preference]]
    )
    return 1.0 if matches_preference else -0.5


def _competition_fit(admission_rate, preferences: list[str]) -> float:
    if "any" in preferences or admission_rate is None:
        return 0.0
    matches_preference = any(
        (preference == "high" and admission_rate < 0.25)
        or (preference == "medium" and 0.25 <= admission_rate < 0.60)
        or (preference == "low" and admission_rate >= 0.60)
        for preference in preferences
    )
    return 1.0 if matches_preference else -0.5


def program_match_score(query: str, program: dict) -> float:
    normalized_query = normalize_school_name(query)
    title = normalize_school_name(program.get("title", ""))
    if not normalized_query or not title:
        return 0.0
    if normalized_query in title:
        return 1.0
    query_tokens = set(normalized_query.split())
    title_tokens = set(title.split())
    generic_terms = {
        "and", "general", "other", "related", "studies", "study",
        "science", "sciences", "engineering",
    }
    distinctive_tokens = query_tokens - generic_terms
    if distinctive_tokens and not distinctive_tokens.issubset(title_tokens):
        return 0.0
    token_coverage = len(query_tokens & title_tokens) / len(query_tokens)
    fuzzy_similarity = SequenceMatcher(None, normalized_query, title).ratio()
    return max(token_coverage, fuzzy_similarity)


def matching_programs(query: str, programs: list[dict], limit: int = 5) -> list[dict]:
    scored = sorted(
        ((program_match_score(query, program), program) for program in programs),
        key=lambda item: item[0],
        reverse=True,
    )
    return [
        {**program, "match_score": round(score, 3)}
        for score, program in scored[:limit]
        if score >= 0.65
    ]


def rank_colleges(
    colleges: Iterable[dict], preferences: dict, candidate_limit: int = 30
) -> list[dict]:
    ranked = []
    program_field = program_field_for(preferences["field"])
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
    return (targets + alternatives)[:candidate_limit]


def ask_recommendation_count(language="en") -> int:
    """Ask for a useful report size while preventing excessively large prompts."""
    prompt = (
        "希望推荐几所大学（1–20）"
        if language == "zh"
        else "How many colleges would you like recommended (1-20)"
    )
    while True:
        value = ask(prompt)
        if value.isdigit() and 1 <= int(value) <= 20:
            return int(value)
        print(
            "请输入 1 到 20 之间的整数。"
            if language == "zh"
            else "Please enter a whole number from 1 to 20."
        )


def print_no_matching_colleges(language="en") -> None:
    print(
        "\n当前条件下没有找到同时符合筛选条件和专业领域要求的大学，请调整条件后重试。"
        if language == "zh"
        else "\nNo colleges matched both the selected filters and field-of-study requirement. Please adjust the conditions and try again."
    )


def confirm_available_count(requested: int, available: int, language="en") -> int | None:
    """Negotiate a smaller report instead of silently padding weak matches."""
    if available >= requested:
        return requested
    if available == 0:
        print_no_matching_colleges(language)
        return 0

    print(
        f"\n当前条件下只能找到 {available} 所有充分数据支持的学校，少于你希望的 {requested} 所。"
        if language == "zh"
        else f"\nOnly {available} well-supported schools were found under the current conditions, fewer than the {requested} requested."
    )
    prompt = (
        f"输入 1 接受推荐这 {available} 所，输入 0 返回并调整条件"
        if language == "zh"
        else f"Enter 1 to continue with {available} schools, or 0 to return and adjust the conditions"
    )
    while True:
        choice = ask(prompt)
        if choice == "1":
            return available
        if choice == "0":
            return 0
        print("请输入 1 或 0。" if language == "zh" else "Please enter 1 or 0.")


def recommend_colleges(llm, student_context: str, language="en") -> None:
    while True:
        preferences = collect_college_preferences(language)
        preferences["field"] = resolve_field_query(
            llm, preferences["field"], language
        )
        if not reconcile_known_target_conflicts(preferences, language):
            continue
        requested_count = ask_recommendation_count(language)
        colleges = fetch_colleges(preferences)
        colleges = filter_by_institution_format(
            colleges, preferences["institution_format"]
        )
        colleges = filter_by_size(colleges, preferences["size"])
        colleges = filter_by_selectivity(colleges, preferences["competition"])
        colleges = filter_by_max_cost(colleges, preferences["max_cost"])
        candidate_limit = min(60, max(30, requested_count * 3))
        candidates = rank_colleges(colleges, preferences, candidate_limit)
        if not candidates:
            print_no_matching_colleges(language)
            continue
        verified_candidates = []
        fields_by_school = fetch_bachelors_fields_for_schools(
            [college["id"] for college in candidates]
        )
        for college in candidates:
            programs = fields_by_school.get(college["id"], [])
            matches = matching_programs(preferences["field"], programs)
            if matches:
                verified_candidates.append(
                    {**college, "matching_bachelors_fields": matches}
                )
        final_count = confirm_available_count(
            requested_count, len(verified_candidates), language
        )
        if final_count is None:
            return
        if final_count == 0:
            continue
        verified_candidates = verified_candidates[:final_count]
        break

    prompt = f"""=== DOCUMENTED STUDENT EVIDENCE ===
{student_context}

=== STUDENT INPUT ===
{json.dumps(preferences, ensure_ascii=False, indent=2)}

=== COLLEGE SCORECARD CANDIDATES ===
{json.dumps(verified_candidates, ensure_ascii=False, indent=2)}

Recommend exactly {final_count} schools. Explain that the
Scorecard cost is not necessarily the student's net price. Do not derive an
admission probability or Reach, Target, Safety, or Likely label from overall
admission rate. Interpret competition preference only as requested institutional
selectivity. The requested target is {preferences.get("targets", "")!r}. Only that
school or system may be labeled as a target; all other schools are alternatives."""
    print("\n" + "=" * 60)
    print("大学推荐" if language == "zh" else "COLLEGE RECOMMENDATIONS")
    print("=" * 60 + "\n")
    target = preferences.get("targets", "")
    if target and target.lower() != "no specific target":
        missing = unmatched_targets(verified_candidates, target)
        if missing:
            print(
                "提示：以下目标学校或大学系统已被识别，但当前筛选条件下没有符合要求的校区："
                if language == "zh"
                else "Note: these target schools or systems were recognized, but no qualifying campus remained under the current filters:"
            )
            for name in missing:
                display_name = "UC" if name in UC_SYSTEM_ALIASES else name
                print(f"- {display_name}")
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
