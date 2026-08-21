import unittest

from src.college_major import college_fact_card, matching_programs, rank_verified_colleges, render_college_fact_cards


class DeterministicCollegeRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preferences = {
            "field": "Computer Science", "states": "CA", "targets": "No specific target",
            "max_cost": 60_000, "size": ["any"], "competition": ["any"],
        }

    def college(self, name: str, field_score: float, *, cost=50_000, state="CA") -> dict:
        return {
            "id": hash(name), "school.name": name, "school.state": state,
            "latest.cost.attendance.academic_year": cost,
            "latest.cost.avg_net_price.overall": None,
            "latest.admissions.admission_rate.overall": 0.4,
            "latest.student.size": 10_000,
            "matching_bachelors_fields": [{"title": "Computer Science", "match_score": field_score}],
        }

    def test_exact_field_strength_determines_order_after_verification(self) -> None:
        ranked = rank_verified_colleges([self.college("Lower Match", 0.7), self.college("Higher Match", 1.0)], self.preferences)
        self.assertEqual(["Higher Match", "Lower Match"], [item["school.name"] for item in ranked])

    def test_target_school_is_kept_first(self) -> None:
        preferences = {**self.preferences, "targets": "Named Target"}
        ranked = rank_verified_colleges([self.college("Strong Alternative", 1.0), self.college("Named Target", 0.7)], preferences)
        self.assertEqual("Named Target", ranked[0]["school.name"])

    def test_fact_status_and_selection_reasons_are_attached(self) -> None:
        result = rank_verified_colleges([self.college("Example", 1.0)], self.preferences)[0]
        self.assertEqual("verified", result["fact_status"]["attendance_cost"]["status"])
        self.assertEqual("unavailable", result["fact_status"]["average_net_price"]["status"])
        self.assertEqual("College Scorecard", result["fact_status"]["admission_rate"]["source"])
        self.assertIn("Matches the requested state filter", result["selection"]["reasons"])

    def test_fact_card_contains_only_clean_deterministic_fields(self) -> None:
        college = self.college("Example", 1.0)
        college["school.city"] = "Example City"
        college["school.school_url"] = "example.edu"
        payload = college_fact_card(college)
        self.assertEqual("https://example.edu", payload["official_url"])
        self.assertNotIn("selection", payload)
        rendered = render_college_fact_cards([college])
        self.assertIn(":::college-fact", rendered)
        self.assertNotIn("ranking_score", rendered)
        self.assertIn("reporting years may differ", payload["data_vintage"])
        self.assertRegex(payload["retrieved_on"], r"^\d{4}-\d{2}-\d{2}$")

    def test_program_match_exposes_honest_match_status(self) -> None:
        programs = [
            {"title": "Computer Science", "cip_code": "11.07"},
            {"title": "Computer and Information Sciences, General", "cip_code": "11.01"},
        ]
        direct = matching_programs("Computer Science", programs)[0]
        self.assertEqual("direct_title_match", direct["match_status"])


if __name__ == "__main__":
    unittest.main()
