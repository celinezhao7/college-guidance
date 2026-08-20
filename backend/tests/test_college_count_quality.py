import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.college_major import stream_college_recommendations


class CollegeCountQualityTests(unittest.TestCase):
    def test_fewer_supported_schools_are_reported_without_padding(self) -> None:
        college = {
            "id": 1,
            "school.name": "Example University",
            "school.city": "Example City",
            "school.state": "CA",
        }
        preferences = {
            "field": "Computer Science",
            "states": "CA",
            "targets": "No specific target",
            "count": 5,
            "institution_format": ["either"],
            "size": ["any"],
            "competition": ["any"],
            "admission_rate_min": 0,
            "admission_rate_max": 100,
            "max_cost": None,
        }
        llm = SimpleNamespace(
            stream=lambda messages: iter([SimpleNamespace(content="## 1. Example University")])
        )

        with (
            patch("src.college_major.fetch_colleges_cached", return_value=[]),
            patch("src.college_major.rank_colleges", return_value=[college]),
            patch(
                "src.college_major.fetch_bachelors_fields_cached",
                return_value={1: [{"title": "Computer Science"}]},
            ),
            patch(
                "src.college_major.matching_programs",
                return_value=[{"title": "Computer Science"}],
            ),
        ):
            output = "".join(
                stream_college_recommendations(
                    llm,
                    "documented evidence",
                    preferences,
                    language="en",
                )
            )

        self.assertIn("Only 1 college", output)
        self.assertIn("fewer than the 5 requested", output)
        self.assertIn("## 1. Example University", output)


if __name__ == "__main__":
    unittest.main()
