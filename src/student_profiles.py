import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def get_student_profile_dir() -> Path:
    setting = os.getenv("STUDENT_PROFILE_DIR", "data/student_profiles")
    profile_dir = Path(setting)
    if not profile_dir.is_absolute():
        profile_dir = BASE_DIR / profile_dir
    return profile_dir


def list_student_profiles() -> list[Path]:
    preferred_order = {
        "学生信息知识库": 0,
        "信息不足": 1,
        "兴趣模糊": 2,
    }
    return sorted(
        get_student_profile_dir().glob("*.docx"),
        key=lambda path: (
            preferred_order.get(path.stem, len(preferred_order)),
            path.name.casefold(),
        ),
    )


def choose_student_profile(
    profiles: list[Path],
    language: str = "en",
    input_fn=input,
) -> Path:
    if not profiles:
        raise FileNotFoundError(
            f"No .docx student profiles found in {get_student_profile_dir()}"
        )

    if language == "zh":
        print("\n请选择学生档案：\n")
    else:
        print("\nChoose a student profile:\n")

    for index, path in enumerate(profiles, start=1):
        print(f"{index}. {path.stem}")

    while True:
        if language == "zh":
            prompt = f"\n请输入选项（1–{len(profiles)}）："
        else:
            prompt = f"\nEnter choice (1-{len(profiles)}): "

        raw_choice = input_fn(prompt).strip()
        try:
            choice = int(raw_choice)
        except ValueError:
            choice = 0

        if 1 <= choice <= len(profiles):
            return profiles[choice - 1]

        if language == "zh":
            print(f"请输入 1 到 {len(profiles)} 之间的整数。")
        else:
            print(f"Enter an integer from 1 to {len(profiles)}.")
