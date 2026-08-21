import datetime as dt
import unittest

from scripts.session_flow_v2_classification_study import (
    END, SOURCES, START, load_bars, weekdays,
)
from session_strategy.session_contract import (
    ER_ONLY_V2_CLASSIFIER_ID,
    M15Bar,
    SESSION_FLOW_V2_LEGS,
    SessionType,
    box_direction_v1,
    classify_trend_range,
    validate_and_freeze_session,
)


class EROnlyV2ValidationTests(unittest.TestCase):
    def synthetic_session(self, closes, first_open=100.0):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        day = dt.date(2022, 10, 3)
        start, _ = leg.bounds(day)
        values = list(closes) + [closes[-1]] * (32 - len(closes))
        bars = []
        previous = first_open
        for index, close in enumerate(values):
            open_ = first_open if index == 0 else previous
            bars.append(M15Bar(
                start + dt.timedelta(minutes=15 * index), open_,
                max(open_, close) + 1.0, min(open_, close) - 1.0, close,
            ))
            previous = close
        return validate_and_freeze_session(leg, day, bars, leg.activation_utc(day))

    def test_exact_040_is_trend_and_contract_is_frozen(self):
        session = self.synthetic_session([100.0, 117.5, 110.0])
        result = classify_trend_range(session)
        self.assertAlmostEqual(result.efficiency_ratio, 0.40)
        self.assertEqual(result.session_type, SessionType.TREND)
        self.assertEqual(result.direction, "LONG")
        self.assertEqual((result.classifier_id, result.threshold, result.equality,
                          result.zero_path, result.status),
                         (ER_ONLY_V2_CLASSIFIER_ID, 0.40, "TREND", "RANGE", "VALIDATED"))

    def test_zero_path_is_range_and_range_has_no_direction(self):
        result = classify_trend_range(self.synthetic_session([100.0]))
        self.assertEqual(result.efficiency_ratio, 0.0)
        self.assertEqual(result.session_type, SessionType.RANGE)
        self.assertIsNone(result.direction)
        self.assertIsNone(box_direction_v1(100.0, 100.0))

    def test_invalid_or_incomplete_session_fails_before_classification(self):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        day = dt.date(2022, 10, 3)
        start, end = leg.bounds(day)
        bars = [M15Bar(start + dt.timedelta(minutes=15 * i), 100, 101, 99, 100)
                for i in range(32)]
        with self.assertRaisesRegex(ValueError, "INVALID_SESSION_DATA"):
            validate_and_freeze_session(leg, day, bars[:-1], end)
        with self.assertRaisesRegex(ValueError, "INVALID_SESSION_DATA"):
            validate_and_freeze_session(leg, day, bars, end - dt.timedelta(minutes=1))

    def test_historical_sessions_reproduce_independently_and_deterministically(self):
        checked = 0
        for source in SOURCES.values():
            indexed = load_bars(source)
            for day in weekdays(START, END):
                for leg in SESSION_FLOW_V2_LEGS.values():
                    start, _ = leg.bounds(day)
                    bars = [indexed[start + dt.timedelta(minutes=15 * i)]
                            for i in range(leg.expected_m15_candles)]
                    frozen = validate_and_freeze_session(
                        leg, day, bars, leg.activation_utc(day))
                    first = classify_trend_range(frozen)
                    second = classify_trend_range(frozen)
                    closes = [bar.close for bar in bars]
                    manual_path = abs(closes[0] - bars[0].open) + sum(
                        abs(current - previous)
                        for previous, current in zip(closes, closes[1:]))
                    manual_er = 0.0 if manual_path == 0 else abs(
                        closes[-1] - bars[0].open) / manual_path
                    self.assertAlmostEqual(first.efficiency_ratio, manual_er)
                    self.assertEqual(first, second)
                    self.assertFalse(hasattr(first, "setup_type"))
                    self.assertFalse(hasattr(first, "entry_engine"))
                    checked += 1
        self.assertEqual(checked, 90)

    def test_future_candle_cannot_enter_frozen_session(self):
        session = self.synthetic_session([100.0, 110.0, 100.0])
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        extra = M15Bar(session.end, 100, 200, 1, 150)
        with self.assertRaisesRegex(ValueError, "INVALID_SESSION_DATA"):
            validate_and_freeze_session(
                leg, session.trading_date, list(session.candles) + [extra], session.end)


if __name__ == "__main__":
    unittest.main()
