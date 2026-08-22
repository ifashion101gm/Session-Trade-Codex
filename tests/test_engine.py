"""ASIAN_SESSION_V1 engine-contract tests.

Fixture session: Asian high 1.16800, low 1.16400, range 0.00400, R = 0.00100.
These are the numbers used by the worked examples in the specification.
"""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import unittest

from session_strategy.config import load_config
from session_strategy.engine import (analyze, calibrate_broker_tick, classify_session,
                                     detect_range_rejection, detect_sweep, execution_bounds,
                                     filter_window, lock_asian_levels, session_bounds,
                                     validate_candles)
from session_strategy.models import AccountSnapshot, Candle, Reason, SymbolSpec


TRADING_DATE = date(2026, 8, 11)
# Session now starts 00:00 on the trading date (corrected window 00:00-07:00 / 28 bars)
ASIAN_START = datetime(2026, 8, 11, 0, tzinfo=timezone.utc)
EXEC_START = datetime(2026, 8, 11, 7, tzinfo=timezone.utc)
SPEC = SymbolSpec("EURUSD", 5, .00001, .00001, .01, 100, .01, 0)

HIGH, LOW = 1.16800, 1.16400
RANGE = HIGH - LOW          # 0.00400
R = 0.25 * RANGE            # 0.00100


def account(kind="demo"):
    return AccountSnapshot("****985", kind, 1000, 1000, "VTMarkets-Demo", True, True, 10)


def asian(i, o, h, l, c):
    return Candle(ASIAN_START + timedelta(minutes=15 * i), o, h, l, c, 10)


def execution(i, o, h, l, c):
    return Candle(EXEC_START + timedelta(minutes=15 * i), o, h, l, c, 10)


def range_session(close=1.16500):
    """28 candles spanning HIGH..LOW with a mid-range close -> RANGE (corrected: 00:00-07:00 / 28 bars)."""
    bars = []
    for i in range(28):
        top = HIGH if i == 5 else HIGH - 0.0005
        bottom = LOW if i == 20 else LOW + 0.0005
        bars.append(asian(i, 1.16600, top, bottom, 1.16600))
    bars[-1] = asian(27, 1.16600, HIGH - 0.0005, LOW + 0.0005, close)
    return bars


def trend_session():
    """28 candles trending up, closing near the high -> BULLISH_TREND (corrected: 00:00-07:00 / 28 bars)."""
    bars = []
    for i in range(28):
        o = LOW + (RANGE - 0.0002) * i / 27
        bars.append(asian(i, o, min(o + 0.00012, HIGH), max(o - 0.00004, LOW), o + 0.0001))
    bars[0] = asian(0, LOW, LOW + 0.0002, LOW, LOW + 0.0001)
    bars[-1] = asian(27, HIGH - 0.0004, HIGH, HIGH - 0.0005, HIGH - 0.0002)
    return bars


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def run_analysis(self, session, execution_candles=(), **kwargs):
        when = kwargs.get("now", datetime(2026, 8, 11, 8, 45, tzinfo=timezone.utc))
        return analyze(
            config=kwargs.get("config", self.config), symbol=kwargs.get("symbol", "EURUSD"),
            trading_date=TRADING_DATE, now=when, account=kwargs.get("account", account()),
            spec=SPEC,
            tick={"bid": 1.16499, "ask": 1.16501, "time": kwargs.get("tick_time", when.timestamp()),
                  "broker_offset_hours": 0, **kwargs.get("tick", {})},
            session_candles=list(session), execution_candles=list(execution_candles),
            one_lot_loss=lambda *_: 100.0, daily_used_cash=kwargs.get("used", 0),
            drawdown_percent=kwargs.get("dd", 0), journal_healthy=kwargs.get("healthy", True),
            trades_taken_this_session=kwargs.get("taken", 0),
            news_events=kwargs.get("news_events"),
            news_calendar_available=kwargs.get("news_calendar_available", True))

    # ---------------------------------------------------------------- time model
    def test_asian_session_window_is_midnight_to_0700_utc(self):
        # CORRECTED 2026-08-22: the session window is 00:00-07:00 UTC / 28 bars.
        # The prior 22:00-07:00 / 36 bar window was superseded on 2026-08-15.
        start, end = session_bounds(TRADING_DATE, self.config)
        self.assertEqual(start, datetime(2026, 8, 11, 0, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 8, 11, 7, tzinfo=timezone.utc))
        self.assertEqual((end - start).total_seconds() / 3600, 7.0)
        self.assertEqual(end.date(), TRADING_DATE)

    def test_execution_window_runs_through_the_london_session(self):
        start, end = execution_bounds(TRADING_DATE, self.config)
        self.assertEqual(start, datetime(2026, 8, 11, 7, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 8, 11, 16, tzinfo=timezone.utc))

    def test_configured_candle_counts_match_the_windows(self):
        self.assertEqual(self.config.strategy_id, "ASIAN_SESSION_V1")
        self.assertEqual(self.config.contract_version, "1.0")
        self.assertEqual(self.config.system["engine_version"], "v1.0")
        self.assertTrue(self.config.system["supersede_legacy"])
        # CORRECTED 2026-08-22: 00:00-07:00 / 28 M15 session bars.
        self.assertEqual(self.config.session_candles, 28)
        self.assertEqual(self.config.timeframe, "M15")
        self.assertEqual(self.config.expected_session_candles, 28)
        self.assertEqual(self.config.post_session_candles, 36)
        self.assertEqual(self.config.expected_post_session_candles, 36)

    def test_broker_clock_is_normalized_to_utc(self):
        now = datetime(2026, 8, 11, 7, 30, tzinfo=timezone.utc)
        ok, offset, age = calibrate_broker_tick(now, now.timestamp() + 3 * 3600 - 2, 3)
        self.assertTrue(ok)
        self.assertEqual(offset, 3)
        self.assertAlmostEqual(age, 2)

    # ------------------------------------------------------------------ validation
    def test_missing_and_duplicated_candles_are_rejected(self):
        bars = range_session()
        self.assertTrue(validate_candles(bars, ASIAN_START, 28, self.config)[0])
        self.assertFalse(validate_candles(bars[:27], ASIAN_START, 28)[0])
        duped = bars[:10] + [bars[9]] + bars[10:27]
        self.assertFalse(validate_candles(duped, ASIAN_START, 28, self.config)[0])

    def test_empty_execution_window_is_valid(self):
        self.assertTrue(validate_candles([], EXEC_START, 36, minimum_count=0)[0])

    # ---------------------------------------------------------------------- levels
    def test_locked_levels_match_the_specification(self):
        levels = lock_asian_levels(range_session(), self.config)
        self.assertAlmostEqual(levels.high, HIGH)
        self.assertAlmostEqual(levels.low, LOW)
        self.assertAlmostEqual(levels.range, RANGE)
        self.assertAlmostEqual(levels.midpoint, LOW + 0.5 * RANGE)
        self.assertAlmostEqual(levels.risk_unit, R)
        self.assertAlmostEqual(levels.lower_quartile, LOW + 0.25 * RANGE)
        self.assertAlmostEqual(levels.upper_quartile, HIGH - 0.25 * RANGE)
        self.assertAlmostEqual(levels.midpoint_zone_low, LOW + 0.45 * RANGE)
        self.assertAlmostEqual(levels.midpoint_zone_high, LOW + 0.55 * RANGE)

    def test_levels_are_immutable_against_post_lock_candles(self):
        session = range_session()
        before = lock_asian_levels(session, self.config)
        result = self.run_analysis(session, [execution(0, 1.16500, 1.20000, 1.10000, 1.16500)])
        self.assertAlmostEqual(result.asian_high, before.high)
        self.assertAlmostEqual(result.asian_low, before.low)

    # -------------------------------------------------------------- classification
    def test_range_and_trend_and_uncertain_classification(self):
        self.assertEqual(classify_session(lock_asian_levels(range_session(), self.config), self.config), "RANGE")
        self.assertEqual(classify_session(lock_asian_levels(trend_session(), self.config), self.config), "BULLISH_TREND")
        # High efficiency but a close in the middle -> neither trend nor range.
        levels = lock_asian_levels(range_session(close=1.16600), self.config)
        uncertain = replace(levels, efficiency_ratio=0.90, close_location=0.50)
        self.assertEqual(classify_session(uncertain, self.config), "UNCERTAIN")

    def test_uncertain_session_produces_no_trade(self):
        session = range_session()
        strict = replace(self.config, classification={**self.config.classification,
                         "efficiency_ratio_threshold": 0.0, "close_location_trend": 0.99})
        result = self.run_analysis(session, config=strict)
        self.assertEqual(result.session_type, "UNCERTAIN")
        self.assertEqual(result.status, "NO_TRADE")
        self.assertIn(Reason.UNCERTAIN_SESSION_TYPE, result.reason_codes)

    # --------------------------------------------------------------- sweep setup
    def test_sweep_body_entry_resolves_the_old_structural_conflict(self):
        levels = lock_asian_levels(range_session(), self.config)
        candle = execution(0, 1.16400, 1.16460, 1.16330, 1.16450)
        self.assertIsNotNone(detect_sweep(candle, levels, self.config))
        result = self.run_analysis(range_session(), [candle])
        self.assertEqual(result.setup, "SWEEP")
        self.assertAlmostEqual(result.entry, 1.16400, places=5)
        self.assertAlmostEqual(result.stop_loss, 1.16300, places=5)
        gate = next(g for g in result.gates if g.name == "G11_STRUCTURAL_STOP")
        self.assertTrue(gate.passed)
        self.assertEqual(result.status, "SIGNAL_ACCEPTED")

    def test_sweep_with_a_protected_stop_is_accepted_with_4r_and_5r_targets(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle])
        self.assertEqual((result.setup, result.direction), ("SWEEP", "LONG"))
        self.assertAlmostEqual(result.entry, 1.16400, places=5)
        self.assertAlmostEqual(result.stop_loss, 1.16300, places=5)
        self.assertAlmostEqual(result.initial_risk, R, places=6)
        self.assertAlmostEqual(result.partial_target, HIGH, places=5)
        self.assertEqual(result.partial_target_label, "opposite session boundary")
        self.assertEqual(result.runner_management, "MOVE_STOP_TO_BREAKEVEN")
        self.assertAlmostEqual(result.tp2_5r, result.entry + 5 * R, places=5)
        self.assertEqual(result.status, "SIGNAL_ACCEPTED")
        for code in (Reason.SELL_SIDE_SWEEP, Reason.CLOSE_BACK_INSIDE, Reason.STRUCTURAL_STOP_VALID):
            self.assertIn(code, result.reason_codes)

    def test_bearish_sweep_mirrors_the_bullish_rule(self):
        candle = execution(0, 1.16800, 1.16900, 1.16770, 1.16790)
        levels = lock_asian_levels(range_session(), self.config)
        signal = detect_sweep(candle, levels, self.config)
        self.assertEqual(signal["direction"], "SHORT")

    def test_wick_outside_but_close_outside_is_not_a_sweep(self):
        levels = lock_asian_levels(range_session(), self.config)
        broke_out = execution(0, 1.16400, 1.16420, 1.16300, 1.16350)   # closed below the low
        self.assertIsNone(detect_sweep(broke_out, levels, self.config))
        self.assertIsNone(detect_range_rejection(broke_out, levels, self.config))

    # ----------------------------------------------------- range rejection setup
    def test_boundary_touch_without_rejection_is_not_a_signal(self):
        levels = lock_asian_levels(range_session(), self.config)
        bearish_at_low = execution(0, 1.16430, 1.16440, 1.16405, 1.16410)
        self.assertIsNone(detect_range_rejection(bearish_at_low, levels, self.config))

    def test_outside_open_reentry_is_not_a_new_range_rejection(self):
        levels = lock_asian_levels(range_session(), self.config)
        outside_reentry = execution(0, 1.16370, 1.16520, 1.16360, 1.16480)
        self.assertIsNone(detect_range_rejection(outside_reentry, levels, self.config))

    def test_range_rejection_requires_a_bullish_close_off_the_low(self):
        candle = execution(0, 1.16410, 1.16460, 1.16405, 1.16450)
        result = self.run_analysis(range_session(), [candle])
        self.assertEqual(result.directional_bias, "BEARISH")
        self.assertEqual((result.setup, result.direction), ("RANGE_REJECTION", "LONG"))
        self.assertAlmostEqual(result.entry, LOW, places=5)
        self.assertAlmostEqual(result.partial_target, HIGH, places=5)
        self.assertAlmostEqual(result.stop_loss, result.entry - R, places=5)
        self.assertIn(Reason.BOUNDARY_REJECTION, result.reason_codes)

    def test_sweep_takes_priority_over_range_rejection(self):
        sweep = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [sweep])
        self.assertEqual(result.setup, "SWEEP")

    # -------------------------------------------------------- trend continuation
    def test_trend_continuation_needs_a_confirmed_midpoint_retracement(self):
        session = trend_session()
        away = execution(0, 1.16750, 1.16780, 1.16740, 1.16770)
        self.assertEqual(self.run_analysis(session, [away]).setup, "NONE")
        retrace = execution(1, 1.16580, 1.16640, 1.16570, 1.16630)
        result = self.run_analysis(session, [retrace])
        self.assertEqual(result.session_type, "BULLISH_TREND")
        self.assertEqual((result.setup, result.direction), ("TREND_CONTINUATION", "LONG"))
        self.assertAlmostEqual(result.entry, (HIGH + LOW) / 2, places=5)
        self.assertAlmostEqual(result.partial_target, result.entry + 4 * R, places=5)
        self.assertEqual(result.runner_management, "MOVE_STOP_TO_BREAKEVEN; RUNNER_TARGET_5R")
        self.assertIn(Reason.MIDPOINT_RETRACEMENT, result.reason_codes)

    def test_high_impact_news_blocks_only_the_relevant_symbol_window(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        event = {"time_utc": "2026-08-11T09:00:00Z", "currency": "USD", "impact": "HIGH"}
        blocked = self.run_analysis(range_session(), [candle],
                                    now=datetime(2026, 8, 11, 8, 45, tzinfo=timezone.utc),
                                    news_events=[event])
        self.assertIn(Reason.HIGH_IMPACT_NEWS_WINDOW, blocked.reason_codes)
        self.assertEqual(blocked.status, "NO_TRADE")

    def test_unavailable_news_calendar_fails_closed(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle], news_calendar_available=False)
        self.assertIn(Reason.NEWS_CALENDAR_UNAVAILABLE, result.reason_codes)
        self.assertEqual(result.status, "NO_TRADE")

    def test_trend_setup_is_cancelled_by_an_opposite_quartile_violation(self):
        session = trend_session()
        breakdown = execution(0, 1.16540, 1.16550, 1.16490, 1.16520)
        retrace = execution(1, 1.16580, 1.16640, 1.16570, 1.16630)
        result = self.run_analysis(session, [breakdown, retrace])
        self.assertEqual(result.setup, "NONE")
        self.assertTrue(any("cancelled" in w for w in result.warnings))

    # ------------------------------------------------------------------- risk
    def test_position_size_uses_half_a_percent_of_lower_balance_or_equity(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle])
        self.assertAlmostEqual(result.intended_risk_cash, 1000 * 0.005)
        self.assertEqual(result.volume, 0.05)      # 5.00 / 100.0, floored to 0.01
        self.assertAlmostEqual(result.risk_fraction, 0.005)
        reduced = self.run_analysis(
            range_session(), [candle],
            account=replace(account(), balance=800, equity=900),
        )
        self.assertEqual(reduced.risk_basis_cash, 800)
        self.assertAlmostEqual(reduced.intended_risk_cash, 4.0)
        self.assertAlmostEqual(reduced.actual_risk_percent, 0.5)

    def test_dual_boundary_sweep_is_directionally_ambiguous(self):
        candle = execution(0, 1.16600, 1.16900, 1.16300, 1.16600)
        self.assertIsNone(detect_sweep(candle, lock_asian_levels(range_session(), self.config),
                                       self.config))

    def test_real_account_daily_risk_and_drawdown_all_fail_closed(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle],
                                   account=account("real"), used=21, dd=16)
        failed = {g.name for g in result.gates if not g.passed}
        self.assertTrue({"G1_ENVIRONMENT", "G14_DAILY_RISK", "G15_DRAWDOWN"} <= failed)
        self.assertEqual(result.status, "NO_TRADE")

    def test_unhealthy_journal_fails_risk_gates_closed(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle], healthy=False)
        failed = {g.name for g in result.gates if not g.passed}
        self.assertTrue({"G14_DAILY_RISK", "G15_DRAWDOWN"} <= failed)

    def test_one_trade_per_symbol_per_session(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle], taken=1)
        gate = next(g for g in result.gates if g.name == "G8_SESSION_QUOTA")
        self.assertFalse(gate.passed)
        self.assertIn(Reason.TRADE_ALREADY_TAKEN, result.reason_codes)
        self.assertIn(Reason.MAX_SESSION_TRADES_EXCEEDED, result.reason_codes)

    def test_excessive_spread_is_rejected(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle],
                                   tick={"bid": 1.16400, "ask": 1.16500})
        gate = next(g for g in result.gates if g.name == "G6_SPREAD")
        self.assertFalse(gate.passed)
        self.assertIn(Reason.EXCESSIVE_SPREAD, result.reason_codes)

    def test_range_outside_configured_bounds_is_rejected(self):
        tiny = [asian(i, 1.16600, 1.16605, 1.16595, 1.16600) for i in range(28)]
        result = self.run_analysis(tiny)
        gate = next(g for g in result.gates if g.name == "G5_RANGE_BOUNDS")
        self.assertFalse(gate.passed)
        self.assertIn(Reason.INVALID_ASIAN_RANGE, result.reason_codes)

    def test_outside_execution_window_is_rejected(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        late = datetime(2026, 8, 11, 16, 30, tzinfo=timezone.utc)
        result = self.run_analysis(range_session(), [candle], now=late)
        gate = next(g for g in result.gates if g.name == "G16_EXECUTION_WINDOW")
        self.assertFalse(gate.passed)
        self.assertEqual(result.status, "NO_TRADE")

    def test_stale_tick_fails_session_data(self):
        stale = datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc).timestamp()
        result = self.run_analysis(range_session(), tick_time=stale)
        self.assertFalse(next(g for g in result.gates if g.name == "G3_BROKER_CLOCK").passed)
        self.assertEqual(result.status, "NO_TRADE")

    # ----------------------------------------- ASIAN_SESSION_V1 contract hardening
    def test_half_open_window_filter_excludes_the_closing_bar(self):
        bars = range_session() + [execution(0, 1.16500, 1.16510, 1.16490, 1.16500)]
        kept = filter_window(bars, ASIAN_START, EXEC_START)
        self.assertEqual(len(kept), 28)
        self.assertTrue(all(c.time < EXEC_START for c in kept))
        self.assertEqual(len(filter_window(bars, EXEC_START, EXEC_START + timedelta(hours=9))), 1)

    def test_unclosed_or_future_bars_are_rejected(self):
        bars = range_session()
        mid_bar = bars[-1].time + timedelta(minutes=5)   # the last bar has not closed yet
        ok, detail = validate_candles(bars, ASIAN_START, 28, self.config, now=mid_bar)
        self.assertFalse(ok)
        self.assertIn("unclosed", detail)

    def test_non_positive_ohlc_is_rejected(self):
        bars = range_session()
        bars[3] = asian(3, 1.16600, 1.16650, 0.0, 1.16600)
        self.assertFalse(validate_candles(bars, ASIAN_START, 28, self.config)[0])

    def test_logical_symbol_maps_to_the_broker_symbol(self):
        self.assertEqual(self.config.broker_symbol("XAUUSD"), "XAUUSD.crp")
        self.assertEqual(self.config.broker_symbol("EURUSD"), "EURUSD")
        self.assertNotIn("XAUUSD.crp", self.config.symbols)
        self.assertEqual(self.config.resolve_symbol("XAUUSD.crp"), "XAUUSD")

    def test_suffix_only_account_matching_records_a_warning(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle])
        gate = next(g for g in result.gates if g.name == "G1_ENVIRONMENT")
        self.assertTrue(gate.passed)
        self.assertIn("suffix fallback", gate.detail)
        self.assertTrue(any("suffix only" in w for w in result.warnings))

    def test_login_allowlist_rejects_a_matching_suffix_from_another_account(self):
        # Masking is length-sensitive, so an allowlisted login of a different length
        # is also rejected — that is intentional extra strength.
        guarded = replace(self.config, account_guard={**self.config.account_guard,
                                                      "allowed_logins": [1234985]})
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        ok = self.run_analysis(range_session(), [candle], config=guarded)
        self.assertTrue(next(g for g in ok.gates if g.name == "G1_ENVIRONMENT").passed)
        other = self.run_analysis(range_session(), [candle], config=guarded,
                                  account=AccountSnapshot("****111", "demo", 1000, 1000,
                                                          "VTMarkets-Demo", True, True, 10))
        self.assertFalse(next(g for g in other.gates if g.name == "G1_ENVIRONMENT").passed)
        self.assertIn(Reason.ACCOUNT_NOT_ALLOWLISTED, other.reason_codes)

    def test_runner_below_broker_minimum_is_flagged(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        # volume 0.05, 25% runner = 0.0125 -> floors to 0.01, at the minimum: fine.
        fine = self.run_analysis(range_session(), [candle])
        self.assertFalse(fine.runner_below_minimum)
        self.assertAlmostEqual(fine.partial_volume + fine.runner_volume, fine.volume, places=8)
        # A coarser step leaves no tradeable runner.
        coarse = SymbolSpec("EURUSD", 5, .00001, .00001, .05, 100, .05, 0)
        tight = analyze(config=self.config, symbol="EURUSD", trading_date=TRADING_DATE,
                        now=datetime(2026, 8, 11, 8, 45, tzinfo=timezone.utc), account=account(),
                        spec=coarse,
                        tick={"bid": 1.16499, "ask": 1.16501,
                              "time": datetime(2026, 8, 11, 8, 45, tzinfo=timezone.utc).timestamp(),
                              "broker_offset_hours": 0},
                        session_candles=range_session(), execution_candles=[candle],
                        one_lot_loss=lambda *_: 100.0, daily_used_cash=0, drawdown_percent=0,
                        journal_healthy=True)
        self.assertTrue(tight.runner_below_minimum)
        self.assertIn(Reason.RUNNER_BELOW_MINIMUM_VOLUME, tight.reason_codes)

    def test_costs_reduce_the_reported_r_multiples(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        result = self.run_analysis(range_session(), [candle])
        self.assertIsNotNone(result.estimated_cost_r)
        self.assertGreater(result.estimated_cost_r, 0)
        self.assertLess(result.net_tp2_r, result.gross_tp2_r)
        self.assertAlmostEqual(result.gross_tp2_r - result.net_tp2_r, result.estimated_cost_r, places=9)
        self.assertFalse(any("Cost model is not signed off" in w for w in result.warnings))

    def test_disabling_a_setup_removes_it_from_detection(self):
        candle = execution(0, 1.16410, 1.16460, 1.16405, 1.16450)   # a range rejection
        self.assertEqual(self.run_analysis(range_session(), [candle]).setup, "RANGE_REJECTION")
        rules = dict(self.config.setup_rules)
        rules["RANGE_REJECTION"] = replace(rules["RANGE_REJECTION"], enabled=False)
        off = replace(self.config, setup_rules=rules)
        self.assertEqual(self.run_analysis(range_session(), [candle], config=off).setup, "NONE")

    def test_execution_permissions_are_all_denied(self):
        for permission in ("submit_orders", "modify_orders", "close_positions"):
            if self.config.mode == "analysis_only":
                self.assertFalse(self.config.execution_permissions[permission])
            else:
                self.assertTrue(self.config.execution_permissions[permission])

    def test_governance_approves_stage_2_baseline_and_locks_optimization(self):
        self.assertEqual(
            self.config.governance["specification_status"],
            "APPROVED_FOR_STAGE_2_BASELINE",
        )
        self.assertFalse(self.config.governance["optimization_allowed"])
        self.assertEqual(
            self.config.governance["parameter_signoff"]["config_hash"],
            self.config.signoff_hash,
        )
        self.assertFalse(self.config.governance["live_execution_authorized"])
        self.assertIn("sweep_buffer_fraction", self.config.governance["provisional_parameters"])

    # ------------------------------------------------------------- determinism
    def test_identical_inputs_produce_identical_output(self):
        candle = execution(0, 1.16400, 1.16440, 1.16330, 1.16410)
        first, second = (self.run_analysis(range_session(), [candle]).to_dict() for _ in range(2))
        for payload in (first, second):
            payload.pop("analysis_id")
            payload.pop("timestamp_utc")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
