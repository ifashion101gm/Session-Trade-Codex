from datetime import date, datetime, timedelta, timezone
import csv
import json
from pathlib import Path
import unittest

from asian_session_backtester import (Bar, END, MAX_TRADES_PER_SESSION,
                                      MINIMUM_ASIAN_RANGE_PIPS,
                                      MOMENTUM_BODY_MULTIPLIER,
                                      POST_LOSS_COOLDOWN_BARS,
                                      RANGE_EFFICIENCY_RATIO_MAX, SESSION_CYCLES, START,
                                      classify, directional_bias, m15_structure_bias,
                                      daily_bias_cutoff,
                                      modeled_spread_pips, opposing_expansion,
                                      parse_target_dates, signal_for, trading_days)


class RealignedAsianBacktesterContractTests(unittest.TestCase):
    def test_developing_london_low_reclaim_is_carried_as_long_sweep(self):
        from asian_session_backtester import developing_session_sweep
        start = datetime(2022, 10, 19, 7, 0, tzinfo=timezone.utc)
        bars = [
            Bar(start + timedelta(minutes=15*i), *ohlc, 0)
            for i, ohlc in enumerate([
                (.9822, .9830, .9818, .9826),
                (.9826, .9834, .9822, .9830),
                (.9830, .9839, .9828, .9837),
                (.9837, .9838, .9827, .9830),
                (.9830, .9831, .9819, .9822),
                (.9822, .9824, .9817, .9819),
                (.9819, .9821, .9815, .9818),
                (.9818, .9820, .9813, .9816),
                (.9816, .9819, .9811, .9814),
                (.9814, .9817, .9809, .9811),
                (.9811, .9814, .9807, .9809),
                (.9809, .9812, .9805, .9807),
                (.9807, .9810, .9803, .9805),
                (.9805, .9808, .9801, .9803),
                (.9803, .9805, .9799, .9801),
                (.9801, .9803, .9797, .9799),
                (.9799, .9801, .9795, .9797),
                (.9797, .9799, .9793, .9795),
                (.9795, .9797, .9791, .9793),
                (.9793, .9800, .9789, .9798),
            ])
        ]
        index, setup, direction, entry = developing_session_sweep(bars)
        self.assertEqual((index, setup, direction), (19, "SWEEP", "LONG"))
        self.assertAlmostEqual(entry, .9793)


    def test_classifier_uses_net_move_over_range_not_path_length(self):
        when = datetime(2022, 10, 12, 0, tzinfo=timezone.utc)
        closes = [1.0010, 1.0040, 1.0020, 1.0060, 1.0040, 1.0080]
        bars = [Bar(when + timedelta(minutes=15*i),
                    1.0000 if i == 0 else closes[i-1], 1.0100, 1.0000,
                    close, 0) for i, close in enumerate(closes)]
        self.assertEqual(classify(bars, 1.0100, 1.0000), "BULLISH_TREND")

    def test_classifier_returns_range_at_the_035_boundary(self):
        when = datetime(2022, 10, 12, 0, tzinfo=timezone.utc)
        bar = Bar(when, 1.0000, 1.0100, 1.0000, 1.0035, 0)
        self.assertEqual(classify([bar], 1.0100, 1.0000), "RANGE")

    def test_classifier_returns_bearish_trend_from_close_geometry(self):
        when = datetime(2022, 10, 12, 0, tzinfo=timezone.utc)
        bar = Bar(when, 1.0100, 1.0100, 1.0000, 1.0020, 0)
        self.assertEqual(classify([bar], 1.0100, 1.0000, "BULLISH"),
                         "BEARISH_TREND")

    def test_classifier_returns_uncertain_when_close_is_not_in_outer_quartile(self):
        when = datetime(2022, 10, 12, 0, tzinfo=timezone.utc)
        bar = Bar(when, 1.0000, 1.0100, 1.0000, 1.0060, 0)
        self.assertEqual(classify([bar], 1.0100, 1.0000), "UNCERTAIN")

    def test_trend_midpoint_retracement_requires_directional_confirmation(self):
        when = datetime(2022, 10, 21, 12, 45, tzinfo=timezone.utc)
        bullish_touch = Bar(when, .97650, .97720, .97640, .97700, 0)
        self.assertIsNone(signal_for("BEARISH_TREND", [bullish_touch], .98025,
                                     .97323, .97451, bias="BEARISH"))
        bearish_confirmation = Bar(when, .97700, .97720, .97640, .97650, 0)
        result = signal_for("BEARISH_TREND", [bearish_confirmation], .98025,
                            .97323, .97451, bias="BEARISH")
        self.assertEqual(result[:3], (0, "TREND", "SHORT"))
        self.assertAlmostEqual(result[3], .97674)

    def test_short_sweep_requires_dominant_upper_wick(self):
        expansion = Bar(datetime(2022, 10, 3, 15, 0, tzinfo=timezone.utc),
                        0.98137, 0.98369, 0.98128, 0.98342, 0)
        rejection = Bar(datetime(2022, 10, 3, 15, 15, tzinfo=timezone.utc),
                        0.98341, 0.98447, 0.98313, 0.98342, 0)
        result = signal_for("RANGE", [expansion, rejection], 0.98344,
                            0.97843, 0.97976, bias="BEARISH")
        self.assertEqual(result, (1, "SWEEP", "SHORT", 0.98342))

    def test_reclaim_keeps_sweep_precedence_until_aligned_confirmation(self):
        when = datetime(2022, 10, 12, 14, 15, tzinfo=timezone.utc)
        opposing_reclaim = Bar(when, .96950, .96973, .96815, .96865, 0)
        outside_close = Bar(when, .96864, .96983, .96728, .96733, 0)
        aligned_reclaim = Bar(when, .96835, .97060, .96678, .97013, 0)
        self.assertEqual(
            signal_for("RANGE", [opposing_reclaim, outside_close, aligned_reclaim],
                       .97343, .96826, .97215, bias="BULLISH"),
            (2, "SWEEP", "LONG", .96835),
        )

    def test_swept_boundary_can_trigger_counter_bias_sweep(self):
        when = datetime(2022, 10, 14, 7, 15, tzinfo=timezone.utc)
        low_reclaim = Bar(when, .97720, .97723, .97525, .97624, 0)
        self.assertEqual(
            signal_for("RANGE", [low_reclaim], .98082, .97617, .97800,
                       bias="BEARISH"),
            (0, "SWEEP", "LONG", .97624),
        )

    def test_sub_pip_boundary_noise_does_not_displace_range_setup(self):
        when = datetime(2022, 10, 21, 7, 0, tzinfo=timezone.utc)
        token_low_breach = Bar(when, 1.0004, 1.0010, .99993, 1.0005, 0)
        resistance_touch = Bar(when + timedelta(minutes=15), 1.0018,
                               1.0020, 1.0004, 1.0006, 0)
        self.assertEqual(
            signal_for("RANGE", [token_low_breach, resistance_touch],
                       1.0020, 1.0000, 1.0005, bias="BEARISH"),
            (1, "RANGE", "SHORT", 1.0020),
        )

    def test_selected_sweep_branch_disables_later_range_fallback(self):
        when = datetime(2022, 10, 14, 9, 30, tzinfo=timezone.utc)
        bearish_break = Bar(when, .97282, .97322, .97188, .97198, 0)
        self.assertIsNone(
            signal_for("RANGE", [bearish_break], .98082, .97617, .97800,
                       bias="BEARISH", allow_range_setup=False)
        )
    def test_calendar_range_contains_fifteen_active_weekdays(self):
        self.assertEqual((START, END), (date(2022, 10, 1), date(2022, 10, 22)))
        self.assertEqual(len(trading_days()), 15)
        self.assertEqual((trading_days()[0], trading_days()[-1]),
                         (date(2022, 10, 3), date(2022, 10, 21)))

    def test_realignments_are_explicit_constants(self):
        self.assertEqual(MAX_TRADES_PER_SESSION, 3)
        self.assertEqual(MINIMUM_ASIAN_RANGE_PIPS, 10.0)
        self.assertEqual(POST_LOSS_COOLDOWN_BARS, 4)
        self.assertEqual(MOMENTUM_BODY_MULTIPLIER, 1.5)
        self.assertEqual(RANGE_EFFICIENCY_RATIO_MAX, .35)

    def test_bias_does_not_disable_official_range_state(self):
        when = datetime(2022, 10, 3, tzinfo=timezone.utc)
        rising = [Bar(when, 1.0, 1.02, .99, 1.005, 0)]
        self.assertEqual(directional_bias(rising), "BULLISH")
        self.assertEqual(classify(rising, 1.02, .99), "RANGE")

    def test_m15_bias_is_neutral_without_confirmed_swings(self):
        cutoff = datetime(2022, 10, 3, 7, tzinfo=timezone.utc)
        flat = [Bar(cutoff, 1.0, 1.01, .99, 1.0, 0)] * 10
        self.assertEqual(m15_structure_bias(flat, cutoff), "NEUTRAL")

    def test_m15_bias_uses_strong_four_swing_majority_over_one_pullback(self):
        cutoff = datetime(2022, 10, 13, 10, tzinfo=timezone.utc)
        highs = [9, 10, 8, 11, 9, 12, 10, 13, 11, 12]
        lows = [6, 7, 5, 8, 6, 9, 7, 9, 6.5, 8]
        bars = [Bar(cutoff-timedelta(minutes=15*(10-i)), 7.5, highs[i],
                    lows[i], 7.5, 0) for i in range(10)]
        self.assertEqual(m15_structure_bias(bars, cutoff), "BULLISH")

    def test_dynamic_spread_curve(self):
        stamp = lambda hour, minute=0: datetime(2022, 10, 3, hour, minute,
                                                tzinfo=timezone.utc)
        self.assertEqual(modeled_spread_pips(stamp(7)), 1.0)
        self.assertEqual(modeled_spread_pips(stamp(12)), 1.0)
        self.assertEqual(modeled_spread_pips(stamp(10)), 0.4)
        self.assertGreaterEqual(modeled_spread_pips(stamp(7, 15)), 0.4)
        self.assertLessEqual(modeled_spread_pips(stamp(7, 15)), 0.7)
        self.assertGreaterEqual(modeled_spread_pips(stamp(16, 45)), 0.4)
        self.assertLessEqual(modeled_spread_pips(stamp(16, 45)), 0.7)
        self.assertEqual(modeled_spread_pips(stamp(20)), 1.2)

    def test_target_dates_preserve_order_and_remove_duplicates(self):
        self.assertEqual(parse_target_dates("2022-10-17, 2022-10-03,2022-10-17"),
                         [date(2022, 10, 17), date(2022, 10, 3)])

    def test_opposing_expansion_uses_prior_bodies_only(self):
        when = datetime(2022, 10, 3, 8, tzinfo=timezone.utc)
        prior = [Bar(when, 1.0, 1.0002, .9998, 1.0001, 0) for _ in range(4)]
        bearish = Bar(when, 1.0010, 1.0011, .9990, 1.0000, 0)
        rejected, body, average, upper, lower = opposing_expansion(bearish, "LONG", prior)
        self.assertFalse(rejected)
        self.assertGreater(body, 1.5 * average)
        self.assertGreater(lower, .35)
        self.assertFalse(opposing_expansion(bearish, "SHORT", prior)[0])

    def test_wide_range_rejects_breakout_and_accepts_reclaimed_sweep(self):
        when = datetime(2022, 10, 3, 9, 30, tzinfo=timezone.utc)
        breakout = Bar(when, .9785, .9790, .9782, .9783, 0)
        reclaimed = Bar(when, .9785, .9790, .9782, .9786, 0)
        self.assertIsNone(signal_for("RANGE", [breakout], .9834, .9784, .9800,
                                     "limit", True))
        self.assertEqual(signal_for("RANGE", [reclaimed], .9834, .9784, .9800,
                                    "limit", True, "BULLISH"),
                         (0, "SWEEP", "LONG", .9785))

    def test_source_workflow_sweep_prices_are_exact_quarter_range_and_5r(self):
        asian_high, asian_low = .98344, .97843
        entry = .98342  # outer body edge of the confirmed short-sweep candle
        risk = .25 * (asian_high-asian_low)
        self.assertAlmostEqual(risk, .0012525)
        self.assertAlmostEqual(entry+risk, .9846725)
        self.assertAlmostEqual(entry-5*risk, .9771575)

    def test_session_cycles_are_causal(self):
        self.assertEqual(SESSION_CYCLES["asian"], (-2, 7))
        self.assertEqual(SESSION_CYCLES["london"], (7, 12))

    def test_daily_bias_is_frozen_at_asian_close_for_new_york(self):
        start = datetime(2022, 10, 11, tzinfo=timezone.utc)
        self.assertEqual(daily_bias_cutoff(start),
                         datetime(2022, 10, 11, 7, tzinfo=timezone.utc))

    def test_range_setup_requires_rejection_at_the_bias_aligned_boundary(self):
        when = datetime(2022, 10, 4, 8, tzinfo=timezone.utc)
        bearish_low_break = Bar(when, .9810, .9812, .9797, .9798, 0)
        self.assertIsNone(signal_for("RANGE", [bearish_low_break], .9872, .9800,
                                     .9840, bias="BEARISH"))
        bearish_top = Bar(when, .9871, .98725, .9860, .9864, 0)
        self.assertEqual(signal_for("RANGE", [bearish_top], .9872, .9800,
                                    .9840, bias="BEARISH"),
                         (0, "RANGE", "SHORT", .9872))
        bullish_bottom = Bar(when, .9804, .9812, .97995, .9810, 0)
        self.assertEqual(signal_for("RANGE", [bullish_bottom], .9872, .9800,
                                    .9840, bias="BULLISH"),
                         (0, "RANGE", "LONG", .9800))

    def test_oct03_bearish_range_flow_rejects_breakout_then_selects_short_sweep(self):
        day = datetime(2022, 10, 3, tzinfo=timezone.utc)
        low_breakout = Bar(day + timedelta(hours=9, minutes=30),
                           .9790, .9792, .9782, .9783, 0)
        outside_reentry = Bar(day + timedelta(hours=14),
                              .97677, .98146, .97677, .97938, 0)
        unconfirmed_high_reclaim = Bar(day + timedelta(hours=15),
                                       .98137, .98369, .98128, .98342, 0)
        confirmed_high_sweep = Bar(day + timedelta(hours=15, minutes=15),
                                   .98341, .98447, .98313, .98342, 0)
        self.assertEqual(
            signal_for("RANGE", [low_breakout, outside_reentry,
                                  unconfirmed_high_reclaim,
                                  confirmed_high_sweep],
                       .98344, .97843, .97976, bias="BEARISH"),
            (3, "SWEEP", "SHORT", .98342),
        )

    def test_range_breakout_partial_is_one_range_projection_or_4r(self):
        high, low = .99039, .98527
        risk = .25*(high-low)
        self.assertAlmostEqual(high+4*risk, high+(high-low))
        self.assertAlmostEqual(low-4*risk, low-(high-low))

    def test_user_confirmed_london_new_york_truth_fixture(self):
        fixture = json.loads(Path("benchmarks/truth_source_setups.json").read_text())
        london, new_york = fixture["benchmarks"][:2]
        self.assertEqual((london["reference_session"], london["execution_session"],
                          london["outcome"], london["target_r"]),
                         ("ASIAN", "LONDON", "TP5_HIT", 5.0))
        trade = new_york
        self.assertEqual(trade["status"], "USER_CONFIRMED_TRUTH")
        self.assertEqual((trade["reference_session"], trade["setup"], trade["direction"]),
                         ("LONDON", "SWEEP", "SHORT"))
        self.assertAlmostEqual(trade["stop"]-trade["entry"], .25*(.98273-.97526))
        self.assertAlmostEqual(trade["entry"]-trade["target_5r"],
                               5*(trade["stop"]-trade["entry"]))
        self.assertEqual((trade["outcome"], trade["gross_r"]), ("STOP_LOSS", -1.0))

    def test_entry_database_price_geometry(self):
        with Path("benchmarks/entry_database.csv").open(newline="") as handle:
            entries = list(csv.DictReader(handle))
        self.assertEqual(len(entries), 19)
        self.assertEqual(sum(row["active_contract_status"] == "CURRENT" for row in entries), 2)
        self.assertEqual(sum(row["active_contract_status"] == "REPLAY_REQUIRED" for row in entries), 17)
        current = [row for row in entries if row["active_contract_status"] == "CURRENT"]
        self.assertTrue(all((row["contract_version"], row["reference_window"]) ==
                            ("3.0", "22:00-07:00") for row in current))
        for trade in entries:
            entry, stop, target = map(float, (trade["entry"], trade["stop"],
                                              trade["target_5r"]))
            risk = abs(entry-stop)
            self.assertAlmostEqual(risk/.0001, float(trade["risk_pips"]), places=6)
            self.assertAlmostEqual(abs(target-entry), 5*risk, places=9)


if __name__ == "__main__":
    unittest.main()
