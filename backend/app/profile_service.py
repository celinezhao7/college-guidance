"""Read-only access to student profile files for the API layer."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class StudentProfile:
    id: str
    display_name: str
    display_name_en: str
    display_name_zh: str
    filename: str


def get_profile_directory() -> Path:
    setting = os.getenv("STUDENT_PROFILE_DIR", "data/student_profiles")
    directory = Path(setting)
    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory
    return directory.resolve()


def _profile_id(filename: str) -> str:
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()[:12]


def list_profiles() -> list[StudentProfile]:
    directory = get_profile_directory()
    if not directory.is_dir():
        return []

    preferred_order = {
        "完整学生档案": 0,
        "信息不足学生档案": 1,
        "兴趣模糊学生档案": 2,
    }
    english_names = {
        "完整学生档案": "Relatively Complete Student Profile",
        "信息不足学生档案": "Limited-Information Student Profile",
        "兴趣模糊学生档案": "Broad-Interest Student Profile",
    }
    chinese_names = {
        "完整学生档案": "相对完整学生档案",
    }
    paths = sorted(
        directory.glob("*.docx"),
        key=lambda path: (
            preferred_order.get(path.stem, len(preferred_order)),
            path.name.casefold(),
        ),
    )
    return [
        StudentProfile(
            id=_profile_id(path.name),
            display_name=path.stem,
            display_name_en=english_names.get(path.stem, path.stem),
            display_name_zh=chinese_names.get(path.stem, path.stem),
            filename=path.name,
        )
        for path in paths
    ]


def get_profile(profile_id: str) -> StudentProfile | None:
    return next(
        (profile for profile in list_profiles() if profile.id == profile_id),
        None,
    )
