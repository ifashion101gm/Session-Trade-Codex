import datetime as dt
import unittest

from session_strategy.cowork_sweep_v2 import detect_cowork_sweeps
from session_strategy.session_contract import M15Bar, SweepSide


UTC = dt.timezone.utc


def bar(index, open_, high, low, close):
    return M15Bar(dt.datetime(2022, 10, 3, 8, tzinfo=UTC)
                  + dt.timedelta(minutes=15 * index), open_, high, low, close)


class CoworkSweepV2Tests(unittest.TestCase):
    def test_short_reversal_body_uses_outer_body_edge(self):
        result = detect_cowork_sweeps(
            1.1000, 1.0900, [bar(0, 1.0990, 1.1002, 1.0970, 1.0980)], 0.0001)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].side, result[0].direction),
                         (SweepSide.HIGH, "SHORT"))
        self.assertEqual(result[0].reference_price, 1.0990)

    def test_long_reversal_body_uses_outer_body_edge(self):
        result = detect_cowork_sweeps(
            1.1000, 1.0900, [bar(0, 1.0910, 1.0930, 1.0898, 1.0920)], 0.0001)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].direction, result[0].reference_price),
                         ("LONG", 1.0910))

    def test_touch_subpip_outside_open_and_no_reclaim_are_rejected(self):
        candles = [
            bar(0, 1.0990, 1.1000, 1.0980, 1.0995),
            bar(1, 1.0990, 1.10005, 1.0980, 1.0995),
            bar(2, 1.1002, 1.1010, 1.0980, 1.0995),
            bar(3, 1.0990, 1.1010, 1.0980, 1.1005),
        ]
        self.assertEqual(detect_cowork_sweeps(1.1000, 1.0900, candles, 0.0001), [])

    def test_wick_can_confirm_non_reversal_body(self):
        result = detect_cowork_sweeps(
            1.1000, 1.0900, [bar(0, 1.0980, 1.1010, 1.0975, 1.0990)], 0.0001)
        self.assertEqual(result[0].confirmation, "WICK_RATIO")

    def test_future_append_does_not_change_prior_signal(self):
        first = bar(0, 1.0990, 1.1010, 1.0970, 1.0980)
        original = detect_cowork_sweeps(1.1000, 1.0900, [first], 0.0001)
        extended = detect_cowork_sweeps(
            1.1000, 1.0900, [first, bar(1, 1.0910, 1.0930, 1.0890, 1.0920)], 0.0001)
        self.assertEqual(extended[:len(original)], original)


if __name__ == "__main__":
    unittest.main()
