"""Small, dependency-free localization helpers for the CLI."""

LANGUAGES = {"1": "en", "2": "zh", "en": "en", "zh": "zh"}

MESSAGES = {
    "language_title": {"en": "Choose language / 选择语言", "zh": "选择语言 / Choose language"},
    "language_en": {"en": "1. English", "zh": "1. English（英文）"},
    "language_zh": {"en": "2. Chinese (Simplified)", "zh": "2. 简体中文"},
    "language_prompt": {"en": "Enter choice (1 or 2) [1]: ", "zh": "请输入选项（1 或 2）[1]："},
    "app_title": {"en": "COLLEGE GUIDANCE ASSISTANT", "zh": "大学申请指导助手"},
    "choose_system": {"en": "Choose application system:", "zh": "请选择申请系统："},
    "menu_uc": {"en": "1. UC PIQ Recommendation", "zh": "1. UC 个人洞察问题（PIQ）推荐"},
    "menu_common": {"en": "2. Common App Essay Prompt Recommendation", "zh": "2. Common App 主文书题目推荐"},
    "menu_college": {"en": "3. College & Major Matching", "zh": "3. 大学与专业匹配"},
    "choice_123": {"en": "Enter choice (1, 2, or 3): ", "zh": "请输入选项（1、2 或 3）："},
    "invalid_123": {"en": "Invalid choice. Please enter 1, 2, or 3.", "zh": "选项无效，请输入 1、2 或 3。"},
    "unable": {"en": "Unable to create recommendations: {error}", "zh": "无法生成推荐：{error}"},
    "retrieved_guidance": {"en": "Retrieved {count} {name} chunks", "zh": "已检索 {count} 个 {name} 指导片段"},
    "retrieved_student": {"en": "Retrieved {count} student chunks", "zh": "已检索 {count} 个学生经历片段"},
    "retrieval_time": {"en": "Retrieval time: {seconds:.2f}s", "zh": "检索耗时：{seconds:.2f} 秒"},
    "student_evidence": {"en": "Student evidence retrieved:", "zh": "已检索的学生经历："},
    "ttft": {"en": "Time to first token: {seconds:.2f}s", "zh": "首个字符生成耗时：{seconds:.2f} 秒"},
    "ttfo": {"en": "Time to first visible output: {seconds:.2f}s", "zh": "首段可见输出耗时：{seconds:.2f} 秒"},
    "ttft_na": {"en": "Time to first token: N/A", "zh": "首个字符生成耗时：无"},
    "generation_time": {"en": "Generation time: {seconds:.2f}s", "zh": "生成耗时：{seconds:.2f} 秒"},
    "total_time": {"en": "Total time: {seconds:.2f}s", "zh": "总耗时：{seconds:.2f} 秒"},
}


def choose_language() -> str:
    print("\n" + "=" * 60)
    print(MESSAGES["language_title"]["zh"])
    print("=" * 60)
    print(MESSAGES["language_en"]["zh"])
    print(MESSAGES["language_zh"]["zh"])
    choice = input(MESSAGES["language_prompt"]["zh"]).strip() or "1"
    return LANGUAGES.get(choice.lower(), "en")


def tr(language: str, key: str, **values) -> str:
    message = MESSAGES[key].get(language, MESSAGES[key]["en"])
    return message.format(**values)


def output_language_instruction(language: str) -> str:
    if language == "zh":
        return (
            "\n\nLANGUAGE REQUIREMENT: Write the entire recommendation in Simplified Chinese. "
            "Keep official school names, CIP codes, PIQ/prompt numbers, source field names, "
            "and student experience labels exactly as supplied."
        )
    return "\n\nLANGUAGE REQUIREMENT: Write the entire recommendation in English."
