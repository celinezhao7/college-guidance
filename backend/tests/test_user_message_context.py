import unittest

from src.user_message_context import USER_MESSAGE_POLICY, response_language


class UserMessageContextTests(unittest.TestCase):
    def test_chinese_request_overrides_english_interface_language(self) -> None:
        message = "我曾经经历过抑郁和校园霸凌，这段经历适合写文书吗？"
        self.assertEqual(response_language("en", message), "zh")

    def test_user_experience_policy_prevents_false_absence_claim(self) -> None:
        self.assertIn("Do not claim that an experience is absent", USER_MESSAGE_POLICY)
        self.assertIn("you mentioned", USER_MESSAGE_POLICY)
        self.assertIn("do not manufacture a full ranked recommendation list", USER_MESSAGE_POLICY)


if __name__ == "__main__":
    unittest.main()
