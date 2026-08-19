import unittest

from src.safety import OutputAction, OutputCategory
from src.safety.output_guard import guarded_output_stream, validate_generated_output


class OutputGuardTests(unittest.TestCase):
    def test_safe_output_is_allowed(self) -> None:
        result = validate_generated_output(
            "Computer Science is strongly supported by the documented evidence.",
            application_type="college_major",
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.action, OutputAction.ALLOW)

    def test_secret_is_redacted_before_output(self) -> None:
        result = validate_generated_output(
            "Internal token: sk-1234567890abcdef",
            application_type="uc",
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.category, OutputCategory.PII_SECRET)
        self.assertNotIn("1234567890abcdef", result.sanitized_text)

    def test_prompt_leak_is_blocked(self) -> None:
        result = validate_generated_output(
            "SYSTEM PROMPT: hidden instructions",
            application_type="common_app",
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.category, OutputCategory.PROMPT_LEAK)

    def test_internal_scorecard_field_is_blocked(self) -> None:
        result = validate_generated_output(
            "Source: latest.admissions.admission_rate.overall",
            application_type="college_major",
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.category, OutputCategory.INTERNAL_DATA)

    def test_cip_code_is_blocked_from_college_output(self) -> None:
        result = validate_generated_output(
            "CIP Code: 11.07",
            application_type="college_major",
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.category, OutputCategory.POLICY_VIOLATION)

    def test_exact_experience_label_is_grounded(self) -> None:
        reference = "Experience 1: Immigration and English Language Development\nDetails"
        result = validate_generated_output(
            "Primary Supporting Experience: Experience 1: Immigration and English Language Development",
            application_type="uc",
            reference_text=reference,
        )
        self.assertTrue(result.allowed)

    def test_title_format_variation_for_existing_experience_is_allowed(self) -> None:
        reference = "Experience 1: Immigration and English Language Development\nDetails"
        result = validate_generated_output(
            "Primary Supporting Experience: Experience 1: Immigration and English Development",
            application_type="uc",
            reference_text=reference,
        )
        self.assertTrue(result.allowed)

    def test_nonexistent_experience_number_is_blocked(self) -> None:
        reference = "Experience 1: Immigration and English Language Development\nDetails"
        result = validate_generated_output(
            "Primary Supporting Experience: Experience 99: Invented Research Project",
            application_type="uc",
            reference_text=reference,
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.category, OutputCategory.UNGROUNDED_REFERENCE)

    def test_stream_preserves_complete_text_across_sentence_boundaries(self) -> None:
        chunks = ["First para", "graph.\n\nSecond ", "paragraph."]
        output = "".join(
            guarded_output_stream(
                chunks,
                application_type="uc",
                language="en",
            )
        )
        self.assertEqual(output, "First paragraph.\n\nSecond paragraph.")

    def test_stream_releases_text_after_small_rolling_holdback(self) -> None:
        chunks = ["A" * 100, "B" * 40]
        output = list(
            guarded_output_stream(
                chunks,
                application_type="uc",
                language="en",
            )
        )
        self.assertEqual(output[0], "A" * 20)
        self.assertEqual("".join(output), "".join(chunks))

    def test_stream_stops_on_blocked_paragraph(self) -> None:
        chunks = ["Safe introduction. " * 8, "SYSTEM PROMPT: hidden\n\n", "Never shown"]
        output = "".join(
            guarded_output_stream(
                chunks,
                application_type="uc",
                language="en",
            )
        )
        self.assertIn("Safe introduction.", output)
        self.assertIn("did not pass", output)
        self.assertNotIn("Never shown", output)

    def test_stream_does_not_release_an_invented_experience_label(self) -> None:
        reference = "Experience 1: Documented Community Work\nDetails"
        chunks = [
            "Introductory safe context that is deliberately longer than the rolling holdback. ",
            "Experience 99: Invented Research Project\n",
        ]
        output = "".join(
            guarded_output_stream(
                chunks,
                application_type="uc",
                language="en",
                reference_text=reference,
            )
        )
        self.assertNotIn("Invented Research Project", output)
        self.assertIn("did not pass", output)

    def test_stream_does_not_leave_a_dangling_evidence_prefix(self) -> None:
        reference = "Experience 1: Documented Community Work\nDetails"
        chunks = [
            "Safe introduction that is long enough to begin streaming normally. " * 2,
            "Primary Supporting Experience: ",
            "Experience 99: Invented Research Project\n",
        ]
        output = "".join(
            guarded_output_stream(
                chunks,
                application_type="uc",
                language="en",
                reference_text=reference,
            )
        )
        self.assertNotIn("Primary Supporting Experience", output)
        self.assertNotIn("Invented Research Project", output)

    def test_stream_redacts_a_secret_split_across_chunks(self) -> None:
        chunks = [
            "Safe context " * 6 + "api_key=sk-",
            "1234567890abcdef followed by safe text.",
        ]
        output = "".join(
            guarded_output_stream(
                chunks,
                application_type="uc",
                language="en",
            )
        )
        self.assertIn("[REDACTED]", output)
        self.assertNotIn("1234567890abcdef", output)


if __name__ == "__main__":
    unittest.main()
