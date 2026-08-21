import datetime as dt
import unittest

from session_strategy.cowork_sweep_v2 import detect_range_session_sweeps
from session_strategy.session_contract import (
    M15Bar, SESSION_FLOW_V2_LEGS, SessionType,
    classify_trend_range, validate_and_freeze_session,
)


UTC = dt.timezone.utc


class SweepDetectionRangeV2ValidationTests(unittest.TestCase):
    def frozen(self, close=100.0):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        day = dt.date(2022, 10, 3)
        start, _ = leg.bounds(day)
        bars = [M15Bar(start + dt.timedelta(minutes=15 * i), 100, 101, 99, close)
                for i in range(32)]
        return validate_and_freeze_session(leg, day, bars, leg.activation_utc(day))

    def test_only_validated_range_session_may_enter_sweep_detection(self):
        session = self.frozen()
        classification = classify_trend_range(session)
        self.assertEqual(classification.session_type, SessionType.RANGE)
        execution = [M15Bar(session.end, 100.5, 101.1, 99.5, 100.0)]
        signals = detect_range_session_sweeps(
            session, classification, execution, 0.1)
        self.assertEqual((signals[0].direction, signals[0].reference_price),
                         ("SHORT", 100.5))

    def test_trend_session_fails_closed(self):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        day = dt.date(2022, 10, 3)
        start, _ = leg.bounds(day)
        bars = [M15Bar(start + dt.timedelta(minutes=15 * i), 100 + i, 102 + i,
                       99 + i, 101 + i) for i in range(32)]
        session = validate_and_freeze_session(leg, day, bars, leg.activation_utc(day))
        classification = classify_trend_range(session)
        self.assertEqual(classification.session_type, SessionType.TREND)
        with self.assertRaisesRegex(ValueError, "SWEEP_DETECTION_REQUIRES_RANGE_SESSION"):
            detect_range_session_sweeps(session, classification, [], 0.1)

    def test_execution_timestamps_must_be_ordered_and_unique(self):
        session = self.frozen()
        classification = classify_trend_range(session)
        bar = M15Bar(session.end, 100, 101, 99, 100)
        with self.assertRaisesRegex(ValueError, "INVALID_COWORK_SWEEP_TIMESTAMPS"):
            detect_range_session_sweeps(
                session, classification, [bar, bar], 0.1)


if __name__ == "__main__":
    unittest.main()
