import unittest
from unittest.mock import patch

from backend.app.conversation_service import TargetCollegeIntent, chat


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


if __name__ == "__main__":
    unittest.main()
