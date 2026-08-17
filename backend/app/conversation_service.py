"""In-memory guided conversation state for college recommendations."""

from dataclasses import dataclass, field
import re
from uuid import uuid4


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
        "scenario": "Where would you like to start? 1) I know my target college but not the field, 2) I know my field but not the college, or 3) I’m unsure about both.",
        "field": "What field of study are you interested in?",
        "states": "Which states do you prefer? Use abbreviations such as CA or WA, or say “any.”",
        "max_cost": "What is your maximum annual cost before aid? You can also say “no limit.”",
        "size": "Do you prefer a small, medium, or large school—or any size?",
        "competition": "What institutional selectivity do you prefer: lower, medium, higher, or any? This is based on the school’s overall admission rate, not your personal admission chance.",
        "sat": "What is your SAT score? You can say “skip.” It is context only, not an admission prediction.",
        "act": "What is your ACT score? You can say “skip.” It is context only, not an admission prediction.",
        "ownership": "Do you prefer public, private nonprofit, private for-profit, or any ownership type?",
        "institution_format": "Do you prefer a university, a liberal arts college, or either?",
        "targets": "Do you have any target schools or university systems? You can say “none.”",
        "count": "How many colleges would you like me to recommend (1–20)?",
    },
    "zh": {
        "scenario": "你想从哪里开始？1）有目标大学，但不确定专业；2）有目标专业，但不确定大学；3）大学和专业都不确定。",
        "field": "你对哪个专业领域感兴趣？",
        "states": "你偏好哪些州？请输入 CA、WA 等缩写，也可以回答“不限”。",
        "max_cost": "你能接受的助学金前最高年度费用是多少？也可以回答“不限”。",
        "size": "你偏好小型、中型还是大型学校？也可以回答“不限”。",
        "competition": "你偏好的学校竞争程度是较低、中等、较高还是不限？这里依据学校整体录取率，不代表个人录取概率。",
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
        "field": "",
        "targets": "No specific target",
        "count": 5,
    })
    answered: set[str] = field(default_factory=set)
    awaiting: str | None = None
    proposed_field: str | None = None
    scenario: str | None = None


_conversations: dict[str, Conversation] = {}


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
        mapping = {
            "lower": "low", "low": "low", "less selective": "low",
            "medium": "medium", "moderate": "medium",
            "higher": "high", "high": "high", "selective": "high",
            "competitive": "high", "较低": "low",
            "中等": "medium", "较高": "high",
        }
        if _is_skip(value):
            preferences["competition"] = ["any"]
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
            "Which target college or university system would you like to explore? Please use its official English name or a common abbreviation such as UC or UMich."
            if conversation.language == "en"
            else "你想探索哪所目标大学或大学系统？请使用英文官方名称或 UC、UMich 等常用缩写。"
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


def chat(
    session_id: str | None,
    profile_id: str,
    language: str,
    message: str,
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
            conversation.preferences["field"] = message.strip()
            conversation.answered.add("field")
            conversation.proposed_field = None
            acknowledgement = _acknowledgement(conversation.language)
        else:
            return _response(
                conversation,
                _field_confirmation(conversation.language, conversation.proposed_field or "Computer Science"),
            )
    elif conversation.awaiting:
        if (
            conversation.awaiting == "targets"
            and conversation.scenario == "college_first"
            and _is_skip(message)
        ):
            conversation.scenario = "explore"
            conversation.awaiting = None
            reply = (
                "No problem. Since you don’t have a target college yet, I’ll recommend fields of study to explore based on your documented experiences."
                if conversation.language == "en"
                else "没问题。既然你目前没有目标大学，我会根据你记录的经历推荐值得探索的专业领域。"
            )
            return _response(conversation, reply, ready=True)
        if conversation.awaiting == "field":
            proposed_field = _ambiguous_field(message)
            if proposed_field:
                conversation.proposed_field = proposed_field
                conversation.awaiting = "field_confirmation"
                return _response(
                    conversation,
                    _field_confirmation(conversation.language, proposed_field),
                )
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


def _response(conversation: Conversation, reply: str, ready: bool = False) -> dict:
    preferences = dict(conversation.preferences)
    preferences.pop("language", None)
    return {
        "session_id": conversation.id,
        "reply": reply,
        "ready": ready,
        "preferences": preferences,
        "answered": [key for key in MAJOR_FIRST_QUESTIONS if key in conversation.answered],
        "scenario": conversation.scenario,
    }
