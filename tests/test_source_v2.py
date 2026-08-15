from datetime import date, datetime, timezone

from session_strategy.models import Candle
from session_strategy.source_v2 import (combined_bias, fractal_pivots, h1_structure,
                                        range_or_trend, ratchet_trailing_stop,
                                        source_v2_bounds)


def c(h, high, low, close=None, opened=None):
    close = (high + low) / 2 if close is None else close
    opened = close if opened is None else opened
    return Candle(datetime(2026, 8, 12, h % 24, tzinfo=timezone.utc), opened, high, low, close)


def test_london_dst_bounds_are_23_to_07_utc():
    start, lock, end = source_v2_bounds(date(2026, 8, 12))
    assert (start.hour, start.day, lock.hour, end.hour) == (23, 11, 7, 9)


def test_london_winter_bounds_are_00_to_08_utc():
    start, lock, end = source_v2_bounds(date(2026, 1, 12))
    assert (start.hour, lock.hour, end.hour) == (0, 8, 10)


def test_fractals_and_bullish_structure():
    bars = [c(i, hi, lo) for i, (hi, lo) in enumerate([
        (5,3),(8,4),(6,2),(7,4),(10,5),(8,4),(9,6),(12,7),(10,6)])]
    highs, lows = fractal_pivots(bars)
    assert [x[1] for x in highs][-2:] == [10,12]
    assert [x[1] for x in lows][-2:] == [2,4]
    assert h1_structure(bars, .1) == "BULLISH"


def test_bias_requires_agreement_and_range_threshold():
    session = [c(0, 10, 0, close=2, opened=1), c(1, 10, 0, close=7)]
    assert combined_bias(session, "BULLISH") == "BULLISH"
    assert combined_bias(session, "BEARISH") == "UNCERTAIN"
    assert range_or_trend(session) == "TREND"


def test_trailing_stop_only_ratchets():
    bars = [c(i, hi, lo) for i, (hi, lo) in enumerate([(5,3),(6,2),(7,4),(8,5)])]
    assert ratchet_trailing_stop("LONG", 1, bars) == 2
    assert ratchet_trailing_stop("LONG", 3, bars) == 3
