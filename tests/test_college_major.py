import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import college_major as cm


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, translation):
        self.translation = translation
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return FakeResponse(self.translation)


class MultiSelectInputTests(unittest.TestCase):
    def test_school_size_accepts_chinese_comma_and_deduplicates(self):
        with patch("builtins.input", return_value="1，2，1"):
            self.assertEqual(cm.ask_school_size("zh"), ["small", "medium"])

    def test_school_size_blank_means_any(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(cm.ask_school_size("zh"), ["any"])

    def test_ownership_accepts_multiple_choices(self):
        with patch("builtins.input", return_value="1, 2"):
            self.assertEqual(
                cm.ask_school_ownership("zh"),
                ["public", "private_nonprofit"],
            )

    def test_ownership_blank_means_any(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(cm.ask_school_ownership("zh"), ["any"])

    def test_selectivity_accepts_multiple_choices(self):
        with patch("builtins.input", return_value="2 3"):
            self.assertEqual(cm.ask_selectivity("zh"), ["medium", "high"])

    def test_institution_format_blank_means_either(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(cm.ask_institution_format("zh"), ["either"])


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.colleges = [
            {
                "school.name": "Small Selective College",
                "school.carnegie_basic": 21,
                "latest.student.size": 3_000,
                "latest.admissions.admission_rate.overall": 0.20,
            },
            {
                "school.name": "Medium University",
                "school.carnegie_basic": 15,
                "latest.student.size": 10_000,
                "latest.admissions.admission_rate.overall": 0.45,
            },
            {
                "school.name": "Large University",
                "school.carnegie_basic": 16,
                "latest.student.size": 25_000,
                "latest.admissions.admission_rate.overall": 0.70,
            },
            {
                "school.name": "Missing Data University",
                "school.carnegie_basic": None,
                "latest.student.size": None,
                "latest.admissions.admission_rate.overall": None,
            },
        ]

    def names(self, colleges):
        return [college["school.name"] for college in colleges]

    def test_size_filter_matches_any_selected_range(self):
        filtered = cm.filter_by_size(self.colleges, ["small", "medium"])
        self.assertEqual(
            self.names(filtered),
            ["Small Selective College", "Medium University"],
        )

    def test_unrestricted_size_keeps_missing_data(self):
        self.assertEqual(cm.filter_by_size(self.colleges, ["any"]), self.colleges)

    def test_selectivity_is_strict_and_excludes_missing_data(self):
        filtered = cm.filter_by_selectivity(self.colleges, ["high"])
        self.assertEqual(self.names(filtered), ["Small Selective College"])

    def test_selectivity_accepts_multiple_ranges(self):
        filtered = cm.filter_by_selectivity(self.colleges, ["medium", "low"])
        self.assertEqual(
            self.names(filtered),
            ["Medium University", "Large University"],
        )

    def test_unrestricted_selectivity_keeps_missing_data(self):
        self.assertEqual(
            cm.filter_by_selectivity(self.colleges, ["any"]), self.colleges
        )

    def test_institution_format_accepts_both_categories(self):
        filtered = cm.filter_by_institution_format(
            self.colleges, ["liberal_arts", "university"]
        )
        self.assertEqual(
            self.names(filtered),
            ["Small Selective College", "Medium University", "Large University"],
        )


class FieldTranslationAndMatchingTests(unittest.TestCase):
    def test_known_chinese_field_uses_dictionary(self):
        llm = FakeLLM("Wrong Translation")
        with patch("builtins.input", return_value=""), redirect_stdout(io.StringIO()):
            result = cm.resolve_field_query(llm, "电子工程", "zh")
        self.assertEqual(result, "Electrical Engineering")
        self.assertEqual(llm.calls, 0)

    def test_unknown_chinese_field_uses_llm_and_confirmation(self):
        llm = FakeLLM("Urban Planning.")
        with patch("builtins.input", return_value=""), redirect_stdout(io.StringIO()):
            result = cm.resolve_field_query(llm, "城市规划", "zh")
        self.assertEqual(result, "Urban Planning")
        self.assertEqual(llm.calls, 1)

    def test_user_can_correct_translation(self):
        llm = FakeLLM("Communication and Media Studies")
        with patch("builtins.input", return_value="Journalism"), redirect_stdout(
            io.StringIO()
        ):
            result = cm.resolve_field_query(llm, "新闻传播", "zh")
        self.assertEqual(result, "Journalism")

    def test_electrical_engineering_does_not_match_mechanical(self):
        programs = [
            {"title": "Mechanical Engineering."},
            {"title": "Electrical, Electronics, and Communications Engineering."},
        ]
        matches = cm.matching_programs("Electrical Engineering", programs)
        self.assertEqual(
            [match["title"] for match in matches],
            ["Electrical, Electronics, and Communications Engineering."],
        )

    def test_broad_engineering_query_can_match_engineering_fields(self):
        programs = [
            {"title": "Mechanical Engineering."},
            {"title": "Civil Engineering, General."},
        ]
        self.assertEqual(len(cm.matching_programs("Engineering", programs)), 2)


class TargetAndFallbackTests(unittest.TestCase):
    def test_uc_alias_matches_uc_campus(self):
        self.assertTrue(
            cm.matches_target("University of California-Berkeley", ["uc"])
        )

    def test_uc_conflict_can_add_public_ownership(self):
        preferences = {
            "targets": "UC",
            "ownership": ["private_nonprofit"],
            "institution_format": ["university"],
        }
        with patch("builtins.input", return_value="1"), redirect_stdout(io.StringIO()):
            self.assertTrue(cm.reconcile_known_target_conflicts(preferences, "zh"))
        self.assertEqual(
            preferences["ownership"], ["private_nonprofit", "public"]
        )

    def test_uc_conflict_can_return_to_filters(self):
        preferences = {
            "targets": "UC",
            "ownership": ["private_nonprofit"],
            "institution_format": ["liberal_arts"],
        }
        with patch("builtins.input", return_value="0"), redirect_stdout(io.StringIO()):
            self.assertFalse(cm.reconcile_known_target_conflicts(preferences, "zh"))

    def test_zero_results_returns_to_filter_loop(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cm.confirm_available_count(5, 0, "zh"), 0)


if __name__ == "__main__":
    unittest.main()
