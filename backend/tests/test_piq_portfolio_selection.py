import unittest

from src.piq_portfolio import PiqCandidate, assess_and_select_portfolio, select_four_piq_portfolio


def candidate(number, score, experience, trait, story):
    return PiqCandidate(number, score, score, score, experience, (trait,), story)


class PiqPortfolioSelectionTests(unittest.TestCase):
    def test_large_quality_gap_can_never_be_replaced_for_diversity(self):
        items = [
            candidate(1, 9.2, "Experience 1", "leadership", "leadership_community"),
            candidate(2, 8.8, "Experience 1", "leadership", "leadership_community"),
            candidate(3, 8.3, "Experience 1", "leadership", "leadership_community"),
            candidate(4, 8.0, "Experience 1", "leadership", "leadership_community"),
            candidate(5, 5.8, "Experience 2", "creativity", "creative_personal"),
        ]
        result = select_four_piq_portfolio(items)
        self.assertEqual([1, 2, 3, 4], [item.piq_number for item in result.selected])
        self.assertIsNone(result.substitution)

    def test_comparable_candidate_may_improve_portfolio_diversity(self):
        items = [
            candidate(1, 9.0, "Experience 1", "curiosity", "academic_technical"),
            candidate(2, 8.8, "Experience 1", "curiosity", "academic_technical"),
            candidate(3, 8.6, "Experience 1", "curiosity", "academic_technical"),
            candidate(4, 8.4, "Experience 1", "curiosity", "academic_technical"),
            candidate(5, 8.0, "Experience 2", "service", "responsibility_service"),
        ]
        result = select_four_piq_portfolio(items)
        self.assertEqual([1, 2, 3, 5], [item.piq_number for item in result.selected])
        self.assertEqual((4, 5, 0.4), result.substitution)

    def test_invalid_model_json_falls_back_without_crashing(self):
        class Llm:
            def invoke(self, _):
                return type("Response", (), {"content": "not json"})()
        self.assertIsNone(assess_and_select_portfolio(Llm(), "Experience 1: Example"))

    def test_invented_primary_experience_is_rejected(self):
        payload = [
            {"piq_number": number, "prompt_fit": 8, "evidence_depth": 8,
             "personal_insight": 8, "primary_experience": "Experience 99: Invented",
             "traits": ["curiosity"], "story_type": "academic_technical"}
            for number in range(1, 9)
        ]
        class Llm:
            def invoke(self, _):
                return type("Response", (), {"content": __import__("json").dumps(payload)})()
        self.assertIsNone(assess_and_select_portfolio(Llm(), "Experience 1: Real"))


if __name__ == "__main__":
    unittest.main()
