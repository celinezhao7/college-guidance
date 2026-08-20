import unittest

from src.request_preferences import (
    explicitly_requested_mode,
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


if __name__ == "__main__":
    unittest.main()
