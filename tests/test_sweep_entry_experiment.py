import datetime as dt
import unittest

from scripts.sweep_entry_experiment import find_sweep_signal, reference_levels


def bar(minute, o, h, l, c):
    return {"t": dt.datetime(2022, 10, 3) + dt.timedelta(minutes=minute),
            "o": o, "h": h, "l": l, "c": c}


def reference():
    rows = [bar(i * 15, 1.002, 1.008, 1.000, 1.006) for i in range(32)]
    rows[0] = bar(0, 1.004, 1.006, 1.000, 1.004)
    rows[-1] = bar(465, 1.004, 1.010, 1.003, 1.004)  # midpoint -> SHORT convention
    return rows


class SweepEntryExperimentTests(unittest.TestCase):
    def test_reference_requires_exactly_32_bars(self):
        with self.assertRaisesRegex(ValueError, "expected 32"):
            reference_levels(reference()[:-1])

    def test_clearance_rejects_borderline_reclaim_then_accepts_clean_one(self):
        ref = reference()
        ex = [bar(480, 1.009, 1.011, 1.008, 1.0099),
              bar(495, 1.0099, 1.012, 1.008, 1.008)]
        sig = find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                "SWEEP_CLOSE_ENTRY", 0.025)
        self.assertEqual(sig.normalized_timestamp_utc, "2022-10-03T08:15Z")

    def test_structural_gate_uses_extreme_known_at_entry(self):
        ref = reference()
        ex = [bar(480, 1.009, 1.011, 1.006, 1.008)]
        sig = find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                "SWEEP_CLOSE_ENTRY", 0.025)
        self.assertEqual(sig.status, "REJECTED")
        self.assertEqual(sig.reason_code, "FIXED_RISK_SL_INSIDE_SWEEP_EXTREME")

    def test_future_extreme_cannot_change_earlier_signal(self):
        ref = reference()
        first = bar(480, 1.009, 1.0105, 1.006, 1.008)
        later = bar(495, 1.008, 1.020, 1.007, 1.019)
        a = find_sweep_signal(dt.datetime(2022, 10, 3), ref, [first],
                              "SWEEP_CLOSE_ENTRY", 0.025)
        b = find_sweep_signal(dt.datetime(2022, 10, 3), ref, [first, later],
                              "SWEEP_CLOSE_ENTRY", 0.025)
        self.assertEqual(a, b)

    def test_confirmation_variant_enters_on_next_directional_close(self):
        ref = reference()
        ex = [bar(480, 1.009, 1.0105, 1.006, 1.008),
              bar(495, 1.008, 1.0085, 1.005, 1.006)]
        sig = find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                "POST_SWEEP_CONFIRMATION_ENTRY", 0.025)
        self.assertEqual(sig.entry, 1.006)
        self.assertEqual(sig.normalized_timestamp_utc, "2022-10-03T08:15Z")
        self.assertEqual(sig.source_timestamp_broker, "2022-10-03T11:15")
        self.assertEqual(sig.confirmation_time_utc, "2022-10-03T08:15Z")

    def test_required_structural_risk_is_range_normalized(self):
        ref = reference()
        ex = [bar(480, 1.009, 1.011, 1.006, 1.008)]
        sig = find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                "SWEEP_CLOSE_ENTRY", 0.025)
        # Range is 0.010; short requires 0.003 from entry to known extreme.
        self.assertAlmostEqual(sig.required_structural_risk_pct, 0.30)
        self.assertEqual(sig.setup_status, "DETECTED")
        self.assertEqual(sig.entry_status, "REJECTED")
        self.assertEqual(sig.all_failed_gates,
                         ("FIXED_RISK_SL_INSIDE_SWEEP_EXTREME",))
        self.assertEqual(sig.source_timezone, "BROKER_SERVER")
        self.assertEqual(sig.reference_start_utc, "2022-10-03T00:00Z")
        self.assertEqual(sig.reference_end_utc, "2022-10-03T08:00Z")
        self.assertEqual(sig.reference_start_broker, "2022-10-03T03:00")
        self.assertEqual(sig.reference_end_broker, "2022-10-03T11:00")
        self.assertEqual(sig.attack_start_time_utc, "2022-10-03T08:00Z")
        self.assertEqual(sig.signal_time_utc, sig.order_time_utc)
        self.assertEqual(sig.order_time_utc, sig.fill_time_utc)

    def test_confirmation_bar_adverse_extreme_is_known_at_entry(self):
        ref = reference()
        ex = [bar(480, 1.009, 1.0105, 1.006, 1.008),
              bar(495, 1.008, 1.013, 1.005, 1.006)]
        sig = find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                "POST_SWEEP_CONFIRMATION_ENTRY", 0.025)
        self.assertEqual(sig.sweep_extreme, 1.013)
        self.assertEqual(sig.sweep_extreme_time_utc, "2022-10-03T08:15Z")

    def test_direction_filter_does_not_substitute_the_other_side(self):
        ref = reference()
        ex = [bar(480, 1.009, 1.0105, 1.006, 1.008)]
        self.assertIsNone(find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                            "SWEEP_CLOSE_ENTRY", 0.025, "LONG"))
        self.assertEqual(find_sweep_signal(dt.datetime(2022, 10, 3), ref, ex,
                                           "SWEEP_CLOSE_ENTRY", 0.025, "SHORT").direction,
                         "SHORT")


if __name__ == "__main__":
    unittest.main()
