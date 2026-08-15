#!/usr/bin/env python3
"""
Backtest SESSION_FLOW_V1 — the first backtest of the corrected contract.

Sweep is read in the REFERENCE session (spec §2.1, corrected 2026-08-15). All
entries are resting limits fixed at the reference close. Two legs per day.

COSTS. Gross R is reported alongside net. Net applies, per trade:
  entry spread  : the broker spread on the fill bar, from the master CSV
  exit  spread  : the broker spread on the exit bar
  slippage      : --slippage pips, round turn (default 0.2)
Cost is charged in price and converted to R at that trade's own R.

COLLISION. STOP_FIRST — if a bar's range contains both the stop and a target,
the stop is taken. No intrabar path information is used.

    python scripts/backtest_session_flow.py
    python scripts/backtest_session_flow.py --slippage 0.5
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import session_flow as SF  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "eurusd_m15_2022_10.master.csv"
PIP = 0.0001
POINT = 0.00001
LEGS = SF.LEGS


def load_master():
    bars = []
    with open(MASTER, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            bars.append({"t": dt.datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S"),
                         "o": float(r["open"]), "h": float(r["high"]),
                         "l": float(r["low"]), "c": float(r["close"]),
                         "sp": int(r["spread"]) if r["spread"] else 0})
    bars.sort(key=lambda b: b["t"])
    return bars


def simulate(p, lv, ex, forward, slip_pips):
    short = p["dir"] == "SHORT"
    e, sl, tp1, tp2, R = p["entry"], p["sl"], p["tp1"], p["tp2"], lv["R"]
    fill = next((b for b in ex if (b["h"] >= e if short else b["l"] <= e)), None)
    if not fill:
        return None
    after = [b for b in forward if b["t"] > fill["t"]]
    partial, banked, mfe = False, 0.0, 0.0
    pr = abs(e - tp1) / R
    for b in after:
        mfe = max(mfe, ((e - b["l"]) if short else (b["h"] - e)) / R)
        if (b["h"] >= sl) if short else (b["l"] <= sl):
            gross = banked + (0.0 if partial else -1.0)
            return dict(fill=fill, exit=b, outcome="BREAKEVEN" if partial else "STOP_LOSS",
                        gross=gross, mfe=mfe, partial=partial, pr=pr, R=R)
        if (b["l"] <= tp2) if short else (b["h"] >= tp2):
            gross = banked + SF.TP2_R * (0.25 if partial else 1.0)
            return dict(fill=fill, exit=b, outcome="TP5_HIT", gross=gross,
                        mfe=mfe, partial=partial, pr=pr, R=R)
        if not partial and ((b["l"] <= tp1) if short else (b["h"] >= tp1)):
            partial, banked, sl = True, pr * 0.75, e
    b = after[-1] if after else fill
    return dict(fill=fill, exit=b, outcome="OPEN_AT_END", gross=banked,
                mfe=mfe, partial=partial, pr=pr, R=R)


def net_of(s, slip_pips):
    cost_price = (s["fill"]["sp"] + s["exit"]["sp"]) * POINT + slip_pips * PIP
    return s["gross"] - cost_price / s["R"], cost_price / s["R"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slippage", type=float, default=0.2)
    ap.add_argument("--er-max", type=float, default=0.35)
    a = ap.parse_args()
    bars = load_master()
    d0, d1 = bars[0]["t"], bars[-1]["t"]

    trades = []
    unfilled = 0
    D = dt.datetime(d0.year, d0.month, d0.day)
    while D <= d1:
        if D.weekday() < 5:
            for tag, rn, xn, (rs, re), (xs, xe) in LEGS:
                ref = SF.V.window(bars, D.replace(hour=rs), D.replace(hour=re))
                ex = SF.V.window(bars, D.replace(hour=xs), D.replace(hour=xe))
                if len(ref) < 8 or len(ex) < 8:
                    continue
                lv = SF.levels(ref)
                p = SF.plan(ref, lv, a.er_max)
                fwd = [b for b in bars if b["t"] >= D.replace(hour=xs)]
                s = simulate(p, lv, ex, fwd, a.slippage)
                if s is None:
                    unfilled += 1
                    continue
                net, cost = net_of(s, a.slippage)
                trades.append(dict(date=D, leg=tag, setup=p["setup"], dir=p["dir"],
                                   outcome=s["outcome"], gross=s["gross"], net=net,
                                   cost=cost, mfe=s["mfe"]))
        D += dt.timedelta(days=1)

    print(f"BACKTEST · SESSION_FLOW_V1 · EURUSD M15 · {d0:%Y-%m-%d} to {d1:%Y-%m-%d}")
    print(f"sweep read in the reference session · ER<={a.er_max} · slippage {a.slippage}p round turn")
    print(f"costs from the master CSV spread column · STOP_FIRST · in-sample\n")

    n = len(trades)
    if not n:
        print("no trades"); return 0
    g = [t["gross"] for t in trades]; nt = [t["net"] for t in trades]
    print(f"{'':<22}{'n':>4}{'gross R':>10}{'net R':>10}{'net/trade':>11}{'win%':>7}")

    def block(label, sel):
        if not sel: return
        gg = sum(t["gross"] for t in sel); nn = sum(t["net"] for t in sel)
        w = sum(1 for t in sel if t["net"] > 0)
        print(f"{label:<22}{len(sel):>4}{gg:>+10.3f}{nn:>+10.3f}{nn/len(sel):>+11.3f}{w/len(sel)*100:>6.0f}%")

    block("ALL", trades)
    print()
    for leg in ("A->L", "L->NY"):
        block(f"  leg {leg}", [t for t in trades if t["leg"] == leg])
    print()
    for stp in ("SWEEP", "RANGE", "TREND"):
        block(f"  {stp}", [t for t in trades if t["setup"] == stp])
    print()
    for stp in ("SWEEP", "RANGE", "TREND"):
        for leg in ("A->L", "L->NY"):
            block(f"  {stp} {leg}", [t for t in trades if t["setup"] == stp and t["leg"] == leg])

    print(f"\nunfilled plans (limit never reached): {unfilled}")
    print(f"total cost drag: {sum(t['cost'] for t in trades):.3f}R "
          f"({sum(t['cost'] for t in trades)/n:.3f}R per trade)")

    m = st.mean(nt); sd = st.stdev(nt) if n > 1 else 0
    se = sd / math.sqrt(n)
    print(f"\nnet R per trade   mean {m:+.3f}   sd {sd:.3f}   n {n}")
    print(f"95% CI            [{m-1.96*se:+.3f}, {m+1.96*se:+.3f}]  "
          f"{'excludes zero' if m-1.96*se > 0 else '** SPANS ZERO **'}")
    wins = [x for x in nt if x > 0]
    losses = [-x for x in nt if x < 0]
    pf = (sum(wins) / sum(losses)) if losses else float("inf")
    print(f"profit factor     {pf:.3f}" + ("  (no losses — review)" if not losses else ""))
    eq, peak, dd = 0.0, 0.0, 0.0
    for t in trades:
        eq += t["net"]; peak = max(peak, eq); dd = max(dd, peak - eq)
    print(f"max drawdown      {dd:.3f}R")

    print(f"\nagainst config/lifecycle.json Stage-2 thresholds:")
    for lab, ok, got in (("trades >= 50", n >= 50, n),
                         ("expectancy >= 0.10R", m >= 0.10, f"{m:+.3f}"),
                         ("profit factor >= 1.20", pf >= 1.20, f"{pf:.3f}"),
                         ("max drawdown <= 10R", dd <= 10, f"{dd:.3f}")):
        print(f"  {'PASS' if ok else 'FAIL'}  {lab:<24}{got}")
    print("\nIN-SAMPLE. 15 days, one instrument. Not a Stage-2 result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
