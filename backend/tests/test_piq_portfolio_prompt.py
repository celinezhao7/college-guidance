import re
import unittest
from pathlib import Path


class PiqPortfolioPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[2] / "src" / "recommend.py").read_text(
            encoding="utf-8"
        )

    def test_four_item_portfolio_uses_quality_first_two_stage_selection(self) -> None:
        self.assertIn("# FOUR-PIQ PORTFOLIO OPTIMIZATION", self.source)
        self.assertIn("Stage 1 — Individual quality", self.source)
        self.assertIn("Stage 2 — Portfolio selection", self.source)
        self.assertIn("Quality has priority", self.source)

    def test_diversity_is_limited_to_comparable_candidates(self) -> None:
        self.assertIn("difference of 0.5 points or less as comparable", self.source)
        self.assertIn("never replace", self.source.lower())
        self.assertIn("a 9.2 candidate with a 5.8 candidate", self.source)

    def test_all_three_diversity_dimensions_are_defined(self) -> None:
        for dimension in (
            "Experience Diversity",
            "Trait Diversity",
            "Story Type Diversity",
        ):
            self.assertIn(dimension, self.source)

    def test_portfolio_rules_are_only_injected_for_four_recommendations(self) -> None:
        match = re.search(
            r'if recommendation_count == 4:\s*system_prompt \+= """(.*?)"""',
            self.source,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertIn("## Four-PIQ Portfolio Balance", match.group(1))
        self.assertIn("Do not add this section when fewer than four", match.group(1))


if __name__ == "__main__":
    unittest.main()
