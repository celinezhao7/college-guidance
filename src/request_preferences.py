"""Parse explicit recommendation preferences from a free-form user request."""

import re


_ENGLISH_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
}
_CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
}


def requested_recommendation_count(query: str, application_type: str) -> int:
    default, maximum = (4, 8) if application_type == "uc" else (3, 7)
    lowered = query.lower()

    digit_match = re.search(
        r"(?:only|just|need|want|recommend|give me|show me|只要|只想要|想要|需要|推荐|给我|我要)"
        r".{0,24}?(?<!\d)([1-8])(?!\d)"
        r"|(?<!\d)([1-8])(?!\d)\s*(?:piqs?|prompts?|recommendations?|个|道|篇|条)",
        lowered,
        re.IGNORECASE,
    )
    if digit_match:
        requested = int(next(group for group in digit_match.groups() if group))
        return min(requested, maximum)

    english_words = "|".join(_ENGLISH_NUMBERS)
    word_match = re.search(
        rf"(?:only|just|need|want|recommend|give me|show me).{{0,24}}?\b({english_words})\b"
        rf"|\b({english_words})\b\s+(?:is enough|will do|please|piqs?|prompts?|recommendations?)",
        lowered,
        re.IGNORECASE,
    )
    if word_match:
        word = next(group for group in word_match.groups() if group)
        return min(_ENGLISH_NUMBERS[word.lower()], maximum)

    chinese_match = re.search(
        r"(?:只要|只想要|想要|需要|推荐|给我|我要).{0,16}?([一二两三四五六七八])\s*(?:个|道|篇|条)?"
        r"|([一二两三四五六七八])\s*(?:个|道|篇|条)?\s*(?:就够|即可|就行)",
        query,
    )
    if chinese_match:
        word = next(group for group in chinese_match.groups() if group)
        return min(_CHINESE_NUMBERS[word], maximum)

    return default


def explicitly_requested_mode(query: str) -> str | None:
    lowered = query.lower()
    if re.search(r"\bpiqs?\b|personal insight questions?|个人洞察", lowered):
        return "uc"
    if re.search(r"common\s*app|主文书", lowered):
        return "common_app"
    return None
