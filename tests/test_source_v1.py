from datetime import datetime, timezone

from session_strategy.models import Candle
from session_strategy.source_v1 import classify, detect, levels, realize


def c(h, o, hi, lo, close):
    return Candle(datetime(2026, 8, 12, h, tzinfo=timezone.utc), o, hi, lo, close)


def test_literal_midpoint_trend_entry_and_stop():
    session = [c(0, 100, 102, 99, 102), c(1, 102, 104, 101, 104)]
    lv = levels(session)
    assert classify(lv) == "BULLISH_TREND"
    trade = detect("BULLISH_TREND", lv, [c(7, 104, 104, 101, 103)])
    assert trade.setup == "TREND"
    assert trade.entry == 101.5
    assert trade.stop_loss == 100.25


def test_sweep_partial_then_breakeven_is_three_r():
    session = [c(0, 100, 104, 100, 102)]
    lv = levels(session)
    trade = detect("RANGE", lv, [c(7, 101, 102, 99, 101)])
    assert trade.setup == "SWEEP"
    realize(trade, [c(8, 101, 105.2, 100.5, 105), c(9, 105, 105, 101, 101)])
    assert trade.outcome_r == 3.0
    assert trade.outcome_label == "4R_PARTIAL_THEN_BE"
