import unittest

from src.user_message_context import USER_MESSAGE_POLICY, requests_application_procedure, response_language


class UserMessageContextTests(unittest.TestCase):
    def test_chinese_request_overrides_english_interface_language(self) -> None:
        message = "我曾经经历过抑郁和校园霸凌，这段经历适合写文书吗？"
        self.assertEqual(response_language("en", message), "zh")

    def test_english_request_overrides_chinese_interface_language(self) -> None:
        self.assertEqual(
            response_language("zh", "Please recommend four PIQs."),
            "en",
        )

    def test_ambiguous_request_keeps_interface_language(self) -> None:
        self.assertEqual(response_language("zh", "4 PIQ"), "zh")

    def test_application_form_request_is_outside_essay_recommendation_scope(self) -> None:
        self.assertTrue(requests_application_procedure("how to fill in my uc application"))
        self.assertTrue(requests_application_procedure("如何填写UC申请"))

    def test_essay_request_is_not_misclassified_as_form_procedure(self) -> None:
        self.assertFalse(requests_application_procedure("How should I fill out my UC PIQ essay?"))

    def test_user_experience_policy_prevents_false_absence_claim(self) -> None:
        self.assertIn("Do not claim that an experience is absent", USER_MESSAGE_POLICY)
        self.assertIn("you mentioned", USER_MESSAGE_POLICY)
        self.assertIn("do not manufacture a full ranked recommendation list", USER_MESSAGE_POLICY)
        self.assertIn("not establish what the student did", USER_MESSAGE_POLICY)
        self.assertIn('Do not label such a minimally', USER_MESSAGE_POLICY)


if __name__ == "__main__":
    unittest.main()
