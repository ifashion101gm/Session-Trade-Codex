import unittest

from scripts.cowork_sweep_v2_population_study import run_study


class CoworkSweepPopulationStudyTests(unittest.TestCase):
    def test_population_is_complete_and_outcome_free(self):
        rows, summary = run_study()
        self.assertEqual(len(rows), 90)
        self.assertEqual(summary["valid"], 90)
        self.assertEqual(summary["trend_sessions"] + summary["range_sessions"], 90)
        self.assertFalse(summary["retired_completed_box_population_comparable"])
        self.assertEqual(summary["orders_fills_pnl"], "NOT_CALCULATED")


if __name__ == "__main__":
    unittest.main()
