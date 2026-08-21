import datetime as dt
import unittest

from session_strategy.session_contract import EntryEngine, SessionType, SetupType
from session_strategy.v2_funnel import FunnelRecord, summarize_funnel


def rec(index, session_type, setup_type, engine, sweep_evaluated, sweep_qualified,
        entry_status="ENTRY_SPEC_BLOCKED"):
    return FunnelRecord(
        "SESSION_FLOW_V2_SIMPLE", "2.1-simple", "TEST",
        dt.date(2022, 10, 3) + dt.timedelta(days=index), "A", "ASIAN", True,
        "CLASSIFIED", 0.5 if session_type is SessionType.TREND else 0.1,
        session_type, sweep_evaluated, sweep_qualified, setup_type, engine, None,
        entry_status,
    )


class SessionFlowV2FunnelTests(unittest.TestCase):
    def test_100_box_session_range_and_setup_splits_reconcile(self):
        rows = []
        for i in range(40):
            rows.append(rec(i, SessionType.TREND, SetupType.TREND,
                            EntryEngine.ENTRY_1, False, None))
        for i in range(40, 60):
            rows.append(rec(i, SessionType.RANGE, SetupType.SWEEP,
                            EntryEngine.ENTRY_2, True, True))
        for i in range(60, 100):
            rows.append(rec(i, SessionType.RANGE, SetupType.RANGE,
                            EntryEngine.ENTRY_3, True, False))
        result = summarize_funnel(rows)
        c = result["counts"]
        self.assertEqual((c["reference_valid"], c["trend_sessions"], c["range_sessions"]),
                         (100, 40, 60))
        self.assertEqual((c["sweep_setups"], c["range_setups"]), (20, 40))
        self.assertTrue(result["funnel_reconciles"])

    def test_trend_is_not_in_sweep_denominator(self):
        row = rec(0, SessionType.TREND, SetupType.TREND,
                  EntryEngine.ENTRY_1, False, None)
        result = summarize_funnel([row])
        self.assertEqual(result["counts"]["range_sessions"], 0)
        self.assertEqual(result["counts"]["range_with_sweep"], 0)

    def test_blocked_sweep_entry_retains_sweep_setup(self):
        row = rec(0, SessionType.RANGE, SetupType.SWEEP,
                  EntryEngine.ENTRY_2, True, True, "SWEEP_ENTRY_SPEC_BLOCKED")
        result = summarize_funnel([row])
        self.assertEqual(row.setup_type, SetupType.SWEEP)
        self.assertEqual(result["counts"]["entry_blocked"], 1)

    def test_range_no_entry_retains_range_setup(self):
        row = rec(0, SessionType.RANGE, SetupType.RANGE,
                  EntryEngine.ENTRY_3, True, False, "NO_VALID_RANGE_ENTRY")
        result = summarize_funnel([row])
        self.assertEqual(row.setup_type, SetupType.RANGE)
        self.assertEqual(result["counts"]["no_valid_entry"], 1)
        self.assertEqual(result["counts"]["tickets"], 0)

    def test_invalid_reference_never_enters_classification(self):
        invalid = FunnelRecord("SESSION_FLOW_V2_SIMPLE", "2.1-simple", "TEST",
                               dt.date(2022, 10, 3), "A", "ASIAN", False,
                               "INVALID_REFERENCE")
        result = summarize_funnel([invalid])
        self.assertEqual(result["counts"]["reference_invalid"], 1)
        self.assertEqual(result["counts"]["trend_sessions"], 0)
        self.assertEqual(result["counts"]["range_sessions"], 0)

    def test_duplicate_owner_is_rejected(self):
        row = rec(0, SessionType.TREND, SetupType.TREND,
                  EntryEngine.ENTRY_1, False, None)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_FUNNEL_OWNER"):
            summarize_funnel([row, row])

    def test_invalid_lineage_and_duplicate_entry_ownership_fail_closed(self):
        bad_trend = rec(0, SessionType.TREND, SetupType.SWEEP,
                        EntryEngine.ENTRY_2, True, True)
        with self.assertRaisesRegex(ValueError, "INVALID_TREND_FUNNEL_LINEAGE"):
            summarize_funnel([bad_trend])


if __name__ == "__main__":
    unittest.main()
