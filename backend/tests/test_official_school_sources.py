import unittest

from src.official_school_sources import official_sources_for_school, validated_official_url


class OfficialSchoolSourceTests(unittest.TestCase):
    def test_reviewed_ucla_pages_are_available_by_scorecard_name(self):
        pages = official_sources_for_school("University of California-Los Angeles")
        self.assertEqual({"majors", "first_year_requirements", "cost"}, {page["kind"] for page in pages})
        self.assertTrue(all(page["url"].startswith("https://admission.ucla.edu/") for page in pages))

    def test_unregistered_school_has_no_invented_official_pages(self):
        self.assertEqual([], official_sources_for_school("Imaginary University"))

    def test_url_validation_blocks_domain_confusion_and_credentials(self):
        domains = ["admission.ucla.edu"]
        self.assertIsNone(validated_official_url("https://admission.ucla.edu.evil.test/cost", domains))
        self.assertIsNone(validated_official_url("https://user@admission.ucla.edu/cost", domains))
        self.assertIsNone(validated_official_url("http://admission.ucla.edu/cost", domains))


if __name__ == "__main__":
    unittest.main()
