import datetime as dt
import inspect
import unittest

from session_strategy.session_contract import (
    M15Bar,
    SESSION_FLOW_V2_LEGS,
    StrategyType,
    SessionType,
    EntryEngine,
    SweepSide,
    box_direction_v1,
    classify_completed_box,
    classify_sweep,
)


UTC = dt.timezone.utc


def bar(index, open_=100.0, high=101.0, low=99.0, close=100.0,
        start=dt.datetime(2022, 10, 3, tzinfo=UTC)):
    return M15Bar(start + dt.timedelta(minutes=15 * index), open_, high, low, close)


class SignedCompletedBoxSweepTests(unittest.TestCase):
    def test_signed_trend_direction_is_long_and_entry_contract_stays_blocked(self):
        candles = [bar(i, open_=100.0 + i, high=102.0 + i,
                       low=99.0 + i, close=101.0 + i) for i in range(32)]
        result = classify_completed_box(
            SESSION_FLOW_V2_LEGS["POST_ASIAN"], dt.date(2022, 10, 3), candles)
        self.assertEqual(result.session_type, SessionType.TREND)
        self.assertEqual(result.entry_engine, EntryEngine.ENTRY_1)
        self.assertEqual(result.direction, "LONG")
        self.assertEqual(result.entry_status, "ENTRY_1_CONTRACT_INCOMPLETE")

    def test_box_direction_v1_long_short_and_exact_equality(self):
        self.assertEqual(box_direction_v1(100.0, 101.0), "LONG")
        self.assertEqual(box_direction_v1(100.0, 99.0), "SHORT")
        self.assertIsNone(box_direction_v1(100.0, 100.0))

    def test_box_direction_v1_has_no_future_data_input(self):
        frozen = box_direction_v1(100.0, 101.0)
        self.assertEqual(frozen, "LONG")
        self.assertEqual(box_direction_v1(100.0, 101.0), frozen)
        self.assertEqual(list(inspect.signature(box_direction_v1).parameters),
                         ["first_open", "final_close"])

    def test_high_penetration_and_zero_clearance_reclaim_is_short(self):
        result = classify_sweep([bar(0), bar(1, high=102.0, low=99.5, close=100.5)])
        self.assertTrue(result.qualified)
        self.assertEqual((result.side, result.direction), (SweepSide.HIGH, "SHORT"))
        self.assertEqual((result.prior_level, result.penetration,
                          result.reclaim_clearance), (101.0, 1.0, 0.5))

    def test_low_penetration_and_zero_clearance_reclaim_is_long(self):
        result = classify_sweep([bar(0), bar(1, high=100.5, low=98.0, close=99.5)])
        self.assertTrue(result.qualified)
        self.assertEqual((result.side, result.direction), (SweepSide.LOW, "LONG"))

    def test_breakouts_without_reclaim_are_not_sweeps(self):
        high_break = classify_sweep([bar(0), bar(1, high=102.0, low=99.5, close=101.5)])
        low_break = classify_sweep([bar(0), bar(1, high=100.5, low=98.0, close=98.5)])
        self.assertFalse(high_break.qualified)
        self.assertFalse(low_break.qualified)

    def test_touch_only_is_not_penetration(self):
        high_touch = classify_sweep([bar(0), bar(1, high=101.0, low=99.5, close=100.5)])
        low_touch = classify_sweep([bar(0), bar(1, high=100.5, low=99.0, close=99.5)])
        self.assertFalse(high_touch.qualified)
        self.assertFalse(low_touch.qualified)

    def test_first_qualified_owns_later_opposite_side(self):
        result = classify_sweep([
            bar(0),
            bar(1, high=102.0, low=99.5, close=100.5),
            bar(2, high=100.5, low=98.0, close=99.5),
        ])
        self.assertEqual((result.candidate_index, result.side, result.direction),
                         (1, SweepSide.HIGH, "SHORT"))
        self.assertEqual(result.candidates_checked, 1)

    def test_same_candle_dual_side_is_sweep_but_entry_two_fails_closed(self):
        result = classify_sweep([bar(0), bar(1, high=102.0, low=98.0, close=100.0)])
        self.assertTrue(result.qualified)
        self.assertEqual(result.side, SweepSide.DUAL)
        self.assertIsNone(result.direction)
        self.assertEqual(result.entry_status, "BLOCKED_DUAL_SIDE_AMBIGUITY")

    def test_causal_levels_are_tested_before_candidate_updates_them(self):
        result = classify_sweep([bar(0), bar(1, high=102.0, low=99.5, close=100.5)])
        self.assertTrue(result.qualified)
        self.assertEqual(result.prior_high, 101.0)
        self.assertNotEqual(result.prior_high, 102.0)

    def test_no_sweep_routes_not_trend_box_to_range(self):
        candles = [bar(i) for i in range(32)]
        selected = classify_completed_box(
            SESSION_FLOW_V2_LEGS["POST_ASIAN"], dt.date(2022, 10, 3), candles)
        self.assertEqual(selected.strategy_type, StrategyType.RANGE)
        self.assertEqual(selected.session_type, SessionType.RANGE)
        self.assertEqual(selected.entry_engine, EntryEngine.ENTRY_3)
        self.assertEqual(selected.sweep_test, "NO_SWEEP")
        self.assertFalse(selected.sweep.qualified)

    def test_not_trend_sweep_routes_to_sweep_and_keeps_entry_separate(self):
        candles = [bar(i) for i in range(32)]
        candles[1] = bar(1, high=102.0, low=99.5, close=100.5)
        selected = classify_completed_box(
            SESSION_FLOW_V2_LEGS["POST_ASIAN"], dt.date(2022, 10, 3), candles)
        self.assertEqual(selected.strategy_type, StrategyType.SWEEP)
        self.assertEqual(selected.session_type, SessionType.RANGE)
        self.assertEqual(selected.entry_engine, EntryEngine.ENTRY_2)
        self.assertEqual(selected.direction, "SHORT")
        self.assertEqual(selected.entry_status, "BLOCKED_BY_ENTRY_2_SPEC")

    def test_trend_precedence_skips_internal_sweep(self):
        candles = [bar(0)]
        candles.append(bar(1, open_=100.0, high=102.0, low=99.5, close=100.5))
        for i in range(2, 32):
            close = 100.5 + (i - 1)
            candles.append(bar(i, open_=close - 1, high=close + 0.2,
                               low=close - 1.2, close=close))
        selected = classify_completed_box(
            SESSION_FLOW_V2_LEGS["POST_ASIAN"], dt.date(2022, 10, 3), candles)
        self.assertEqual(selected.strategy_type, StrategyType.TREND)
        self.assertEqual(selected.session_type, SessionType.TREND)
        self.assertEqual(selected.entry_engine, EntryEngine.ENTRY_1)
        self.assertEqual(selected.sweep_test, "NOT_EVALUATED")
        self.assertIsNone(selected.sweep)

    def test_post_box_candle_is_rejected_and_cannot_reroute(self):
        candles = [bar(i) for i in range(32)]
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        baseline = classify_completed_box(leg, dt.date(2022, 10, 3), candles)
        self.assertEqual(baseline.strategy_type, StrategyType.RANGE)
        with self.assertRaisesRegex(ValueError, "INVALID_REFERENCE_SESSION"):
            classify_completed_box(
                leg, dt.date(2022, 10, 3), candles +
                [bar(32, high=102.0, low=99.5, close=100.5)])


if __name__ == "__main__":
    unittest.main()
