"""ST04_07_EXECUTION_ATTRIBUTION_V1 — Entry 2 (Sweep) fill-execution attribution study.

Research-only. Operates purely on historical OHLC DataFrames; makes no MT5 calls of any
kind (no read, no write). See ST04_07_EXECUTION_ATTRIBUTION_V1_SPEC.md for the full
architecture, signal-qualification rules, and the attribution accounting this compares.

FROZEN INVARIANTS (do not touch in this module — see spec §0):
reference-box definition, ER_ONLY_V2 classification, Sweep qualification, Sweep direction,
and strategy routing. This module only ever compares two execution/fill models against one
frozen signal population; it must never become a second place those upstream rules are decided.
"""

import numpy as np
import pandas as pd


# =====================================================================
# 1. UPSTREAM ENGINE & IMMUTABLE LEDGER EXTRACTION
# =====================================================================
def extract_signal_ledger(
    df_m15: pd.DataFrame,
    pip: float = 0.0001,
    sl_buffer_pips: float = 1.0,
    output_csv: str = "ST04_07_SWEEP_SIGNAL_LEDGER.csv",
) -> pd.DataFrame:
    df = df_m15.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df["date"] = df.index.date
    df["hour"] = df.index.hour
    buffer = sl_buffer_pips * pip

    records = []

    # Process each day's reference session
    for date, day_bars in df.groupby("date"):
        asian = day_bars[(day_bars["hour"] >= 0) & (day_bars["hour"] < 7)]
        if len(asian) < 4:
            continue

        box_start = asian.index[0]
        box_end = asian.index[-1]
        box_open = float(asian["open"].iloc[0])
        box_high = float(asian["high"].max())
        box_low = float(asian["low"].min())
        box_close = float(asian["close"].iloc[-1])
        box_range = box_high - box_low

        if box_range <= 0:
            continue

        # Kaufman Efficiency Ratio (ER_ONLY_V2)
        net_change = abs(box_close - box_open)
        path = (asian["high"] - asian["low"]).sum()
        er = net_change / path if path > 0 else 0.0

        # Regime Filter: Only RANGE (ER < 0.40) qualifies for Entry 2
        if er >= 0.40:
            continue

        post_box = day_bars[day_bars.index > box_end]

        for t_sweep, bar in post_box.iterrows():
            # Bearish Sweep of Box High
            if bar["high"] > box_high and bar["close"] < box_high:
                sweep_extreme = float(bar["high"])
                records.append(
                    {
                        "reference_id": f"EURUSD_{date}_E2_SHORT",
                        "symbol": "EURUSD",
                        "reference_date": str(date),
                        "box_start": str(box_start),
                        "box_end": str(box_end),
                        "box_open": box_open,
                        "box_high": box_high,
                        "box_low": box_low,
                        "box_close": box_close,
                        "box_range_pips": round(box_range / pip, 2),
                        "ER": round(er, 4),
                        "regime": "RANGE",
                        "sweep_timestamp": str(t_sweep),
                        "sweep_direction": "SHORT",
                        "sweep_open": float(bar["open"]),
                        "sweep_high": sweep_extreme,
                        "sweep_low": float(bar["low"]),
                        "sweep_close": float(bar["close"]),
                        "sweep_extreme": sweep_extreme,
                        "reference_level": box_high,
                        "signal_price": float(bar["close"]),
                        "sl_price": sweep_extreme + buffer,
                    }
                )
                break

            # Bullish Sweep of Box Low
            elif bar["low"] < box_low and bar["close"] > box_low:
                sweep_extreme = float(bar["low"])
                records.append(
                    {
                        "reference_id": f"EURUSD_{date}_E2_LONG",
                        "symbol": "EURUSD",
                        "reference_date": str(date),
                        "box_start": str(box_start),
                        "box_end": str(box_end),
                        "box_open": box_open,
                        "box_high": box_high,
                        "box_low": box_low,
                        "box_close": box_close,
                        "box_range_pips": round(box_range / pip, 2),
                        "ER": round(er, 4),
                        "regime": "RANGE",
                        "sweep_timestamp": str(t_sweep),
                        "sweep_direction": "LONG",
                        "sweep_open": float(bar["open"]),
                        "sweep_high": float(bar["high"]),
                        "sweep_low": sweep_extreme,
                        "sweep_close": float(bar["close"]),
                        "sweep_extreme": sweep_extreme,
                        "reference_level": box_low,
                        "signal_price": float(bar["close"]),
                        "sl_price": sweep_extreme - buffer,
                    }
                )
                break

    ledger = pd.DataFrame(records)
    ledger.to_csv(output_csv, index=False)
    return ledger


# =====================================================================
# 2. EXECUTION ATTRIBUTION ENGINE (LAYER B - M1)
# =====================================================================
def execute_attribution_test(
    ledger_csv: str,
    df_m1: pd.DataFrame,
    spread_pips: float = 0.8,
    target_r: float = 1.5,
    limit_expiry_min: int = 60,
) -> tuple[pd.DataFrame, dict]:
    ledger = pd.read_csv(ledger_csv)
    pip = 0.0001
    spread = spread_pips * pip

    if not isinstance(df_m1.index, pd.DatetimeIndex):
        df_m1.index = pd.to_datetime(df_m1.index)

    market_res = []
    limit_res = []

    for ledger_idx, sig in ledger.iterrows():
        sig_t = pd.to_datetime(sig["sweep_timestamp"])
        direction = sig["sweep_direction"]
        sl = float(sig["sl_price"])
        ref_level = float(sig["reference_level"])

        forward_m1 = df_m1[df_m1.index > sig_t]
        if forward_m1.empty:
            continue

        # --- CONTRACT A: MARKET ---
        # Symmetric half-spread against the M1 open: LONG fills at the modeled ask,
        # SHORT fills at the modeled bid. Uses real bid/ask columns when the caller's
        # M1 data provides them (authoritative Layer B/C), falls back to a modeled
        # half-spread around `open` for Layer A (theoretical) runs.
        m_bar1 = forward_m1.iloc[0]
        if "ask" in df_m1.columns and "bid" in df_m1.columns:
            m_entry = float(m_bar1["ask"]) if direction == "LONG" else float(m_bar1["bid"])
        else:
            half_spread = spread / 2.0
            m_entry = (
                m_bar1["open"] + half_spread
                if direction == "LONG"
                else m_bar1["open"] - half_spread
            )
        m_risk = abs(m_entry - sl)

        if m_risk > 0:
            m_tp = (
                m_entry + (m_risk * target_r)
                if direction == "LONG"
                else m_entry - (m_risk * target_r)
            )
            m_pnl = None

            for _, bar in forward_m1.iterrows():
                if direction == "LONG":
                    if bar["low"] <= sl:
                        m_pnl = -1.0
                        break
                    if bar["high"] >= m_tp:
                        m_pnl = target_r
                        break
                else:
                    if bar["high"] >= sl:
                        m_pnl = -1.0
                        break
                    if bar["low"] <= m_tp:
                        m_pnl = target_r
                        break

            if m_pnl is not None:
                market_res.append(
                    {"ledger_idx": ledger_idx, "pnl_r": m_pnl, "status": "FILLED", "type": "MARKET"}
                )

        # --- CONTRACT B: LIMIT ---
        l_entry = ref_level
        l_risk = abs(l_entry - sl)
        l_tp = (
            l_entry + (l_risk * target_r)
            if direction == "LONG"
            else l_entry - (l_risk * target_r)
        )
        l_expiry = sig_t + pd.Timedelta(minutes=limit_expiry_min)

        l_filled = False
        l_fill_idx = None

        fill_window = forward_m1[forward_m1.index <= l_expiry]
        for t_m1, bar in fill_window.iterrows():
            if direction == "LONG" and bar["low"] <= (l_entry - spread):
                l_filled = True
                l_fill_idx = t_m1
                break
            elif direction == "SHORT" and bar["high"] >= (l_entry + spread):
                l_filled = True
                l_fill_idx = t_m1
                break

        if not l_filled:
            limit_res.append(
                {"ledger_idx": ledger_idx, "pnl_r": 0.0, "status": "NO_FILL", "type": "LIMIT"}
            )
        else:
            post_fill = forward_m1[forward_m1.index >= l_fill_idx]
            l_pnl = None

            for _, bar in post_fill.iterrows():
                if direction == "LONG":
                    if bar["low"] <= sl:
                        l_pnl = -1.0
                        break
                    if bar["high"] >= l_tp:
                        l_pnl = target_r
                        break
                else:
                    if bar["high"] >= sl:
                        l_pnl = -1.0
                        break
                    if bar["low"] <= l_tp:
                        l_pnl = target_r
                        break

            if l_pnl is not None:
                limit_res.append(
                    {"ledger_idx": ledger_idx, "pnl_r": l_pnl, "status": "FILLED", "type": "LIMIT"}
                )

    # Calculate statistics
    def calc_stats(results: list, total_n: int) -> dict:
        df_r = pd.DataFrame(results)
        fills = df_r[df_r["status"] == "FILLED"]
        n_fills = len(fills)
        if n_fills == 0:
            return {
                "Signals": total_n,
                "Fills": 0,
                "FillRate": 0.0,
                "WR": 0.0,
                "PF": 0.0,
                "Expectancy": 0.0,
                "NetR": 0.0,
                "MaxDD": 0.0,
            }

        wins = len(fills[fills["pnl_r"] > 0])
        wr = (wins / n_fills) * 100
        gw = fills[fills["pnl_r"] > 0]["pnl_r"].sum()
        gl = abs(fills[fills["pnl_r"] < 0]["pnl_r"].sum())
        pf = gw / gl if gl > 0 else (99.0 if gw > 0 else 0.0)
        net_r = fills["pnl_r"].sum()
        exp = net_r / n_fills

        cum = fills["pnl_r"].cumsum()
        max_dd = (cum.cummax() - cum).max()

        return {
            "Signals": total_n,
            "Fills": n_fills,
            "FillRate": (n_fills / total_n) * 100,
            "WR": wr,
            "PF": pf,
            "Expectancy": exp,
            "NetR": net_r,
            "MaxDD": max_dd,
        }

    total_signals = len(ledger)
    stats_m = calc_stats(market_res, total_signals)
    stats_l = calc_stats(limit_res, total_signals)

    comparison_df = pd.DataFrame(
        {
            "Metric": [
                "Signals (N)",
                "Fills",
                "Fill Rate",
                "Win Rate",
                "Profit Factor",
                "Expectancy",
                "Net R",
                "Max DD",
            ],
            "E2-A Market (Control)": [
                stats_m["Signals"],
                stats_m["Fills"],
                f"{stats_m['FillRate']:.1f}%",
                f"{stats_m['WR']:.1f}%",
                f"{stats_m['PF']:.2f}",
                f"{stats_m['Expectancy']:+.3f}R",
                f"{stats_m['NetR']:+.2f}R",
                f"{stats_m['MaxDD']:.2f}R",
            ],
            "E2-B Limit (Challenger)": [
                stats_l["Signals"],
                stats_l["Fills"],
                f"{stats_l['FillRate']:.1f}%",
                f"{stats_l['WR']:.1f}%",
                f"{stats_l['PF']:.2f}",
                f"{stats_l['Expectancy']:+.3f}R",
                f"{stats_l['NetR']:+.2f}R",
                f"{stats_l['MaxDD']:.2f}R",
            ],
        }
    )

    return comparison_df, {
        "market": stats_m,
        "limit": stats_l,
        "market_results": market_res,
        "limit_results": limit_res,
    }


# =====================================================================
# 3. ATTRIBUTION ACCOUNTING (spec §7)
# =====================================================================
def compute_attribution(market_results: list, limit_results: list) -> dict:
    """Decompose Contract B's outcome relative to Contract A on the identical signal
    population, per-signal (aligned by `ledger_idx`), instead of comparing two
    independently-summarized PF/expectancy numbers.

    Realized Edge = Signal Edge + Price/Geometry Improvement
                     - Missed Fill Opportunity Cost - Friction
    """
    market_by_idx = {r["ledger_idx"]: r for r in market_results}
    limit_filled = [r for r in limit_results if r["status"] == "FILLED"]
    limit_no_fill = [r for r in limit_results if r["status"] == "NO_FILL"]

    signal_edge = sum(r["pnl_r"] for r in market_results)

    # Price/geometry improvement: on signals the limit actually filled, compare its
    # outcome to what the market contract achieved on that SAME signal.
    overlap_idx = [r["ledger_idx"] for r in limit_filled if r["ledger_idx"] in market_by_idx]
    price_improvement = sum(
        next(r["pnl_r"] for r in limit_filled if r["ledger_idx"] == idx) - market_by_idx[idx]["pnl_r"]
        for idx in overlap_idx
    )

    # Missed-fill opportunity cost: what the market contract earned on signals the
    # limit never filled. This is a cost only if positive (market would have won);
    # a limit that skips losers is doing its job, not incurring a cost.
    missed_fill_cost = sum(
        max(market_by_idx[r["ledger_idx"]]["pnl_r"], 0.0)
        for r in limit_no_fill
        if r["ledger_idx"] in market_by_idx
    )

    realized_execution_edge = sum(r["pnl_r"] for r in limit_filled) - missed_fill_cost

    return {
        "signal_edge_r": round(signal_edge, 3),
        "price_geometry_improvement_r": round(price_improvement, 3),
        "missed_fill_opportunity_cost_r": round(missed_fill_cost, 3),
        "friction_note": "spread/slippage cost is embedded in each contract's own fill price, "
                          "not separately decomposed in v1 — see spec limitation note",
        "realized_execution_edge_limit_r": round(realized_execution_edge, 3),
        "n_overlap_filled_by_both": len(overlap_idx),
        "n_missed_fill": len(limit_no_fill),
    }
