from datetime import datetime, timedelta, timezone
import unittest

from session_strategy.models import Candle
from session_strategy.research_optimization import atr, dynamic_stop, session_volume_profile


class ResearchOptimizationTests(unittest.TestCase):
    def bars(self):
        start = datetime(2026, 8, 12, tzinfo=timezone.utc)
        return [Candle(start + timedelta(minutes=15 * i), 100 + i, 102 + i, 99 + i,
                       101 + i, 10 + i) for i in range(16)]

    def test_volume_profile_is_ordered_and_inside_range(self):
        bars = self.bars()
        profile = session_volume_profile(bars, bins=20)
        self.assertLessEqual(profile.val, profile.vpoc)
        self.assertLessEqual(profile.vpoc, profile.vah)
        self.assertGreater(profile.val, min(c.low for c in bars))
        self.assertLess(profile.vah, max(c.high for c in bars))

    def test_atr_and_dynamic_stop_expand_beyond_sweep(self):
        value = atr(self.bars(), 14)
        stop, distance = dynamic_stop(100, 98, "LONG", value, 1.2, 0.5)
        self.assertLess(stop, 98)
        self.assertAlmostEqual(distance, 100 - stop)

    def test_dynamic_short_stop_mirrors_long(self):
        stop, distance = dynamic_stop(100, 102, "SHORT", 3, 1.2, 0.5)
        self.assertAlmostEqual(stop, 106.1)
        self.assertAlmostEqual(distance, 6.1)


if __name__ == "__main__":
    unittest.main()
