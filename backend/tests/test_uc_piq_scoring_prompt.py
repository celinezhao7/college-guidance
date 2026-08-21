import re
import unittest
from decimal import Decimal
from pathlib import Path

from src.piq_scoring import (
    calculated_uc_match_score,
    normalize_uc_match_score,
    normalize_uc_match_score_stream,
)


class UcPiqScoringPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        recommend_source = Path(__file__).parents[2] / "src" / "recommend.py"
        source = recommend_source.read_text(encoding="utf-8")
        match = re.search(
            r'UC_SYSTEM_PROMPT = """(.*?)"""\s*\n\s*# =+\s*\n# Common App',
            source,
            re.DOTALL,
        )
        if match is None:
            raise AssertionError("UC_SYSTEM_PROMPT was not found")
        cls.prompt = match.group(1)

    def test_match_score_has_reproducible_weighted_formula(self) -> None:
        self.assertIn(
            "Match Score = (Prompt Fit x 0.35) + (Evidence Depth x 0.35)",
            self.prompt,
        )
        self.assertIn("+ (Personal Insight x 0.30)", self.prompt)
        self.assertIn("Round the Match Score to one decimal place", self.prompt)

    def test_output_replaces_qualitative_strength_with_numeric_score(self) -> None:
        self.assertIn("**Match Score: [calculated score]/10**", self.prompt)
        self.assertIn("**Score Breakdown:** Prompt Fit [score]/10", self.prompt)
        self.assertNotIn("**Evidence Strength:** High / Medium / Low", self.prompt)

    def test_portfolio_distinctiveness_does_not_change_item_score(self) -> None:
        self.assertIn(
            "Distinctiveness is a portfolio-selection factor, not part of the Match",
            self.prompt,
        )

    def test_backend_clamps_and_formats_match_score(self) -> None:
        self.assertEqual(
            normalize_uc_match_score("**Match Score: 12.34/10**"),
            "**Match Score: 10.0 / 10**",
        )
        self.assertEqual(
            normalize_uc_match_score("**Match Score: -1/10**"),
            "**Match Score: 0.0 / 10**",
        )
        self.assertEqual(
            normalize_uc_match_score("**Match Score: 8/10**"),
            "**Match Score: 8.0 / 10**",
        )

    def test_stream_normalizes_score_split_across_chunks(self) -> None:
        output = "".join(
            normalize_uc_match_score_stream(
                ["**Match Score: ", "8.74", "/10**\n", "Experience 2: Research"]
            )
        )
        self.assertIn("**Match Score: 8.7 / 10**", output)
        self.assertIn("Experience 2: Research", output)

    def test_backend_recomputes_score_and_removes_scratch_arithmetic(self) -> None:
        output = "".join(
            normalize_uc_match_score_stream(
                [
                    "**Match Score: 5.8 / 10**\n",
                    "**Score Breakdown:** Prompt Fit 7/10; Evidence Depth 4/10; "
                    "Personal Insight 6/10 Calculation: wrong scratch work\n",
                ]
            )
        )
        self.assertIn("**Match Score: 5.7 / 10**", output)
        self.assertIn(
            "**Score Breakdown:** Prompt Fit 7/10; Evidence Depth 4/10; Personal Insight 6/10",
            output,
        )
        self.assertNotIn("Calculation", output)
        self.assertEqual(calculated_uc_match_score("7", "4", "6"), Decimal("5.7"))

    def test_prompt_forbids_evidence_inflation_and_single_item_portfolio_text(self) -> None:
        self.assertIn("Preserve qualifiers exactly", self.prompt)
        self.assertIn("do not add Why These Recommendations", self.prompt)


if __name__ == "__main__":
    unittest.main()
