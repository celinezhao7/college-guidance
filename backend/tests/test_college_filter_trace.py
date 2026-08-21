import unittest

from src.college_major import apply_college_filters, format_filter_bottlenecks


class CollegeFilterTraceTests(unittest.TestCase):
    def test_filter_trace_identifies_constraints_that_removed_candidates(self) -> None:
        colleges = [
            {"school.carnegie_basic": 15, "latest.student.size": 4000, "latest.admissions.admission_rate.overall": 0.4, "latest.cost.attendance.academic_year": 70000},
            {"school.carnegie_basic": 15, "latest.student.size": 10000, "latest.admissions.admission_rate.overall": 0.4, "latest.cost.attendance.academic_year": 40000},
        ]
        preferences = {
            "institution_format": ["either"], "size": ["small"], "competition": ["any"],
            "admission_rate_min": 0, "admission_rate_max": 100, "max_cost": 50000,
        }
        result, trace = apply_college_filters(colleges, preferences)
        self.assertEqual([], result)
        explanation = format_filter_bottlenecks(trace, "en")
        self.assertIn("undergraduate size: 2 → 1", explanation)
        self.assertIn("maximum cost: 1 → 0", explanation)

    def test_unchanged_filters_are_not_reported(self) -> None:
        trace = [
            {"filter": "size", "before": 5, "after": 5},
            {"filter": "reported_field", "before": 5, "after": 2},
        ]
        output = format_filter_bottlenecks(trace, "zh")
        self.assertNotIn("学校规模", output)
        self.assertIn("专业领域验证: 5 → 2", output)


if __name__ == "__main__":
    unittest.main()
