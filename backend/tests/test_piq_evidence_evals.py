import json
import unittest
from pathlib import Path

from src.piq_follow_up import rank_piq_evidence_gaps, summarize_piq_profile_evidence


class PiqEvidenceEvalTests(unittest.TestCase):
    def test_versioned_evidence_cases(self):
        path = Path(__file__).parents[1] / "evals" / "piq_evidence_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 4)
        for case in cases:
            with self.subTest(case=case["name"]):
                summary = summarize_piq_profile_evidence(case["context"], case["requested_count"])
                self.assertEqual(case["well_supported_count"], summary.well_supported_count)
                gaps = rank_piq_evidence_gaps(case["context"])
                actual = [gaps[0].experience_label, gaps[0].field] if gaps else None
                self.assertEqual(case["top_gap"], actual)


if __name__ == "__main__":
    unittest.main()
