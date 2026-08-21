import unittest

from scripts.session_flow_v2_classification_study import run_study


class SessionFlowV2ClassificationStudyTests(unittest.TestCase):
    def test_oct_3_21_three_symbol_funnel_reconciles(self):
        rows, summary = run_study()
        counts = summary["counts"]
        self.assertEqual(len(rows), 90)
        self.assertEqual((counts["reference_valid"], counts["reference_invalid"]),
                         (90, 0))
        self.assertEqual((counts["trend_sessions"], counts["range_sessions"]),
                         (8, 82))
        self.assertEqual((counts["sweep_setups"], counts["range_setups"]),
                         (81, 1))
        self.assertTrue(summary["funnel_reconciles"])
        self.assertTrue(all(summary["equations"].values()))
        self.assertEqual(counts["tickets"], 0)
        self.assertEqual(counts["fills"], 0)


if __name__ == "__main__":
    unittest.main()
