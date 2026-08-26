"""SMC_3R_V1 Stage-0 deterministic test suite.

Written from scratch against the registered package (`smc_3r_v1/`, ledger id
`9bd4c67a8404c8f9`) -- there was no prior test artifact in this repository or
conversation to recover, despite the module docstrings referencing this exact
filename. Every fixture below is a hand-built, fully deterministic OHLC frame
(no randomness), so the fixed rule constants this project has frozen --
1.5x displacement, 0.60 body efficiency, 8-bar sweep window, 2-pip SL buffer,
5-minute activation delay, 25-minute expiry, 3R target -- are exercised
directly rather than inferred from a backtest.

20 tests, grouped by module:
  reference_levels.py   -- 4
  smc_features.py       -- 4
  PendingOrder geometry -- 2
  session window        -- 2
  smc_state_machine.py  -- 5 (integration, via scan_dataset)
  matcher.py             -- 3
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from smc_3r_v1.reference_levels import compute_reference_levels
from smc_3r_v1.smc_features import extract_smc_features
from smc_3r_v1.smc_state_machine import OrderSide, PendingOrder, SMCStateMachine
from smc_3r_v1.matcher import M1OrderMatcher, OrderStatus, TradeOutcome

UTC = "UTC"


def _rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    idx = pd.DatetimeIndex([r["ts"] for r in rows], tz=UTC)
    return pd.DataFrame(
        {k: [r[k] for r in rows] for k in ("open", "high", "low", "close")},
        index=idx,
    )


def _flat_day(date: pd.Timestamp, n_bars: int, base: float = 1.1000,
              eps: float = 0.0001, bump_high_at: int | None = None,
              bump_high_to: float | None = None,
              bump_low_at: int | None = None,
              bump_low_to: float | None = None) -> list[dict]:
    """`n_bars` M5 bars starting at `date` 00:00, flat OHLC=base +/- eps, with
    one optional single-bar high bump and one optional single-bar low bump --
    used to seed exactly one causal swing-high and one causal swing-low
    fractal (see smc_features.extract_smc_features)."""
    rows = []
    for i in range(n_bars):
        ts = date + pd.Timedelta(minutes=5 * i)
        high = base + eps
        low = base - eps
        if bump_high_at is not None and i == bump_high_at:
            high = bump_high_to
        if bump_low_at is not None and i == bump_low_at:
            low = bump_low_to
        # Tiny nonzero body (not exactly open==close): a strictly-0 median_body_20
        # would make smc_state_machine.py's disp_body_ratio=body/median divide by
        # zero (a real latent issue in the registered code, left untouched per the
        # freeze -- worked around here at the fixture level instead).
        rows.append({"ts": ts, "open": base, "high": high, "low": low, "close": base + 0.00001})
    return rows


DAY = pd.Timestamp("2026-08-20", tz=UTC)
ASIAN_BASE = 1.1000
ASIAN_EPS = 0.0001
SWING_HIGH_IDX = 10   # confirmed (fractal) at bar 11
SWING_HIGH_VALUE = 1.1010
SWING_LOW_IDX = 15    # confirmed (fractal) at bar 16
SWING_LOW_VALUE = 1.0990


def _asian_block() -> list[dict]:
    return _flat_day(
        DAY, 72, base=ASIAN_BASE, eps=ASIAN_EPS,
        bump_high_at=SWING_HIGH_IDX, bump_high_to=SWING_HIGH_VALUE,
        bump_low_at=SWING_LOW_IDX, bump_low_to=SWING_LOW_VALUE,
    )
    # asian_high == SWING_HIGH_VALUE (1.1010), asian_low == SWING_LOW_VALUE
    # (1.0990) as a direct consequence -- the bump bars are simultaneously
    # the session extremes and the fractal swings, which is realistic (the
    # extreme of a session commonly *is* a swing point) and not a collision.


def _buy_setup_rows() -> list[dict]:
    """Sweep(ASIAN_LOW) -> displacement bull + CHoCH -> immediate FVG, at
    07:00/07:05/07:10, entirely inside the 07:00-10:00 session block."""
    return [
        {"ts": DAY + pd.Timedelta(hours=7), "open": 1.0993, "high": 1.0995,
         "low": 1.0985, "close": 1.0992},  # sweep: low<1.0990, close>1.0990
        {"ts": DAY + pd.Timedelta(hours=7, minutes=5), "open": 1.0995,
         "high": 1.1022, "low": 1.0993, "close": 1.1020},  # displacement bull, close>1.1010
        {"ts": DAY + pd.Timedelta(hours=7, minutes=10), "open": 1.1021,
         "high": 1.1035, "low": 1.1015, "close": 1.1030},  # FVG: low(1.1015) > c1_high(1.0995)
    ]


def _sell_setup_rows() -> list[dict]:
    """Mirror of the BUY setup at 12:00/12:05/12:10, inside the 12:00-15:00 block."""
    return [
        {"ts": DAY + pd.Timedelta(hours=12), "open": 1.1004, "high": 1.1015,
         "low": 1.1002, "close": 1.1005},  # sweep: high>1.1010, close<1.1010
        {"ts": DAY + pd.Timedelta(hours=12, minutes=5), "open": 1.1005,
         "high": 1.1007, "low": 1.0978, "close": 1.0980},  # displacement bear, close<1.0990
        {"ts": DAY + pd.Timedelta(hours=12, minutes=10), "open": 1.0979,
         "high": 1.0995, "low": 1.0965, "close": 1.0970},  # FVG: high(1.0995) < c1_low(1.1002)
    ]


@pytest.fixture(scope="module")
def buy_and_sell_orders() -> list[PendingOrder]:
    df = _rows_to_frame(_asian_block() + _buy_setup_rows() + _sell_setup_rows())
    return SMCStateMachine().scan_dataset(df, model_id="TEST")


# --------------------------------------------------------------- reference_levels.py

def test_asian_session_exact_72_bars_computes_high_low():
    df = _rows_to_frame(_asian_block())
    levels = compute_reference_levels(df, DAY + pd.Timedelta(hours=8))
    assert levels.asian_high == pytest.approx(SWING_HIGH_VALUE)
    assert levels.asian_low == pytest.approx(SWING_LOW_VALUE)


def test_asian_session_incomplete_returns_none():
    df = _rows_to_frame(_asian_block()[:-2])  # drop the last 2 bars -> 70, not 72
    levels = compute_reference_levels(df, DAY + pd.Timedelta(hours=8))
    assert levels.asian_high is None
    assert levels.asian_low is None


def test_pdh_pdl_selects_immediate_prior_day_when_it_has_full_coverage():
    prior_day = DAY - pd.Timedelta(days=1)
    rows = _flat_day(prior_day, 288, base=1.2000, eps=0.0005)
    df = _rows_to_frame(rows)
    levels = compute_reference_levels(df, DAY + pd.Timedelta(hours=8))
    assert levels.pdh == pytest.approx(1.2005)
    assert levels.pdl == pytest.approx(1.1995)


def test_pdh_pdl_skips_immediate_prior_day_below_coverage_threshold():
    two_days_prior = DAY - pd.Timedelta(days=2)
    immediate_prior = DAY - pd.Timedelta(days=1)
    rows = (
        _flat_day(two_days_prior, 288, base=1.3000, eps=0.0005)   # full coverage: eligible
        + _flat_day(immediate_prior, 100, base=1.4000, eps=0.0005)  # 100 < 273: skipped
    )
    df = _rows_to_frame(rows)
    levels = compute_reference_levels(df, DAY + pd.Timedelta(hours=8))
    assert levels.pdh == pytest.approx(1.3005)
    assert levels.pdl == pytest.approx(1.2995)


# --------------------------------------------------------------- smc_features.py

def test_median_body_20_excludes_the_current_bar_causally():
    rows = []
    for i in range(25):
        ts = DAY + pd.Timedelta(minutes=5 * i)
        body = 0.0001 * i
        rows.append({"ts": ts, "open": 1.1000, "high": 1.1000 + body + 0.0001,
                     "low": 1.1000 - 0.0001, "close": 1.1000 + body})
    df = _rows_to_frame(rows)
    out = extract_smc_features(df)
    expected = out["body"].iloc[4:24].median()  # shift(1).rolling(20) at row 24 -> rows 4..23
    assert out["median_body_20"].iloc[24] == pytest.approx(expected)
    assert out["median_body_20"].iloc[24] != pytest.approx(out["body"].iloc[24])


def test_displacement_bull_requires_both_body_multiple_and_efficiency():
    rows = []
    for i in range(20):
        ts = DAY + pd.Timedelta(minutes=5 * i)
        rows.append({"ts": ts, "open": 1.1000, "high": 1.1001, "low": 1.0999, "close": 1.1000})
    # row 20: body >= 1.5x median AND body_eff >= 0.60 -> True
    rows.append({"ts": DAY + pd.Timedelta(minutes=100), "open": 1.1000, "high": 1.1002,
                 "low": 1.0999, "close": 1.1002})
    # row 21: body >= 1.5x median but body_eff < 0.60 (wide wicks) -> False
    rows.append({"ts": DAY + pd.Timedelta(minutes=105), "open": 1.1002, "high": 1.1010,
                 "low": 1.0995, "close": 1.1005})
    df = _rows_to_frame(rows)
    out = extract_smc_features(df)
    assert bool(out["disp_bull"].iloc[20]) is True
    assert bool(out["disp_bull"].iloc[21]) is False


def test_confirmed_swing_high_lags_by_one_bar():
    rows = [
        {"ts": DAY, "open": 1.1000, "high": 1.1000, "low": 1.0999, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=5), "open": 1.1000, "high": 1.1200,
         "low": 1.0999, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=10), "open": 1.1000, "high": 1.1000,
         "low": 1.0999, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=15), "open": 1.1000, "high": 1.1000,
         "low": 1.0999, "close": 1.1000},
    ]
    df = _rows_to_frame(rows)
    out = extract_smc_features(df)
    assert pd.isna(out["last_confirmed_swing_high"].iloc[1])  # bar 1 IS the extreme, not yet confirmed
    assert out["last_confirmed_swing_high"].iloc[2] == pytest.approx(1.1200)  # confirmed once bar 2 closes
    assert out["last_confirmed_swing_high"].iloc[3] == pytest.approx(1.1200)  # ffill holds


def test_confirmed_swing_low_lags_by_one_bar():
    rows = [
        {"ts": DAY, "open": 1.1000, "high": 1.1001, "low": 1.1000, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=5), "open": 1.1000, "high": 1.1001,
         "low": 1.0800, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=10), "open": 1.1000, "high": 1.1001,
         "low": 1.1000, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=15), "open": 1.1000, "high": 1.1001,
         "low": 1.1000, "close": 1.1000},
    ]
    df = _rows_to_frame(rows)
    out = extract_smc_features(df)
    assert pd.isna(out["last_confirmed_swing_low"].iloc[1])
    assert out["last_confirmed_swing_low"].iloc[2] == pytest.approx(1.0800)
    assert out["last_confirmed_swing_low"].iloc[3] == pytest.approx(1.0800)


# --------------------------------------------------------------- PendingOrder geometry

def test_pending_order_validate_accepts_correct_buy_geometry():
    order = PendingOrder(
        setup_id="X", model_id="TEST", side=OrderSide.BUY,
        limit_price=1.1000, sl=1.0980, tp=1.1060,
        activation_time=DAY, expiry_time=DAY + pd.Timedelta(minutes=25), meta={},
    )
    order.validate()  # must not raise


def test_pending_order_validate_rejects_inverted_buy_geometry():
    order = PendingOrder(
        setup_id="X", model_id="TEST", side=OrderSide.BUY,
        limit_price=1.1000, sl=1.1010, tp=1.1060,  # sl above entry -- invalid for BUY
        activation_time=DAY, expiry_time=DAY + pd.Timedelta(minutes=25), meta={},
    )
    with pytest.raises(AssertionError):
        order.validate()


# --------------------------------------------------------------- session window

def test_is_in_session_window_true_inside_morning_and_midday_blocks():
    sm = SMCStateMachine()
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=8)) is True
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=13)) is True


def test_is_in_session_window_false_between_and_outside_blocks():
    sm = SMCStateMachine()
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=11)) is False  # the gap
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=20)) is False


# --------------------------------------------------------------- smc_state_machine.py (integration)

def test_scan_dataset_builds_buy_order_from_sweep_displacement_choch_fvg(buy_and_sell_orders):
    buy_orders = [o for o in buy_and_sell_orders if o.side == OrderSide.BUY]
    assert len(buy_orders) == 1
    o = buy_orders[0]
    assert o.limit_price == pytest.approx(1.1015)
    assert o.sl == pytest.approx(1.0983)   # sweep_extreme(1.0985) - 2 pips(0.0002)
    assert o.tp == pytest.approx(1.1111)   # limit + 3R, R = 0.0032
    assert o.activation_time == DAY + pd.Timedelta(hours=7, minutes=15)
    assert o.expiry_time == DAY + pd.Timedelta(hours=7, minutes=40)
    assert o.meta["liquidity_source"] == "ASIAN_LOW"


def test_scan_dataset_builds_sell_order_from_sweep_displacement_choch_fvg(buy_and_sell_orders):
    sell_orders = [o for o in buy_and_sell_orders if o.side == OrderSide.SELL]
    assert len(sell_orders) == 1
    o = sell_orders[0]
    assert o.limit_price == pytest.approx(1.0995)
    assert o.sl == pytest.approx(1.1017)   # sweep_extreme(1.1015) + 2 pips
    assert o.tp == pytest.approx(1.0929)   # limit - 3R, R = 0.0022
    assert o.meta["liquidity_source"] == "ASIAN_HIGH"


def test_scan_dataset_invalidates_sweep_after_max_sweep_bars():
    sweep = [{"ts": DAY + pd.Timedelta(hours=7), "open": 1.0993, "high": 1.0995,
              "low": 1.0985, "close": 1.0992}]
    buffer_bars = [
        {"ts": DAY + pd.Timedelta(hours=7, minutes=5 * (i + 1)), "open": 1.1000,
         "high": 1.1001, "low": 1.0999, "close": 1.1000}
        for i in range(8)  # exactly max_sweep_bars -- the 9th bar after sweep is invalidated
    ]
    would_be_displacement = [
        {"ts": DAY + pd.Timedelta(hours=7, minutes=45), "open": 1.0995,
         "high": 1.1022, "low": 1.0993, "close": 1.1020},
    ]
    df = _rows_to_frame(_asian_block() + sweep + buffer_bars + would_be_displacement)
    orders = SMCStateMachine().scan_dataset(df)
    assert orders == []


def test_scan_dataset_abandons_setup_when_fvg_not_confirmed_on_immediate_bar():
    sweep_and_displacement = _buy_setup_rows()[:2]
    failed_fvg_bar = [{
        "ts": DAY + pd.Timedelta(hours=7, minutes=10), "open": 1.1021,
        "high": 1.1035, "low": 1.0990,  # low(1.0990) NOT > c1_high(1.0995) -> no FVG
        "close": 1.1030,
    }]
    late_bar_that_would_otherwise_qualify = [{
        "ts": DAY + pd.Timedelta(hours=7, minutes=15), "open": 1.1030,
        "high": 1.1040, "low": 1.1015,  # would satisfy the original FVG test, but no retry
        "close": 1.1035,
    }]
    df = _rows_to_frame(
        _asian_block() + sweep_and_displacement + failed_fvg_bar + late_bar_that_would_otherwise_qualify
    )
    orders = SMCStateMachine().scan_dataset(df)
    assert orders == []


def test_scan_dataset_produces_no_orders_outside_session_window():
    out_of_window_rows = [
        {"ts": DAY + pd.Timedelta(hours=11), "open": 1.0993, "high": 1.0995,
         "low": 1.0985, "close": 1.0992},
        {"ts": DAY + pd.Timedelta(hours=11, minutes=5), "open": 1.0995,
         "high": 1.1022, "low": 1.0993, "close": 1.1020},
        {"ts": DAY + pd.Timedelta(hours=11, minutes=10), "open": 1.1021,
         "high": 1.1035, "low": 1.1015, "close": 1.1030},
    ]
    df = _rows_to_frame(_asian_block() + out_of_window_rows)
    orders = SMCStateMachine().scan_dataset(df)
    assert orders == []


# --------------------------------------------------------------- matcher.py

def _test_order(side: OrderSide, limit_price: float, sl: float, tp: float) -> PendingOrder:
    return PendingOrder(
        setup_id="X", model_id="TEST", side=side, limit_price=limit_price, sl=sl, tp=tp,
        activation_time=DAY, expiry_time=DAY + pd.Timedelta(minutes=25), meta={},
    )


def test_matcher_fills_buy_limit_when_low_plus_spread_touches_entry():
    order = _test_order(OrderSide.BUY, limit_price=1.1000, sl=1.0980, tp=1.1050)
    rows = [
        {"ts": DAY, "open": 1.1002, "high": 1.1003, "low": 1.0998, "close": 1.1000},
        {"ts": DAY + pd.Timedelta(minutes=1), "open": 1.1001, "high": 1.1005,
         "low": 1.1000, "close": 1.1002},
    ]
    m1 = _rows_to_frame(rows)
    record = M1OrderMatcher(spread_pips=1.0, pip_size=0.0001).evaluate_order(order, m1)
    assert record.order_status == OrderStatus.FILLED
    assert record.fill_time == DAY
    assert record.latency_m1_bars == 1
    assert record.outcome == TradeOutcome.UNRESOLVED  # data runs out before SL/TP/cutoff


def test_matcher_marks_same_bar_sl_and_tp_touch_as_loss_with_ambiguity_flag():
    order = _test_order(OrderSide.BUY, limit_price=1.1000, sl=1.0990, tp=1.1030)
    rows = [
        {"ts": DAY, "open": 1.0996, "high": 1.0999, "low": 1.0994, "close": 1.0997},  # fills here
        {"ts": DAY + pd.Timedelta(minutes=1), "open": 1.0995, "high": 1.1035,
         "low": 1.0985, "close": 1.1000},  # both SL(1.0990) and TP(1.1030) touched
    ]
    m1 = _rows_to_frame(rows)
    record = M1OrderMatcher(spread_pips=1.0, pip_size=0.0001).evaluate_order(order, m1)
    assert record.order_status == OrderStatus.FILLED
    assert record.outcome == TradeOutcome.LOSS
    assert record.intrabar_ambiguity is True
    assert record.exit_price == pytest.approx(1.0990)
    assert record.realized_r == pytest.approx(-1.0)


def test_matcher_reports_data_gap_when_m1_bars_missing_at_activation():
    order = _test_order(OrderSide.BUY, limit_price=1.1000, sl=1.0980, tp=1.1050)
    rows = [
        {"ts": DAY + pd.Timedelta(minutes=2), "open": 1.1000, "high": 1.1002,
         "low": 1.0998, "close": 1.1001},  # first bar is 2 minutes late, not exactly activation
    ]
    m1 = _rows_to_frame(rows)
    record = M1OrderMatcher(spread_pips=1.0, pip_size=0.0001).evaluate_order(order, m1)
    assert record.order_status == OrderStatus.DATA_GAP
    assert record.outcome == TradeOutcome.DATA_GAP
