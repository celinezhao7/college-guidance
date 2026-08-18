import unittest
from types import ModuleType
from unittest.mock import Mock, patch

from backend.app.conversation_service import (
    TargetCollegeIntent,
    _resolve_scorecard_target,
    _translate_college_name_to_english,
    chat,
)


class CollegeFirstConversationTests(unittest.TestCase):
    def _start_college_first(self, language: str) -> str:
        first = chat(None, "test-profile", language, "hi")
        second = chat(first["session_id"], "test-profile", language, "1")
        self.assertEqual(second["scenario"], "college_first")
        return second["session_id"]

    def test_chinese_dont_know_switches_to_exploration(self) -> None:
        session_id = self._start_college_first("zh")

        with patch(
            "backend.app.conversation_service._classify_target_college",
            return_value=TargetCollegeIntent("no_target", None, 0.96),
        ):
            result = chat(session_id, "test-profile", "zh", "不知道欸")

        self.assertTrue(result["ready"])
        self.assertEqual(result["scenario"], "explore")
        self.assertNotIn("不知道欸", result["preferences"].get("targets", ""))
        self.assertIn("没有目标大学", result["reply"])

    def test_english_not_sure_switches_to_exploration(self) -> None:
        session_id = self._start_college_first("en")

        with patch(
            "backend.app.conversation_service._classify_target_college",
            return_value=TargetCollegeIntent("no_target", None, 0.94),
        ):
            result = chat(session_id, "test-profile", "en", "I'm not sure yet")

        self.assertTrue(result["ready"])
        self.assertEqual(result["scenario"], "explore")
        self.assertIn("don’t have a target college", result["reply"])

    def test_target_prompt_respects_interface_language(self) -> None:
        english_first = chat(None, "test-profile", "en", "hi")
        english_prompt = chat(english_first["session_id"], "test-profile", "en", "1")
        self.assertIn("official English name", english_prompt["reply"])
        self.assertNotIn("Chinese name", english_prompt["reply"])

        chinese_first = chat(None, "test-profile", "zh", "hi")
        chinese_prompt = chat(chinese_first["session_id"], "test-profile", "zh", "1")
        self.assertIn("中文或英文校名", chinese_prompt["reply"])
        self.assertIn("先转换为英文", chinese_prompt["reply"])

    def test_target_name_uses_the_classified_college_name(self) -> None:
        session_id = self._start_college_first("en")

        with patch(
            "backend.app.conversation_service._classify_target_college",
            return_value=TargetCollegeIntent("target_college", "UMich", 0.98),
        ), patch(
            "backend.app.conversation_service._resolve_scorecard_target",
            return_value="University of Michigan-Ann Arbor",
        ):
            result = chat(session_id, "test-profile", "en", "I'm thinking about UMich")

        self.assertTrue(result["ready"])
        self.assertEqual(result["scenario"], "college_first")
        self.assertEqual(result["preferences"]["targets"], "University of Michigan-Ann Arbor")

    def test_chinese_target_is_resolved_to_scorecard_official_name(self) -> None:
        session_id = self._start_college_first("zh")

        with patch(
            "backend.app.conversation_service._classify_target_college",
            return_value=TargetCollegeIntent("target_college", "密歇根大学", 0.98),
        ), patch(
            "backend.app.conversation_service._resolve_scorecard_target",
            return_value="University of Michigan-Ann Arbor",
        ) as resolve:
            result = chat(session_id, "test-profile", "zh", "我想看密歇根大学")

        resolve.assert_called_once_with("密歇根大学")
        self.assertTrue(result["ready"])
        self.assertEqual(
            result["preferences"]["targets"],
            "University of Michigan-Ann Arbor",
        )

    def test_known_chinese_college_name_translates_without_model_call(self) -> None:
        self.assertEqual(
            _translate_college_name_to_english("密歇根大学"),
            "University of Michigan-Ann Arbor",
        )

    def test_chinese_college_name_is_translated_then_fuzzy_matched(self) -> None:
        candidates = [
            {
                "school.name": "University of Michigan-Ann Arbor",
                "_match_score": 1.5,
            },
            {
                "school.name": "University of Michigan-Flint",
                "_match_score": 0.91,
            },
        ]
        college_major = ModuleType("src.college_major")
        college_major.UC_SYSTEM_ALIASES = {"uc"}
        college_major.normalize_school_name = lambda value: " ".join(
            "".join(character.lower() if character.isalnum() else " " for character in value).split()
        )
        college_major.search_school_candidates = Mock(return_value=candidates)
        with patch(
            "backend.app.conversation_service._translate_college_name_to_english",
            return_value="University of Michigan Ann Arbour",
        ), patch.dict("sys.modules", {"src.college_major": college_major}):
            result = _resolve_scorecard_target("密西根大学安娜堡")

        self.assertEqual(result, "University of Michigan-Ann Arbor")
        college_major.search_school_candidates.assert_called_once_with(
            "University of Michigan Ann Arbour", set()
        )

    def test_unclear_answer_asks_for_clarification(self) -> None:
        session_id = self._start_college_first("zh")

        with patch(
            "backend.app.conversation_service._classify_target_college",
            return_value=TargetCollegeIntent("unclear", None, 0.42),
        ):
            result = chat(session_id, "test-profile", "zh", "也许吧")

        self.assertFalse(result["ready"])
        self.assertEqual(result["scenario"], "college_first")
        self.assertNotEqual(result["preferences"]["targets"], "也许吧")
        self.assertIn("我不确定", result["reply"])

    def test_unverified_college_does_not_start_recommendations(self) -> None:
        session_id = self._start_college_first("zh")

        with patch(
            "backend.app.conversation_service._classify_target_college",
            return_value=TargetCollegeIntent("target_college", "Imaginary University", 0.99),
        ), patch(
            "backend.app.conversation_service._resolve_scorecard_target",
            return_value=None,
        ):
            result = chat(session_id, "test-profile", "zh", "Imaginary University")

        self.assertFalse(result["ready"])
        self.assertEqual(result["scenario"], "college_first")
        self.assertNotEqual(result["preferences"]["targets"], "Imaginary University")
        self.assertIn("无法在 College Scorecard 中可靠确认", result["reply"])

    def test_scenario_response_provides_structured_quick_replies(self) -> None:
        result = chat(None, "test-profile", "zh", "hi")

        self.assertEqual(
            [reply["id"] for reply in result["quick_replies"]],
            ["scenario_college", "scenario_major", "scenario_explore"],
        )

    def test_scenario_choice_id_does_not_depend_on_its_label(self) -> None:
        first = chat(None, "test-profile", "zh", "hi")

        result = chat(
            first["session_id"],
            "test-profile",
            "zh",
            "This label can change",
            choice_id="scenario_college",
        )

        self.assertEqual(result["scenario"], "college_first")
        self.assertEqual([reply["id"] for reply in result["quick_replies"]], ["no_target"])


class FieldConversationTests(unittest.TestCase):
    def _start_major_first(self, language: str = "zh") -> str:
        first = chat(None, "test-profile", language, "hi")
        second = chat(first["session_id"], "test-profile", language, "2")
        self.assertEqual(second["scenario"], "major_first")
        return second["session_id"]

    def test_pinyin_field_is_corrected_and_requires_confirmation(self) -> None:
        session_id = self._start_major_first("zh")

        result = chat(session_id, "test-profile", "zh", "diannao")

        self.assertFalse(result["ready"])
        self.assertNotIn("field", result["answered"])
        self.assertIn("计算机科学", result["reply"])
        self.assertIn("field_yes", [reply["id"] for reply in result["quick_replies"]])

        confirmed = chat(session_id, "test-profile", "zh", "是")
        self.assertEqual(confirmed["preferences"]["field"], "计算机科学")
        self.assertIn("field", confirmed["answered"])
        self.assertIn("SAT", confirmed["reply"])

    def test_unrecognized_field_does_not_advance(self) -> None:
        session_id = self._start_major_first("zh")

        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": ""}):
            result = chat(session_id, "test-profile", "zh", "asdfgh")

        self.assertNotIn("field", result["answered"])
        self.assertNotIn("SAT", result["reply"])
        self.assertIn("无法可靠识别", result["reply"])

    def test_replacement_after_correction_is_revalidated(self) -> None:
        session_id = self._start_major_first("zh")
        chat(session_id, "test-profile", "zh", "diannao")

        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": ""}):
            result = chat(session_id, "test-profile", "zh", "不是，asdfgh")

        self.assertNotIn("field", result["answered"])
        self.assertIn("无法可靠识别", result["reply"])


if __name__ == "__main__":
    unittest.main()
