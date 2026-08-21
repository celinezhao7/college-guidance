import unittest

from src.piq_follow_up import rank_piq_evidence_gaps, summarize_piq_profile_evidence


class PiqGapRankingTests(unittest.TestCase):
    def test_challenge_is_not_mistaken_for_student_action(self):
        context = """Experience 1: Moving Schools
Challenge: Changed languages.
Outcome: Adapted successfully.
Reflection: Learned persistence.
"""
        summary = summarize_piq_profile_evidence(context, 1)
        self.assertEqual(0, summary.well_supported_count)
        self.assertEqual("action", rank_piq_evidence_gaps(context)[0].field)

    def test_nearly_complete_experience_is_prioritized_over_sparse_one(self):
        context = """Experience 1: Nearly Complete
Actions: Built a tutoring plan.
Outcome: Not documented.
Reflection: Learned to listen.
Experience 2: Sparse
Background: Joined a club.
"""
        gaps = rank_piq_evidence_gaps(context)
        self.assertEqual("Experience 1: Nearly Complete", gaps[0].experience_label)
        self.assertEqual("outcome", gaps[0].field)


if __name__ == "__main__":
    unittest.main()
