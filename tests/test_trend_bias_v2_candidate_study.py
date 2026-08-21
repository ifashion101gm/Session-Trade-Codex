import unittest

from scripts.trend_bias_v2_candidate_study import candidate_a, run_study


class TrendBiasV2CandidateStudyTests(unittest.TestCase):
    def test_candidate_a_rule(self):
        self.assertEqual(candidate_a(1.0, 2.0), "LONG")
        self.assertEqual(candidate_a(2.0, 1.0), "SHORT")
        self.assertEqual(candidate_a(1.0, 1.0), "DIRECTION_UNRESOLVED")

    def test_study_is_outcome_blind_and_preserves_router(self):
        rows, summary = run_study()
        self.assertEqual(summary["population"], {
            "all_references": 90, "trend_references": 8})
        self.assertEqual(len(rows), 8)
        self.assertFalse(summary["trade_outcomes_used"])
        self.assertFalse(summary["router_changed"])
        self.assertFalse(summary["sweep_classifier_changed"])
        self.assertEqual(summary["candidate_b"]["status"],
                         "NOT_EVALUABLE_SPEC_INCOMPLETE")
        self.assertEqual(summary["candidate_c"]["status"],
                         "NOT_EVALUABLE_SPEC_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
