import datetime as dt
import inspect
import unittest
from collections import Counter

from scripts.session_flow_v2_classification_study import (
    END, SOURCES, START, load_bars, weekdays,
)
from session_strategy.session_contract import (
    EntryEngine, M15Bar, SESSION_FLOW_V2_LEGS, SessionType, SetupType,
    route_v2_simple, validate_and_freeze_session,
)


class SessionFlowV2SimpleRouterTests(unittest.TestCase):
    def frozen(self, closes, highs=None, lows=None):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        day = dt.date(2022, 10, 3)
        start, _ = leg.bounds(day)
        closes = list(closes) + [closes[-1]] * (32 - len(closes))
        highs = list(highs or [max(101.0, value + 1.0) for value in closes])
        lows = list(lows or [min(99.0, value - 1.0) for value in closes])
        highs += [highs[-1]] * (32 - len(highs))
        lows += [lows[-1]] * (32 - len(lows))
        bars = [M15Bar(start + dt.timedelta(minutes=15 * i),
                       100.0 if i == 0 else closes[i - 1],
                       highs[i], lows[i], closes[i]) for i in range(32)]
        return validate_and_freeze_session(leg, day, bars, leg.activation_utc(day))

    def test_trend_routes_entry_1_without_sweep_evaluation(self):
        session = self.frozen([100.0, 110.0] + list(range(111, 141)))
        route = route_v2_simple(session)
        self.assertEqual((route.regime.session_type, route.setup_type, route.entry_engine),
                         (SessionType.TREND, SetupType.TREND, EntryEngine.ENTRY_1))
        self.assertFalse(route.sweep_evaluated)
        self.assertIsNone(route.sweep_qualified)

    def test_range_reference_sweep_routes_entry_2(self):
        session = self.frozen(
            [100.0, 100.5, 100.2],
            highs=[101.0, 102.0, 101.0],
            lows=[99.0, 99.5, 99.5],
        )
        route = route_v2_simple(session)
        self.assertEqual((route.regime.session_type, route.setup_type, route.entry_engine),
                         (SessionType.RANGE, SetupType.SWEEP, EntryEngine.ENTRY_2))
        self.assertTrue(route.sweep_qualified)
        self.assertEqual(route.sweep_scope, "REFERENCE_SESSION_ONLY")

    def test_range_without_reference_sweep_routes_entry_3(self):
        route = route_v2_simple(self.frozen([100.0]))
        self.assertEqual((route.regime.session_type, route.setup_type, route.entry_engine),
                         (SessionType.RANGE, SetupType.RANGE, EntryEngine.ENTRY_3))
        self.assertFalse(route.sweep_qualified)
        self.assertIsNone(route.direction)

    def test_router_is_stateless_deterministic_and_has_no_future_input(self):
        session = self.frozen([100.0, 100.5, 100.2],
                              highs=[101.0, 102.0, 101.0],
                              lows=[99.0, 99.5, 99.5])
        self.assertEqual(route_v2_simple(session), route_v2_simple(session))
        self.assertEqual(list(inspect.signature(route_v2_simple).parameters), ["session"])
        self.assertEqual(route_v2_simple(session).strategy_flow,
                         "SESSION_FLOW_V2_SIMPLE")

    def test_post_session_candle_is_rejected_before_routing(self):
        session = self.frozen([100.0])
        extra = M15Bar(session.end, 100.0, 500.0, 1.0, 400.0)
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        with self.assertRaisesRegex(ValueError, "INVALID_SESSION_DATA"):
            validate_and_freeze_session(
                leg, session.trading_date, list(session.candles) + [extra], session.end)

    def test_ninety_historical_sessions_have_exactly_one_stable_route(self):
        counts = Counter()
        checked = 0
        for source in SOURCES.values():
            indexed = load_bars(source)
            for day in weekdays(START, END):
                for leg in SESSION_FLOW_V2_LEGS.values():
                    start, _ = leg.bounds(day)
                    bars = [indexed[start + dt.timedelta(minutes=15 * i)]
                            for i in range(leg.expected_m15_candles)]
                    session = validate_and_freeze_session(
                        leg, day, bars, leg.activation_utc(day))
                    route = route_v2_simple(session)
                    self.assertEqual(route, route_v2_simple(session))
                    self.assertIn(route.setup_type, SetupType)
                    self.assertIn(route.entry_engine, EntryEngine)
                    counts[route.setup_type.value] += 1
                    checked += 1
        self.assertEqual(checked, 90)
        self.assertEqual(counts, {"TREND": 8, "SWEEP": 81, "RANGE": 1})


if __name__ == "__main__":
    unittest.main()
