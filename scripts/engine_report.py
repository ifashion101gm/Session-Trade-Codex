#!/usr/bin/env python3
"""
SESSION_FLOW_V1 — the desk report.

The engine runs TWICE a day, at the close of each reference session, when that
session's data is complete. Each run produces one report for the session that
follows.

    RUN 1   07:00 UTC   Asian complete   ->  report on the LONDON session
    RUN 2   12:00 UTC   London complete  ->  report on the NEW YORK session

Each report reads exactly one range and nothing else (spec §5).

RANGE and TREND entries are resting limits and are final at the reference close.
A SWEEP entry is not — the sweep candle has not printed yet. Per spec §5.3a the
working default is option 1: the report states the range/trend limit AND the
sweep levels to watch, so one report covers the whole session.

    python scripts/engine_report.py --date 2022-10-03
    python scripts/engine_report.py --date 2022-10-03 --run 1
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_golden_oct3 as V  # noqa: E402
import run_flowchart as F  # noqa: E402

PIP = 0.0001
RUNS = [
    (1, "ASIAN", "LONDON", (0, 7), (7, 16)),
    (2, "LONDON", "NEW YORK", (7, 12), (12, 18)),
]


def report(bars, D, run_no, ref_name, exec_name, ref_hrs, exec_hrs, er_max, bias_mode):
    rs, re = ref_hrs
    xs, xe = exec_hrs
    ref = V.window(bars, D.replace(hour=rs), D.replace(hour=re))
    ex = V.window(bars, D.replace(hour=xs), D.replace(hour=xe))

    print(f"\n{'='*72}")
    print(f"RUN {run_no} · {re:02d}:00 UTC · {ref_name} complete → report on the {exec_name} session")
    print(f"{'='*72}")
    if len(ref) < 8:
        print("  INSUFFICIENT REFERENCE DATA — no report")
        return
    lv = F.levels(ref, bias_mode)
    R = lv["R"]
    is_range = lv["er"] <= er_max

    print(f"\nREFERENCE — {ref_name} {rs:02d}:00–{re:02d}:00 UTC · {lv['n']} closed M15 bars")
    print(f"  high      {lv['hi']:.5f}")
    print(f"  low       {lv['lo']:.5f}")
    print(f"  range     {lv['rng']/PIP:.1f} pips")
    print(f"  midpoint  {lv['mid']:.5f}")
    print(f"  1R        {R/PIP:.3f} pips   (25% of range)")

    print(f"\nDECISIONS")
    print(f"  1  bull or bear?     close_location {lv['loc']:.3f}  →  {lv['bias']}")
    print(f"  2  range or trend?   ER {lv['er']:.3f}  →  {'RANGE' if is_range else 'TREND'}")

    print(f"\nPLAN FOR THE {exec_name} SESSION  ({xs:02d}:00–{xe:02d}:00 UTC)")
    if not is_range:
        d = "LONG" if lv["bias"] == "BULL" else "SHORT"
        sgn = 1 if d == "LONG" else -1
        e = lv["mid"]
        print(f"  TREND SETUP · {d}")
        print(f"    place        {'BUY' if d=='LONG' else 'SELL'} LIMIT at the midpoint  {e:.5f}")
        print(f"    stop         {e - sgn*R:.5f}")
        print(f"    TP1  75%     {e + sgn*4*R:.5f}   (4R)  → then trail (§4-C unsigned)")
        print(f"    TP2  runner  {e + sgn*5*R:.5f}   (5R)")
        print(f"    if price never trades the midpoint, the order does not fill")
    else:
        d = "LONG" if lv["bias"] == "BULL" else "SHORT"
        sgn = 1 if d == "LONG" else -1
        e = lv["lo"] if d == "LONG" else lv["hi"]
        opp = lv["hi"] if d == "LONG" else lv["lo"]
        print(f"  RANGE SETUP · {d}   — resting order, final now")
        print(f"    place        {'BUY' if d=='LONG' else 'SELL'} LIMIT at the session "
              f"{'low' if d=='LONG' else 'high'}  {e:.5f}")
        print(f"    stop         {e - sgn*R:.5f}")
        print(f"    TP1  75%     {opp:.5f}   (4.00R)  → then breakeven")
        print(f"    TP2  runner  {e + sgn*5*R:.5f}   (5R)")
        print(f"\n  SWEEP WATCH · {d}   — supersedes the resting order if it triggers")
        b = lv["hi"] if d == "SHORT" else lv["lo"]
        print(f"    trigger      a candle trades {'above' if d=='SHORT' else 'below'} {b:.5f} "
              f"and CLOSES back inside")
        print(f"    entry        that candle's body {'high' if d=='SHORT' else 'low'} "
              f"= {'max' if d=='SHORT' else 'min'}(open, close)")
        print(f"    stop         entry {'+' if d=='SHORT' else '−'} {R/PIP:.3f}p")
        print(f"    TP1  75%     {opp:.5f}  (the opposite boundary) → then breakeven")
        print(f"    TP2  runner  entry {'−' if d=='SHORT' else '+'} {5*R/PIP:.3f}p  (5R)")
        print(f"    entry is not computable until the candle closes — spec §5.3a")

    # what actually happened, for backtesting only
    s = F.detect(lv, ex, er_max)
    print(f"\nOUTCOME (historical replay — not part of the live report)")
    if not s.get("setup"):
        print(f"  {s['reason']}")
    else:
        k, r, mfe = V.simulate(s, bars, R, None)
        print(f"  {s['setup']} {s['dir']} filled {s['bar']['t']:%H:%M}Z at {s['entry']:.5f}"
              f"  →  {k}  {r:+.3f}R   (best {mfe:.2f}R)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--run", type=int, choices=[1, 2])
    ap.add_argument("--er-max", type=float, default=0.35)
    ap.add_argument("--bias", choices=["loc", "sign"], default="loc")
    a = ap.parse_args()

    bars = V.load_bars()
    D = dt.datetime.strptime(a.date, "%Y-%m-%d")
    print(f"SESSION_FLOW_V1 · EURUSD M15 · {D:%A %d %B %Y} · UTC")
    print(f"fixture data/eurusd_m15_2022_10_utc.csv · ER≤{a.er_max} · bias={a.bias}")
    for n, rn, xn, rh, xh in RUNS:
        if a.run and a.run != n:
            continue
        report(bars, D, n, rn, xn, rh, xh, a.er_max, a.bias)
    print("\nAnalysis only. §4-A, §4-B, §4-C and §5.3a unsigned. In-sample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
