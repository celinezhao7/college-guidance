import unittest

from src.college_major import official_school_url
from src.safety.output_guard import validate_generated_output


class CollegeOfficialLinkTests(unittest.TestCase):
    def test_scorecard_school_url_is_normalized(self) -> None:
        self.assertEqual(official_school_url("example.edu"), "https://example.edu")
        self.assertEqual(official_school_url("https://example.edu/path"), "https://example.edu/path")

    def test_unsafe_or_empty_school_url_is_rejected(self) -> None:
        self.assertIsNone(official_school_url("javascript:alert(1)"))
        self.assertIsNone(official_school_url(""))

    def test_unapproved_generated_url_is_blocked(self) -> None:
        facts = {"schools": [{
            "name": "Example University", "admission_rate": None, "cost": None,
            "net_price": None, "size": None, "fields": [],
            "official_url": "https://example.edu",
        }]}
        allowed = validate_generated_output(
            "## 1. Example University\n\nOfficial website: https://example.edu",
            application_type="college_major", fact_reference=facts,
        )
        blocked = validate_generated_output(
            "## 1. Example University\n\nOfficial website: https://fake.example",
            application_type="college_major", fact_reference=facts,
        )
        self.assertTrue(allowed.allowed)
        self.assertFalse(blocked.allowed)


if __name__ == "__main__":
    unittest.main()
