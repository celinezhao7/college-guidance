import re
import unittest
from pathlib import Path

from src.piq_follow_up import (
    piq_follow_up_round,
    PIQ_MAX_FOLLOW_UP_ROUNDS,
    has_piq_evidence_warning,
    normalize_piq_follow_up_heading,
    normalize_piq_follow_up_heading_stream,
    requests_direct_piq_recommendation,
    requests_piq_information_follow_up,
    requests_skip_current_piq_question,
    summarize_piq_profile_evidence,
)


class PiqFollowUpStateTests(unittest.TestCase):
    def test_round_is_read_from_english_and_chinese_markers(self) -> None:
        self.assertEqual(
            piq_follow_up_round(
                [
                    {"role": "assistant", "content": "**Information Needed — Question 1**"},
                    {"role": "user", "content": "I cleaned the dataset."},
                    {"role": "assistant", "content": "**需要补充的信息 — 第 3 个问题**"},
                ]
            ),
            3,
        )

    def test_user_text_cannot_fake_a_completed_round(self) -> None:
        self.assertEqual(
            piq_follow_up_round(
                [{"role": "user", "content": "Information Needed (Round 2/2)"}]
            ),
            0,
        )

    def test_direct_recommendation_request_is_detected(self) -> None:
        for message in ("Skip all", "Just recommend now", "不知道，直接推荐吧", "不要再问了"):
            with self.subTest(message=message):
                self.assertTrue(requests_direct_piq_recommendation(message))

    def test_evidence_choice_intents_are_detected(self) -> None:
        self.assertTrue(requests_direct_piq_recommendation("Continue anyway"))
        self.assertTrue(requests_piq_information_follow_up("Add information"))
        self.assertTrue(requests_piq_information_follow_up("补充信息并完善推荐"))
        self.assertTrue(
            has_piq_evidence_warning(
                [{"role": "assistant", "content": "**More Information Recommended**"}]
            )
        )

    def test_skipping_one_question_does_not_skip_all(self) -> None:
        for message in ("skip", "Skip this question", "跳过这题", "不知道"):
            with self.subTest(message=message):
                self.assertTrue(requests_skip_current_piq_question(message))
                self.assertFalse(requests_direct_piq_recommendation(message))
        for message in ("Skip all and recommend now", "全部跳过，直接推荐"):
            with self.subTest(message=message):
                self.assertFalse(requests_skip_current_piq_question(message))
                self.assertTrue(requests_direct_piq_recommendation(message))

    def test_misspelled_recommendation_is_not_a_continue_choice(self) -> None:
        self.assertFalse(requests_direct_piq_recommendation("recmooned 4 piqs"))
        self.assertFalse(requests_piq_information_follow_up("recmooned 4 piqs"))

    def test_follow_up_heading_is_forced_to_requested_language(self) -> None:
        self.assertEqual(
            normalize_piq_follow_up_heading("需要补充的信息（第 1/2 轮）", "en"),
            "Information Needed — Question 1",
        )
        self.assertEqual(
            normalize_piq_follow_up_heading("Information Needed (Round 2/2)", "zh"),
            "需要补充的信息 — 第 2 个问题",
        )
        self.assertEqual(
            normalize_piq_follow_up_heading("建议补充更多信息", "en"),
            "More Information Recommended",
        )
        streamed = "".join(
            normalize_piq_follow_up_heading_stream(
                ["**需要补充的", "信息（第 1/2 轮）**\n"],
                "en",
            )
        )
        self.assertEqual(streamed, "**Information Needed — Question 1**\n")

    def test_follow_up_limit_is_configurable_and_bounded(self) -> None:
        self.assertGreaterEqual(PIQ_MAX_FOLLOW_UP_ROUNDS, 1)
        self.assertLessEqual(PIQ_MAX_FOLLOW_UP_ROUNDS, 10)

    def test_limited_profile_requires_follow_up_for_requested_count(self) -> None:
        context = """
Experience 1: Initial Interest
Evidence Reliability: Self-reported interest only.
Actions:
- Read one article.
Outcome:
The student has not yet tested this interest.
Reflection:
The student is curious.

Experience 2: Occasional Participation
Actions:
- Helped once.
Outcome:
No independent project was completed.
Reflection:
The student enjoyed it.
"""
        summary = summarize_piq_profile_evidence(context, requested_count=3)
        self.assertEqual(summary.experience_count, 2)
        self.assertEqual(summary.well_supported_count, 0)
        self.assertTrue(summary.requires_initial_follow_up)

    def test_complete_profile_can_recommend_without_forced_follow_up(self) -> None:
        experience = """
Experience {number}: Documented Work {number}
Actions:
- Designed and completed the work.
Impact:
- Improved the program.
Reflection:
- Learned to adapt and lead.
"""
        context = "\n".join(experience.format(number=index) for index in range(1, 4))
        summary = summarize_piq_profile_evidence(context, requested_count=3)
        self.assertEqual(summary.well_supported_count, 3)
        self.assertFalse(summary.requires_initial_follow_up)

    def test_prompt_defines_targeted_questions_and_hard_limit(self) -> None:
        source = (Path(__file__).parents[2] / "src" / "recommend.py").read_text(
            encoding="utf-8"
        )
        prompt = re.search(
            r'UC_SYSTEM_PROMPT = """(.*?)"""\s*\n\s*# =+\s*\n# Common App',
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(prompt)
        value = prompt.group(1)
        self.assertIn("Ask exactly one focused question at a time", value)
        self.assertIn("candidates you are actually preparing to select", value)
        self.assertIn("unused Experience has an undocumented field", value)
        self.assertIn("Information Needed — Question [number]", value)
        self.assertIn("Never ask a vague", value)


if __name__ == "__main__":
    unittest.main()
