"""In-memory guided conversation state for college recommendations."""

from dataclasses import dataclass, field
import json
import logging
import os
import re
from uuid import uuid4

from src.safety import SafetyAction, SafetyCategory, SafetyResult, validate_input


logger = logging.getLogger(__name__)


MAJOR_FIRST_QUESTIONS = [
    "field",
    "sat",
    "act",
    "states",
    "max_cost",
    "size",
    "ownership",
    "institution_format",
    "competition",
    "targets",
    "count",
]

QUESTION_ORDERS = {
    "college_first": ["targets"],
    "major_first": MAJOR_FIRST_QUESTIONS,
    "explore": [],
}

QUESTIONS = {
    "en": {
        "scenario": "Let’s first choose a direction. Do you already have a target college, a field of study, or are you still exploring both?",
        "field": "What field of study are you interested in?",
        "states": "Which states do you prefer? Use abbreviations such as CA or WA, or say “any.”",
        "max_cost": "What is your maximum annual cost before aid? You can also say “no limit.”",
        "size": "Do you prefer a small, medium, or large school—or any size?",
        "competition": "What overall admission-rate range do you prefer? Choose a minimum and maximum percentage. This is not your personal admission chance.",
        "sat": "What is your SAT score? You can say “skip.” It is context only, not an admission prediction.",
        "act": "What is your ACT score? You can say “skip.” It is context only, not an admission prediction.",
        "ownership": "Do you prefer public, private nonprofit, private for-profit, or any ownership type?",
        "institution_format": "Do you prefer a university, a liberal arts college, or either?",
        "targets": "Do you have any target schools or university systems? You can say “none.”",
        "count": "How many colleges would you like me to recommend (1–20)?",
    },
    "zh": {
        "scenario": "我们先确定一下探索方向：你已经有目标大学、有感兴趣的专业领域，还是两者都还不确定？",
        "field": "你对哪个专业领域感兴趣？",
        "states": "你偏好哪些州？请输入 CA、WA 等缩写，也可以回答“不限”。",
        "max_cost": "你能接受的助学金前最高年度费用是多少？也可以回答“不限”。",
        "size": "你偏好小型、中型还是大型学校？也可以回答“不限”。",
        "competition": "你偏好的学校整体录取率范围是多少？请选择最低和最高百分比。这里不代表个人录取概率。",
        "sat": "你的 SAT 分数是多少？可以回答“跳过”。该分数仅作为背景信息，不用于预测录取。",
        "act": "你的 ACT 分数是多少？可以回答“跳过”。该分数仅作为背景信息，不用于预测录取。",
        "ownership": "你偏好公立、私立非营利、私立营利，还是不限学校性质？",
        "institution_format": "你偏好综合性大学、文理学院，还是两者都可以？",
        "targets": "你有目标大学或大学系统吗？没有可以回答“无”。",
        "count": "你希望推荐几所大学（1–20）？",
    },
}

STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "washington dc": "DC", "washington d.c.": "DC",
}
VALID_STATE_CODES = set(STATE_CODES.values())


@dataclass
class Conversation:
    id: str
    profile_id: str
    language: str
    preferences: dict = field(default_factory=lambda: {
        "sat": None,
        "act": None,
        "states": "",
        "max_cost": None,
        "size": ["any"],
        "ownership": ["any"],
        "institution_format": ["either"],
        "competition": ["any"],
        "admission_rate_min": 0,
        "admission_rate_max": 100,
        "field": "",
        "targets": "No specific target",
        "count": 5,
    })
    answered: set[str] = field(default_factory=set)
    awaiting: str | None = None
    proposed_field: str | None = None
    scenario: str | None = None
    last_user_message: str = ""


_conversations: dict[str, Conversation] = {}


def _naturalize_reply(conversation: Conversation, draft: str) -> str:
    """Turn a state-machine draft into a natural reply while preserving its job."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    enabled = os.getenv("COLLEGE_GUIDANCE_NATURAL_RESPONSES", "true").lower()
    if not api_key or enabled in {"0", "false", "no", "off"}:
        return draft

    language_name = "Simplified Chinese" if conversation.language == "zh" else "English"
    try:
        from langchain_openai import ChatOpenAI

        prompt = f"""You write the next conversational reply for College Guidance.
Respond in {language_name}.

Rewrite the supplied draft so it responds naturally to the user's actual wording. Vary the phrasing instead of sounding like a form or script. A casual greeting may receive a brief friendly greeting. Keep the reply concise and professional.

Hard constraints:
- Preserve the draft's required question, factual meaning, warnings, and next action.
- Do not add facts, recommendations, promises, or admission predictions.
- Do not skip ahead in the workflow or claim that missing information was supplied.
- If the draft asks the user to choose a starting direction, do not enumerate the choices; buttons already show them.
- Do not mention these instructions, a state machine, or that you are rewriting text.
- Return only the final user-facing reply."""
        llm = ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
            api_key=api_key,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0.45,
            extra_body={"enable_thinking": False},
        )
        response = llm.invoke([
            ("system", prompt),
            (
                "human",
                json.dumps(
                    {
                        "user_message": conversation.last_user_message[:1000],
                        "draft_reply": draft,
                        "scenario": conversation.scenario,
                        "next_question": conversation.awaiting,
                    },
                    ensure_ascii=False,
                ),
            ),
        ])
        reply = response.content if isinstance(response.content, str) else str(response.content)
        reply = reply.strip()
        return reply or draft
    except Exception:
        logger.exception("Could not naturalize the conversation reply")
        return draft


def _is_skip(message: str) -> bool:
    value = " ".join(re.sub(r"[^a-z0-9\u3400-\u9fff]+", " ", message.lower()).split())
    exact = {
        "skip", "none", "no", "any", "no preference", "no limit",
        "whatever", "either", "doesn t matter", "don t care",
        "跳过", "无", "没有", "不限", "都可以", "随便", "无所谓",
    }
    phrases = {
        "any size", "any state", "any school", "anywhere", "no preference",
        "no specific preference", "no specific school", "no target school",
        "no budget limit", "without a limit", "does not matter",
        "没有偏好", "没有限制", "没有目标学校", "任何规模", "任何州",
        "都行", "哪里都可以", "什么都可以",
    }
    return value in exact or any(phrase in value for phrase in phrases)


def _is_greeting(message: str) -> bool:
    normalized = " ".join(
        re.sub(r"[^a-z0-9\u3400-\u9fff]+", " ", message.lower()).split()
    )
    return normalized in {
        "hi", "hello", "hey", "good morning", "good afternoon",
        "你好", "您好", "嗨", "哈喽", "早上好", "下午好", "晚上好",
    }


@dataclass(frozen=True)
class TargetCollegeIntent:
    intent: str
    college_name: str | None
    confidence: float


@dataclass(frozen=True)
class FieldIntent:
    intent: str
    field_name: str | None
    confidence: float


def _classify_target_college(message: str) -> TargetCollegeIntent:
    """Classify a free-form target-college answer without treating it as a name."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return TargetCollegeIntent("unclear", None, 0.0)

    prompt = """Classify the student's answer to: 'Which target college or university system would you like to explore?'

Return one JSON object with exactly these fields:
- intent: "target_college", "no_target", or "unclear"
- college_name: the school/system name from the answer, or null
- confidence: a number from 0 to 1

Meaning:
- target_college: the student actually named a college or university system. Extract the name as written by the student; preserve Chinese names for the later translation-and-verification step.
- no_target: the student says they do not know, have not decided, want help choosing, or currently have no target.
- unclear: the answer is unrelated, ambiguous, empty, or cannot safely be interpreted.

Do not invent a school that the student did not name. Examples: "UMich" is target_college with college_name "UMich"; "密歇根大学" is target_college with college_name "密歇根大学"; "you pick for me" is no_target; "maybe" is unclear.
    Return JSON only."""
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
            api_key=api_key,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0,
            extra_body={"enable_thinking": False},
        ).bind(response_format={"type": "json_object"})
        response = llm.invoke([
            ("system", prompt),
            ("human", message[:1000]),
        ])
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        intent = data.get("intent")
        college_name = data.get("college_name")
        confidence = float(data.get("confidence", 0))
        if intent not in {"target_college", "no_target", "unclear"}:
            raise ValueError(f"Unknown target-college intent: {intent}")
        if intent == "target_college" and not isinstance(college_name, str):
            return TargetCollegeIntent("unclear", None, 0.0)
        return TargetCollegeIntent(intent, college_name, max(0.0, min(confidence, 1.0)))
    except Exception:
        logger.exception("Could not classify the target-college answer")
        return TargetCollegeIntent("unclear", None, 0.0)


CHINESE_COLLEGE_ALIASES = {
    "加州大学": "UC",
    "加利福尼亚大学": "UC",
    "加州大学伯克利分校": "University of California, Berkeley",
    "加州大学洛杉矶分校": "University of California, Los Angeles",
    "密歇根大学": "University of Michigan-Ann Arbor",
    "密歇根大学安娜堡分校": "University of Michigan-Ann Arbor",
    "南加州大学": "University of Southern California",
    "纽约大学": "New York University",
    "波士顿大学": "Boston University",
    "东北大学": "Northeastern University",
    "卡内基梅隆大学": "Carnegie Mellon University",
}


def _translate_college_name_to_english(name: str) -> str | None:
    """Translate a Chinese college name for Scorecard lookup without selecting a school."""
    compact = re.sub(r"\s+", "", name)
    if compact in CHINESE_COLLEGE_ALIASES:
        return CHINESE_COLLEGE_ALIASES[compact]
    if not re.search(r"[\u3400-\u9fff]", name):
        return name.strip()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return None
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
            api_key=api_key,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0,
            extra_body={"enable_thinking": False},
        )
        response = llm.invoke([
            (
                "system",
                "Translate the Chinese name of a U.S. college or university system into its most likely official English name. Return only the English name. Do not add explanations and do not invent a different school.",
            ),
            ("human", name[:300]),
        ])
        translated = response.content if isinstance(response.content, str) else str(response.content)
        translated = translated.strip().strip('"\'').rstrip(".")
        if not translated or re.search(r"[\u3400-\u9fff]", translated):
            return None
        return translated
    except Exception:
        logger.exception("Could not translate the Chinese college name")
        return None


def _resolve_scorecard_target(name: str) -> str | None:
    """Translate when needed, then fuzzy-match against the Scorecard catalog."""
    from src.college_major import (
        UC_SYSTEM_ALIASES,
        normalize_school_name,
        search_school_candidates,
    )

    lookup_name = _translate_college_name_to_english(name)
    if not lookup_name:
        return None
    normalized = normalize_school_name(lookup_name)
    if normalized in UC_SYSTEM_ALIASES:
        return "UC"
    campus_aliases = {
        "ucla": "University of California Los Angeles",
        "ucsd": "University of California San Diego",
        "ucsb": "University of California Santa Barbara",
        "uci": "University of California Irvine",
        "ucr": "University of California Riverside",
        "ucsc": "University of California Santa Cruz",
        "ucm": "University of California Merced",
        "cal berkeley": "University of California Berkeley",
        "umich": "University of Michigan Ann Arbor",
    }
    if normalized in campus_aliases:
        lookup_name = campus_aliases[normalized]
    elif normalized.startswith("uc ") and len(normalized.split()) > 1:
        campus = " ".join(normalized.split()[1:])
        lookup_name = f"University of California {campus}"
    candidates = search_school_candidates(lookup_name, set())
    if not candidates:
        return None
    top = candidates[0]
    second_score = candidates[1]["_match_score"] if len(candidates) > 1 else -1
    if top["_match_score"] >= 1.4 or (
        top["_match_score"] >= 1.05
        and top["_match_score"] - second_score >= 0.2
    ):
        return top["school.name"]
    return None


def _number(message: str) -> float | None:
    match = re.search(r"\d[\d,]*(?:\.\d+)?", message)
    if not match:
        words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19, "twenty": 20,
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        }
        normalized = message.strip().lower()
        matched_word = next(
            (
                number for word, number in words.items()
                if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", normalized)
            ),
            None,
        )
        return float(matched_word) if matched_word is not None else None
    value = float(match.group().replace(",", ""))
    if re.search(r"\d\s*[kK]\b|千", message):
        value *= 1000
    return value


def _parse_states(message: str) -> list[str]:
    lowered = message.lower()
    found = [
        code for name, code in STATE_CODES.items()
        if re.search(rf"\b{re.escape(name)}\b", lowered)
    ]
    found.extend(
        code.upper() for code in re.findall(r"\b[A-Za-z]{2}\b", message)
        if code.upper() in VALID_STATE_CODES
    )
    if re.search(r"\bwashington\s+(?:d\.?c\.?|district of columbia)\b", lowered):
        found = [code for code in found if code != "WA"]
        found.append("DC")
    return list(dict.fromkeys(found))


def _parse(answer_for: str, message: str, preferences: dict) -> bool:
    value = message.strip()
    lowered = value.lower()
    if answer_for == "field":
        if not value:
            return False
        preferences["field"] = value
    elif answer_for == "states":
        if _is_skip(value):
            preferences["states"] = ""
        else:
            states = _parse_states(value)
            if not states:
                return False
            preferences["states"] = ", ".join(states)
    elif answer_for == "max_cost":
        if _is_skip(value):
            preferences["max_cost"] = None
        else:
            number = _number(value)
            if number is None or number <= 0:
                return False
            preferences["max_cost"] = number
    elif answer_for == "size":
        mapping = {
            "small": "small", "smaller": "small", "tiny": "small",
            "medium": "medium", "mid size": "medium", "mid-sized": "medium",
            "large": "large", "larger": "large", "big": "large",
            "小": "small", "中": "medium", "大": "large",
        }
        if _is_skip(value):
            preferences["size"] = ["any"]
        else:
            selected = next((result for key, result in mapping.items() if key in lowered), None)
            if not selected:
                return False
            preferences["size"] = [selected]
    elif answer_for == "competition":
        rate_range = re.search(r"(\d{1,3})\s*%?\s*[–—-]\s*(\d{1,3})\s*%?", value)
        mapping = {
            "lower": "low", "low": "low", "less selective": "low",
            "medium": "medium", "moderate": "medium",
            "higher": "high", "high": "high", "selective": "high",
            "competitive": "high", "较低": "low",
            "中等": "medium", "较高": "high",
        }
        if rate_range:
            minimum, maximum = map(int, rate_range.groups())
            if not 0 <= minimum < maximum <= 100:
                return False
            preferences["competition"] = ["range"]
            preferences["admission_rate_min"] = minimum
            preferences["admission_rate_max"] = maximum
        elif _is_skip(value):
            preferences["competition"] = ["any"]
            preferences["admission_rate_min"] = 0
            preferences["admission_rate_max"] = 100
        else:
            selected = next((result for key, result in mapping.items() if key in lowered), None)
            if not selected:
                return False
            preferences["competition"] = [selected]
    elif answer_for == "sat":
        if _is_skip(value):
            preferences["sat"] = None
        else:
            number = _number(value)
            if number is None or not 400 <= number <= 1600:
                return False
            preferences["sat"] = int(number)
    elif answer_for == "act":
        if _is_skip(value):
            preferences["act"] = None
        else:
            number = _number(value)
            if number is None or not 1 <= number <= 36:
                return False
            preferences["act"] = int(number)
    elif answer_for == "ownership":
        mapping = {
            "public": "public", "公立": "public",
            "private nonprofit": "private_nonprofit", "nonprofit": "private_nonprofit", "私立非营利": "private_nonprofit",
            "private for profit": "private_for_profit", "for profit": "private_for_profit", "私立营利": "private_for_profit",
        }
        if _is_skip(value):
            preferences["ownership"] = ["any"]
        else:
            selected = next((result for key, result in mapping.items() if key in lowered), None)
            if not selected:
                return False
            preferences["ownership"] = [selected]
    elif answer_for == "institution_format":
        mapping = {
            "university": "university", "大学": "university", "综合性": "university",
            "liberal arts": "liberal_arts", "文理学院": "liberal_arts",
        }
        if _is_skip(value):
            preferences["institution_format"] = ["either"]
        else:
            selected = next((result for key, result in mapping.items() if key in lowered), None)
            if not selected:
                return False
            preferences["institution_format"] = [selected]
    elif answer_for == "targets":
        preferences["targets"] = (
            "无特定目标" if _is_skip(value) and preferences.get("language") == "zh"
            else "No specific target" if _is_skip(value)
            else value
        )
    elif answer_for == "count":
        number = _number(value)
        if number is None or not 1 <= number <= 20 or not number.is_integer():
            return False
        preferences["count"] = int(number)
    return True


def _next_question(conversation: Conversation) -> str | None:
    if conversation.scenario is None:
        return "scenario"
    order = QUESTION_ORDERS[conversation.scenario]
    return next((key for key in order if key not in conversation.answered), None)


def _parse_scenario(message: str) -> str | None:
    value = message.strip().lower()
    if value == "1" or any(phrase in value for phrase in ("know college", "target college", "有目标大学", "知道大学")):
        return "college_first"
    if value == "2" or any(phrase in value for phrase in ("know major", "know field", "target major", "target field", "有目标专业", "知道专业")):
        return "major_first"
    if value == "3" or any(phrase in value for phrase in ("unsure about both", "don t know either", "don't know either", "都不确定", "都不知道")):
        return "explore"
    return None


def _acknowledgement(language: str) -> str:
    return "Got it. " if language == "en" else "好的。"


def _question(conversation: Conversation, key: str) -> str:
    if key == "targets" and conversation.scenario == "college_first":
        return (
            "Which target college or university system would you like to explore? Please enter its official English name or a common abbreviation such as UC or UMich."
            if conversation.language == "en"
            else "你想探索哪所目标大学或大学系统？可以输入中文或英文校名，也可以使用 UC、UMich 等常用缩写；中文校名会先转换为英文，再与 College Scorecard 核对。"
        )
    return QUESTIONS[conversation.language][key]


def _infer_field(message: str) -> str | None:
    lowered = message.lower()
    fields = {
        "computer science": "Computer Science",
        "data science": "Data Science",
        "engineering": "Engineering",
        "business": "Business",
        "psychology": "Psychology",
        "biology": "Biology",
        "计算机": "计算机科学",
        "数据科学": "数据科学",
        "工程": "工程",
        "商科": "商科",
        "心理": "心理学",
        "生物": "生物学",
    }
    return next((field for term, field in fields.items() if term in lowered), None)


def _classify_field(message: str, language: str) -> FieldIntent:
    """Validate and normalize an academic field instead of accepting arbitrary text."""
    normalized = " ".join(
        re.sub(r"[^a-zA-Z0-9\u3400-\u9fff]+", " ", message.lower()).split()
    )
    exact_aliases = {
        "computer science": "Computer Science",
        "data science": "Data Science",
        "engineering": "Engineering",
        "business": "Business",
        "psychology": "Psychology",
        "biology": "Biology",
        "economics": "Economics",
        "political science": "Political Science",
        "计算机科学": "计算机科学",
        "数据科学": "数据科学",
        "工程": "工程",
        "商科": "商科",
        "心理学": "心理学",
        "生物学": "生物学",
        "经济学": "经济学",
        "政治学": "政治学",
    }
    if normalized in exact_aliases:
        return FieldIntent("valid", exact_aliases[normalized], 1.0)

    correction_aliases = {
        "computer": "Computer Science",
        "cs": "Computer Science",
        "comp sci": "Computer Science",
        "compsci": "Computer Science",
        "diannao": "计算机科学" if language == "zh" else "Computer Science",
        "jisuanji": "计算机科学" if language == "zh" else "Computer Science",
        "计算机": "计算机科学",
    }
    if normalized in correction_aliases:
        return FieldIntent("corrected", correction_aliases[normalized], 1.0)

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return FieldIntent("unclear", None, 0.0)
    try:
        from langchain_openai import ChatOpenAI

        output_language = "Simplified Chinese" if language == "zh" else "English"
        prompt = f"""Determine whether the user's text names an academic field of study.
Return one JSON object with exactly these fields:
- intent: "valid", "corrected", or "unclear"
- field_name: a concise canonical field name in {output_language}, or null
- confidence: a number from 0 to 1

Use "corrected" when you repaired a typo, pinyin, informal shorthand, or translated the input. Use "valid" only when the input already clearly names a field. Use "unclear" for unrelated text, gibberish, or an unsafe guess. Do not invent a field. Return JSON only."""
        llm = ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
            api_key=api_key,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            temperature=0,
            extra_body={"enable_thinking": False},
        ).bind(response_format={"type": "json_object"})
        response = llm.invoke([("system", prompt), ("human", message[:500])])
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        intent = data.get("intent")
        field_name = data.get("field_name")
        confidence = max(0.0, min(float(data.get("confidence", 0)), 1.0))
        if intent not in {"valid", "corrected", "unclear"}:
            raise ValueError(f"Unknown field intent: {intent}")
        if intent != "unclear" and not isinstance(field_name, str):
            return FieldIntent("unclear", None, 0.0)
        return FieldIntent(intent, field_name, confidence)
    except Exception:
        logger.exception("Could not classify the field-of-study answer")
        return FieldIntent("unclear", None, 0.0)


def _ambiguous_field(message: str) -> str | None:
    normalized = " ".join(re.sub(r"[^a-zA-Z0-9\u3400-\u9fff]+", " ", message.lower()).split())
    aliases = {
        "computer": "Computer Science",
        "cs": "Computer Science",
        "comp sci": "Computer Science",
        "compsci": "Computer Science",
        "计算机": "计算机科学",
    }
    direct = aliases.get(normalized)
    if direct:
        return direct
    tokens = set(normalized.split())
    if "computer" in tokens and "science" not in tokens:
        return "Computer Science"
    if ("cs" in tokens or "compsci" in tokens) and "science" not in tokens:
        return "Computer Science"
    if "计算机" in normalized and "科学" not in normalized:
        return "计算机科学"
    return None


def _field_confirmation(language: str, proposed_field: str) -> str:
    return (
        f'Did you mean “{proposed_field}”? Reply yes to confirm, or enter the intended field.'
        if language == "en"
        else f'你是指“{proposed_field}”吗？回复“是”确认，或者直接输入你想选择的专业领域。'
    )


def _is_yes(message: str) -> bool:
    return message.strip().lower() in {"yes", "y", "yeah", "yep", "correct", "是", "对", "正确", "确认"}


def _is_no(message: str) -> bool:
    return message.strip().lower() in {"no", "n", "nope", "不是", "不对"}


CHOICE_VALUES = {
    "scenario_college": "1",
    "scenario_major": "2",
    "scenario_explore": "3",
    "field_yes": "yes",
    "field_no": "no",
    "skip": "skip",
    "any": "any",
    "size_small": "small",
    "size_medium": "medium",
    "size_large": "large",
    "ownership_public": "public",
    "ownership_nonprofit": "private nonprofit",
    "ownership_for_profit": "private for profit",
    "format_university": "university",
    "format_liberal_arts": "liberal arts college",
    "competition_low": "lower",
    "competition_medium": "medium",
    "competition_high": "higher",
    "count_5": "5",
    "count_10": "10",
}


def _quick_replies(conversation: Conversation) -> list[dict[str, str]]:
    key = conversation.awaiting
    language = conversation.language
    labels = {
        "en": {
            "scenario_college": "I have a target college",
            "scenario_major": "I have a target field",
            "scenario_explore": "I’m unsure about both",
            "no_target": "Changed your mind? Explore without a target →",
            "field_yes": "Yes",
            "field_no": "No, I’ll re-enter it",
            "skip": "Skip",
            "any": "Any",
            "size_small": "Small",
            "size_medium": "Medium",
            "size_large": "Large",
            "ownership_public": "Public",
            "ownership_nonprofit": "Private nonprofit",
            "ownership_for_profit": "Private for-profit",
            "format_university": "University",
            "format_liberal_arts": "Liberal arts college",
            "competition_low": "Lower",
            "competition_medium": "Medium",
            "competition_high": "Higher",
            "count_5": "5 schools",
            "count_10": "10 schools",
        },
        "zh": {
            "scenario_college": "有目标大学",
            "scenario_major": "有目标专业",
            "scenario_explore": "两者都不确定",
            "no_target": "还没有，帮我探索",
            "field_yes": "是",
            "field_no": "不是，我重新输入",
            "skip": "跳过",
            "any": "不限",
            "size_small": "小型",
            "size_medium": "中型",
            "size_large": "大型",
            "ownership_public": "公立",
            "ownership_nonprofit": "私立非营利",
            "ownership_for_profit": "私立营利",
            "format_university": "综合性大学",
            "format_liberal_arts": "文理学院",
            "competition_low": "较低",
            "competition_medium": "中等",
            "competition_high": "较高",
            "count_5": "5 所",
            "count_10": "10 所",
        },
    }[language]
    choices_by_question = {
        "scenario": ["scenario_college", "scenario_major", "scenario_explore"],
        "field_confirmation": ["field_yes", "field_no"],
        "sat": ["skip"],
        "act": ["skip"],
        "states": ["any"],
        "max_cost": ["any"],
        "size": ["size_small", "size_medium", "size_large", "any"],
        "ownership": ["ownership_public", "ownership_nonprofit", "ownership_for_profit", "any"],
        "institution_format": ["format_university", "format_liberal_arts", "any"],
        "competition": [],
        "targets": ["no_target"],
        "count": ["count_5", "count_10"],
    }
    return [{"id": choice, "label": labels[choice]} for choice in choices_by_question.get(key or "", [])]


def chat(
    session_id: str | None,
    profile_id: str,
    language: str,
    message: str,
    choice_id: str | None = None,
) -> dict:
    conversation = _conversations.get(session_id or "")
    if conversation is None:
        conversation = Conversation(
            id=uuid4().hex,
            profile_id=profile_id,
            language=language if language in QUESTIONS else "en",
        )
        _conversations[conversation.id] = conversation
    conversation.language = language if language in QUESTIONS else "en"
    conversation.preferences["language"] = conversation.language

    safety = validate_input(message, "chat")
    if not safety.allowed or safety.action is SafetyAction.REDACT:
        if conversation.awaiting is None:
            conversation.awaiting = _next_question(conversation)
        return _response(
            conversation,
            _chat_safety_reply(safety, conversation.language),
            naturalize=False,
        )

    if choice_id:
        message = "none" if choice_id == "no_target" else CHOICE_VALUES.get(choice_id, message)
    conversation.last_user_message = message.strip()

    if conversation.awaiting == "scenario":
        scenario = _parse_scenario(message)
        if scenario is None:
            return _response(
                conversation,
                ("I couldn’t determine the starting point. " if conversation.language == "en" else "我没有判断出你的起点。")
                + QUESTIONS[conversation.language]["scenario"],
            )
        conversation.scenario = scenario
        conversation.answered.add("scenario")
        acknowledgement = _acknowledgement(conversation.language)
    elif conversation.awaiting == "field_confirmation":
        if _is_yes(message):
            conversation.preferences["field"] = conversation.proposed_field
            conversation.answered.add("field")
            conversation.proposed_field = None
            acknowledgement = _acknowledgement(conversation.language)
        elif _is_no(message):
            conversation.proposed_field = None
            conversation.awaiting = "field"
            return _response(conversation, QUESTIONS[conversation.language]["field"])
        elif message.strip():
            conversation.proposed_field = None
            conversation.awaiting = "field"
            return chat(
                conversation.id,
                conversation.profile_id,
                conversation.language,
                message,
            )
        else:
            return _response(
                conversation,
                _field_confirmation(conversation.language, conversation.proposed_field or "Computer Science"),
            )
    elif conversation.awaiting:
        if conversation.awaiting == "targets" and conversation.scenario == "college_first":
            target_intent = (
                TargetCollegeIntent("no_target", None, 1.0)
                if choice_id == "no_target"
                else _classify_target_college(message)
            )
            if target_intent.confidence < 0.75 or target_intent.intent == "unclear":
                reply = (
                    "I’m not sure whether you named a college or meant that you don’t have one yet. Please enter the college’s official English name, or say that you’d like help choosing one."
                    if conversation.language == "en"
                    else "我不确定你是在提供大学名称，还是目前没有目标大学。请输入中文或英文校名，或者告诉我希望由我帮助选择。"
                )
                return _response(conversation, reply)
            if target_intent.intent == "no_target":
                conversation.scenario = "explore"
                conversation.awaiting = None
                reply = (
                    "No problem. Since you don’t have a target college yet, I’ll recommend fields of study to explore based on your documented experiences."
                    if conversation.language == "en"
                    else "没问题。既然你目前没有目标大学，我会根据你记录的经历推荐值得探索的专业领域。"
                )
                return _response(conversation, reply, ready=True)
            try:
                resolved_target = _resolve_scorecard_target(target_intent.college_name or "")
            except Exception:
                logger.exception("Could not validate the target college")
                resolved_target = None
            if not resolved_target:
                reply = (
                    "I understood that as a college, but I couldn’t verify it in College Scorecard. Try its official English name with a campus identifier, or tell me that you’d like help choosing a college."
                    if conversation.language == "en"
                    else "我理解你输入的是一所大学，但无法在 College Scorecard 中可靠确认。请尝试补充分校信息，或换一种中文/英文校名；也可以告诉我希望由我帮助选择大学。"
                )
                return _response(conversation, reply)
            message = resolved_target
        if conversation.awaiting == "field":
            field_intent = _classify_field(message, conversation.language)
            if field_intent.confidence < 0.8 or field_intent.intent == "unclear":
                reply = (
                    "I couldn’t reliably identify an academic field. Please enter a field such as Computer Science, Economics, or Biology."
                    if conversation.language == "en"
                    else "我无法可靠识别这个专业领域。请输入较完整的专业名称，例如“计算机科学”“经济学”或“生物学”。"
                )
                return _response(conversation, reply)
            if field_intent.intent == "corrected":
                conversation.proposed_field = field_intent.field_name
                conversation.awaiting = "field_confirmation"
                return _response(
                    conversation,
                    _field_confirmation(
                        conversation.language,
                        field_intent.field_name or "Computer Science",
                    ),
                )
            message = field_intent.field_name or message
        if not _parse(conversation.awaiting, message, conversation.preferences):
            prefix = "I couldn’t understand that. " if conversation.language == "en" else "我没有理解这个回答。"
            return _response(conversation, prefix + _question(conversation, conversation.awaiting))
        conversation.answered.add(conversation.awaiting)
        acknowledgement = _acknowledgement(conversation.language)
    elif message.strip():
        scenario = _parse_scenario(message)
        if scenario:
            conversation.scenario = scenario
            conversation.answered.add("scenario")
        if _is_greeting(message):
            acknowledgement = "Hi! " if conversation.language == "en" else "你好！"
        else:
            acknowledgement = (
                "I can help with that. " if conversation.language == "en" else "可以，我来帮你。"
            )
    else:
        acknowledgement = ""

    conversation.awaiting = _next_question(conversation)
    if conversation.awaiting:
        return _response(
            conversation,
            acknowledgement + _question(conversation, conversation.awaiting),
        )

    ready_messages = {
        "en": {
            "college_first": "Thanks—I’ll now explore fields of study reported by your target college that fit your documented experiences.",
            "major_first": "Thanks—I have enough information. I’ll generate your college recommendations now.",
            "explore": "Thanks—I’ll recommend fields of study to explore based on your documented experiences.",
        },
        "zh": {
            "college_first": "谢谢。现在根据你的经历，探索目标大学所报告的相关专业领域。",
            "major_first": "谢谢，我已经获得足够的信息。现在为你生成大学推荐。",
            "explore": "谢谢。现在根据你记录的经历，推荐值得探索的专业领域。",
        },
    }
    ready_message = ready_messages[conversation.language][conversation.scenario]
    return _response(conversation, ready_message, ready=True)


def _chat_safety_reply(result: SafetyResult, language: str) -> str:
    if result.category is SafetyCategory.SELF_HARM:
        return (
            "我不能帮助伤害自己的请求。如果你可能立即伤害自己，请马上联系当地紧急服务或身边可信任的人。这个工具只能帮助你探索大学、专业和申请材料。"
            if language == "zh"
            else "I can’t help with requests to harm yourself. If you may act now, contact local emergency services or a trusted person immediately. This tool can only help with colleges, fields of study, and application materials."
        )
    if result.category is SafetyCategory.PII_SECRET:
        return (
            "为了保护隐私，请不要输入身份证件号码、银行卡信息、密码或 API 密钥。请删除这些信息后重新发送。"
            if language == "zh"
            else "For your privacy, don’t enter government ID numbers, payment-card details, passwords, or API keys. Remove that information and try again."
        )
    return (
        "抱歉，我不能处理这条请求。这个工具只能帮助你探索大学、专业和申请材料。"
        if language == "zh"
        else "Sorry, I can’t help with that request. This tool is for exploring colleges, fields of study, and application materials."
    )


def _response(
    conversation: Conversation,
    reply: str,
    ready: bool = False,
    *,
    naturalize: bool = True,
) -> dict:
    preferences = dict(conversation.preferences)
    preferences.pop("language", None)
    return {
        "session_id": conversation.id,
        "reply": _naturalize_reply(conversation, reply) if naturalize else reply,
        "ready": ready,
        "preferences": preferences,
        "answered": [key for key in MAJOR_FIRST_QUESTIONS if key in conversation.answered],
        "scenario": conversation.scenario,
        "quick_replies": [] if ready else _quick_replies(conversation),
        "awaiting": None if ready else conversation.awaiting,
    }
