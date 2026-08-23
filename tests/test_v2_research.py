import datetime as dt
import unittest

from session_strategy.session_contract import M15Bar, SESSION_FLOW_V2_LEGS, validate_and_freeze_session
from session_strategy.v2_research import (
    build_risk_geometry,
    detect_strict_sweep,
    er_040_research_candidate,
    extract_reference_features,
    midpoint_side_research_candidate,
    route_v2_research,
)


class V2ResearchTests(unittest.TestCase):
    def make_session(self, closes, highs=None, lows=None):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        day = dt.date(2022, 10, 3)
        start, _ = leg.bounds(day)
        closes = list(closes)
        closes += [closes[-1]] * (leg.expected_m15_candles - len(closes))
        supplied_highs = highs is not None
        supplied_lows = lows is not None
        highs = list(highs or [])
        lows = list(lows or [])
        if supplied_highs:
            highs += [highs[-1]] * (leg.expected_m15_candles - len(highs))
        if supplied_lows:
            lows += [lows[-1]] * (leg.expected_m15_candles - len(lows))
        bars = []
        for index, close in enumerate(closes):
            open_price = 100.0 if index == 0 else closes[index - 1]
            if not supplied_highs:
                highs.append(max(open_price, close) + 1.0)
            if not supplied_lows:
                lows.append(min(open_price, close) - 1.0)
            bars.append(M15Bar(start + dt.timedelta(minutes=15 * index), open_price,
                               highs[index], lows[index], close))
        return validate_and_freeze_session(leg, day, bars, leg.activation_utc(day))

    def test_features_are_box_only_and_deterministic(self):
        session = self.make_session([100.0, 102.0, 101.0, 103.0])
        first = extract_reference_features(session)
        second = extract_reference_features(session)
        self.assertEqual(first, second)
        self.assertEqual(first.candle_count, 32)
        self.assertEqual(first.midpoint_crossing_count, 3)
        self.assertEqual(first.high_index, 3)
        self.assertEqual(first.low_index, 0)

    def test_research_classifiers_are_explicitly_callable_only(self):
        session = self.make_session([100.0, 102.0, 101.0, 103.0])
        features = extract_reference_features(session)
        self.assertIn(er_040_research_candidate(features), {"TREND", "RANGE"})
        self.assertIn(midpoint_side_research_candidate(features), {"TREND", "RANGE"})
        intent = route_v2_research(session)
        self.assertIsNone(intent.setup)
        self.assertEqual(intent.execution_status, "ANALYSIS_ONLY")
        self.assertIn("REGIME_CLASSIFIER_UNRESOLVED", intent.reason_codes)

    def test_strict_sweep_requires_established_level_and_reclaims(self):
        candles = [
            M15Bar(dt.datetime(2022, 10, 3, 0, tzinfo=dt.timezone.utc), 100, 101, 99, 100),
            M15Bar(dt.datetime(2022, 10, 3, 0, 15, tzinfo=dt.timezone.utc), 100, 103, 100, 100.5),
        ]
        missing = detect_strict_sweep(candles)
        self.assertFalse(missing.qualified)
        self.assertEqual(missing.reason_code, "SWEEP_INSUFFICIENT_LEVEL")
        sweep = detect_strict_sweep(candles, 101, 99)
        self.assertTrue(sweep.qualified)
        self.assertEqual((sweep.direction, sweep.reason_code), ("SHORT", "SWEEP_HIGH_RECLAIM"))
        breakout = detect_strict_sweep(
            candles[:1] + [M15Bar(candles[1].open_time, 100, 103, 100, 102)], 101, 99)
        self.assertFalse(breakout.qualified)

    def test_risk_geometry_is_fixed_and_symmetric(self):
        long_stop, long_tp1, long_tp2 = build_risk_geometry(100.0, "LONG", 4.0)
        short_stop, short_tp1, short_tp2 = build_risk_geometry(100.0, "SHORT", 4.0)
        self.assertEqual((long_stop, long_tp1, long_tp2), (99.0, 104.0, 105.0))
        self.assertEqual((short_stop, short_tp1, short_tp2), (101.0, 96.0, 95.0))

    def test_post_box_data_cannot_change_features(self):
        session = self.make_session([100.0, 101.0, 100.0, 101.0])
        original = extract_reference_features(session)
        post_box = M15Bar(session.end, 101.0, 1000.0, 1.0, 2.0)
        self.assertEqual(original, extract_reference_features(session))
        self.assertGreater(post_box.high, session.box_top)


if __name__ == "__main__":
    unittest.main()