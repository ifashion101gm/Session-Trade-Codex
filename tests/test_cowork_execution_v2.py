import datetime as dt
import unittest

from session_strategy.cowork_execution_v2 import (
    M1BidAskBar, limit_entry_fill, protective_exit_stop_first,
    order_active_for_bar, stop_exit_fill, target_exit_fill,
)


def quote(**overrides):
    values = dict(open_time=dt.datetime(2022, 10, 3, 8, 16, tzinfo=dt.timezone.utc),
                  bid_open=1.1000, bid_high=1.1010, bid_low=1.0990,
                  ask_open=1.1002, ask_high=1.1012, ask_low=1.0992)
    values.update(overrides)
    return M1BidAskBar(**values)


class CoworkExecutionV2Tests(unittest.TestCase):
    def test_activation_and_expiry_are_half_open(self):
        signal_end = dt.datetime(2022, 10, 3, 8, 15, tzinfo=dt.timezone.utc)
        expiry = dt.datetime(2022, 10, 3, 16, 0, tzinfo=dt.timezone.utc)
        self.assertTrue(order_active_for_bar(signal_end, expiry, quote()))
        at_expiry = quote(open_time=expiry)
        self.assertFalse(order_active_for_bar(signal_end, expiry, at_expiry))
        overlapping = quote(open_time=signal_end - dt.timedelta(minutes=1))
        self.assertFalse(order_active_for_bar(signal_end, expiry, overlapping))

    def test_long_uses_ask_and_short_uses_bid(self):
        bar = quote()
        self.assertEqual(limit_entry_fill("LONG", 1.0995, bar), 1.0995)
        self.assertEqual(limit_entry_fill("SHORT", 1.1005, bar), 1.1005)

    def test_marketable_limit_gets_opening_improvement(self):
        bar = quote()
        self.assertEqual(limit_entry_fill("LONG", 1.1010, bar), 1.1002)
        self.assertEqual(limit_entry_fill("SHORT", 1.0995, bar), 1.1000)

    def test_stop_gap_is_adverse_and_target_gap_improves(self):
        long_gap = quote(bid_open=1.0970, bid_low=1.0965, bid_high=1.0980)
        self.assertEqual(stop_exit_fill("LONG", 1.0980, long_gap), 1.0970)
        short_target_gap = quote(ask_open=1.0970, ask_low=1.0965, ask_high=1.0980)
        self.assertEqual(target_exit_fill("SHORT", 1.0980, short_target_gap), 1.0970)

    def test_same_bar_stop_first(self):
        bar = quote(bid_low=1.0980, bid_high=1.1020)
        self.assertEqual(protective_exit_stop_first(
            "LONG", 1.0985, 1.1015, bar), ("STOP", 1.0985))

    def test_no_touch_is_no_fill(self):
        self.assertIsNone(limit_entry_fill("LONG", 1.0980, quote()))


if __name__ == "__main__":
    unittest.main()
