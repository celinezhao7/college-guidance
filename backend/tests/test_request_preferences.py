import unittest

from src.request_preferences import (
    conversational_recommendation_count,
    explicitly_requested_mode,
    prior_recommended_prompt_numbers,
    requested_recommendation_count,
)


class RequestPreferenceTests(unittest.TestCase):
    def test_defaults_are_preserved_without_explicit_count(self) -> None:
        self.assertEqual(requested_recommendation_count("recommend for me", "uc"), 4)
        self.assertEqual(requested_recommendation_count("recommend for me", "common_app"), 3)

    def test_chinese_single_recommendation(self) -> None:
        self.assertEqual(
            requested_recommendation_count("我要piq推荐，一个就够", "uc"),
            1,
        )

    def test_chinese_follow_up_count_with_classifier(self) -> None:
        self.assertEqual(
            requested_recommendation_count("我只想要两个", "uc"),
            2,
        )

    def test_follow_up_inherits_the_most_recent_explicit_count(self) -> None:
        self.assertEqual(
            conversational_recommendation_count(
                "把第二个换掉",
                "uc",
                ["请推荐两个", "第二个为什么适合？"],
            ),
            2,
        )

    def test_current_count_overrides_conversation_history(self) -> None:
        self.assertEqual(
            conversational_recommendation_count("现在只要一个", "uc", ["请推荐两个"]),
            1,
        )

    def test_english_two_recommendations(self) -> None:
        self.assertEqual(
            requested_recommendation_count("Just recommend two prompts", "common_app"),
            2,
        )

    def test_count_is_capped_by_available_prompts(self) -> None:
        self.assertEqual(requested_recommendation_count("Give me 8 prompts", "common_app"), 7)

    def test_explicit_mode_is_detected(self) -> None:
        self.assertEqual(explicitly_requested_mode("I need a PIQ recommendation"), "uc")
        self.assertEqual(explicitly_requested_mode("帮我选 Common App 主文书"), "common_app")
        self.assertIsNone(explicitly_requested_mode("recommend for me"))

    def test_prior_prompt_numbers_come_only_from_assistant_history(self) -> None:
        history = [
            {"role": "user", "content": "Why not PIQ #7?"},
            {"role": "assistant", "content": "### Primary recommendation: PIQ #4 — Barrier"},
        ]
        self.assertEqual(prior_recommended_prompt_numbers(history, "uc"), [4])

    def test_all_prior_recommendations_are_preserved_in_display_order(self) -> None:
        history = [
            {
                "role": "assistant",
                "content": (
                    "Primary recommendation: PIQ #5\n"
                    "Second choice: PIQ #6\n"
                    "Third choice: PIQ #7\n"
                    "Fourth choice: PIQ #2"
                ),
            }
        ]
        self.assertEqual(
            prior_recommended_prompt_numbers(history, "uc"),
            [5, 6, 7, 2],
        )


if __name__ == "__main__":
    unittest.main()
