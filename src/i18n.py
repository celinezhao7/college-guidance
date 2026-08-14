"""Small, dependency-free localization helpers for the CLI."""

LANGUAGES = {"1": "en", "2": "zh", "en": "en", "zh": "zh"}

MESSAGES = {
    "language_title": {"en": "Choose language / 选择语言", "zh": "选择语言 / Choose language"},
    "language_en": {"en": "1. English", "zh": "1. English（英文）"},
    "language_zh": {"en": "2. Chinese (Simplified)", "zh": "2. 简体中文"},
    "language_prompt": {
        "en": "Enter choice (1 or 2) / 请输入选项（1 或 2）: ",
        "zh": "请输入选项（1 或 2）/ Enter choice (1 or 2): ",
    },
    "app_title": {"en": "COLLEGE GUIDANCE ASSISTANT", "zh": "大学申请指导助手"},
    "choose_system": {"en": "Choose application system:", "zh": "请选择申请系统："},
    "menu_uc": {"en": "1. UC PIQ Recommendation", "zh": "1. UC 个人洞察问题（PIQ）推荐"},
    "menu_common": {"en": "2. Common App Essay Prompt Recommendation", "zh": "2. Common App 主文书题目推荐"},
    "menu_college": {"en": "3. College & Field-of-Study Matching", "zh": "3. 大学与专业领域匹配"},
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
    while True:
        choice = input(MESSAGES["language_prompt"]["zh"]).strip().lower()
        if choice in LANGUAGES:
            return LANGUAGES[choice]
        print("请输入 1 或 2。/ Please enter 1 or 2.")


def tr(language: str, key: str, **values) -> str:
    message = MESSAGES[key].get(language, MESSAGES[key]["en"])
    return message.format(**values)


def output_language_instruction(language: str) -> str:
    if language == "zh":
        return (
            "\n\n# CHINESE OUTPUT REQUIREMENT (HIGHEST PRIORITY)\n"
            "Write the complete user-facing answer in Simplified Chinese. Do not "
            "use English section headings, labels, ratings, explanatory sentences, "
            "or parenthetical English translations. Proper names and established "
            "abbreviations such as UC, Common App, PIQ, and official university names "
            "may remain in their official form.\n"
            "Translate prompt titles, field-of-study titles, and student experience "
            "titles into natural Chinese. Preserve their original numbers so the "
            "evidence remains traceable, but do not repeat the English title. Any "
            "earlier instruction to keep an experience or prompt title exactly as "
            "supplied applies to its number and meaning, not its English wording.\n"
            "Use Chinese labels throughout. For example:\n"
            "- Rank #1 -> 第1名\n"
            "- Why It Fits -> 适配原因\n"
            "- Primary Supporting Experience -> 主要支持经历\n"
            "- Secondary Supporting Evidence -> 补充支持经历\n"
            "- Story Potential -> 故事潜力\n"
            "- Personal Insight Potential -> 个人洞察潜力\n"
            "- Supporting Evidence -> 支持证据\n"
            "- Student Action -> 学生行动\n"
            "- Impact / Outcome -> 影响或结果\n"
            "- Reflection / Personal Insight -> 反思与个人洞察\n"
            "- Evidence Strength -> 证据强度\n"
            "- High / Medium / Low -> 高 / 中 / 低\n"
            "- Evidence Gaps -> 证据缺口\n"
            "- No major evidence gap -> 暂无重大证据缺口\n"
            "- Best Overall Choice -> 最佳总体选择\n"
            "- Why Not the Other Prompts -> 未选择其他题目的原因\n"
            "- Why These Four -> 为什么选择这四道题\n"
            "Before returning the answer, check every heading and label and replace "
            "any remaining English wording that is not an allowed proper name."
        )
    return "\n\nLANGUAGE REQUIREMENT: Write the entire recommendation in English."
