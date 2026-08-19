"""Deterministic grounding checks for references in generated answers."""

import re


_EXPERIENCE_LINE = re.compile(
    r"^\s*(Experience\s+\d+\s*:\s*[^\r\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_EXPERIENCE_NUMBER = re.compile(r"\bExperience\s+(\d+)\s*:", re.IGNORECASE)


def extract_experience_labels(reference_text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(1).strip() for match in _EXPERIENCE_LINE.finditer(reference_text)))


def find_ungrounded_experience_references(
    generated_text: str,
    reference_text: str,
) -> tuple[str, ...]:
    """Return referenced experience numbers that do not exist in the evidence."""
    allowed_labels = extract_experience_labels(reference_text)
    if not allowed_labels:
        return ()

    issues = []
    for match in _EXPERIENCE_NUMBER.finditer(generated_text):
        number = match.group(1)
        matching_labels = [
            label
            for label in allowed_labels
            if re.match(rf"Experience\s+{re.escape(number)}\s*:", label, re.IGNORECASE)
        ]
        if not matching_labels:
            issues.append(f"Experience {number}")
    return tuple(dict.fromkeys(issues))
