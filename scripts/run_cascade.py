#!/usr/bin/env python3
"""
Run both cascade legs over a date range and print a ticket per leg.

    LEG 1   reference ASIAN  00:00-07:00 UTC  ->  execution LONDON   07:00-16:00
    LEG 2   reference LONDON 07:00-12:00 UTC  ->  execution NEW YORK 12:00-18:00

Implements STRATEGY_SPEC.md §0 as written — no momentum filter, no cooldown,
no session-loss lock. Outcomes are shown under several position-hold policies
because §0 does not specify one (see §9).

    python scripts/run_cascade.py --from 2022-10-03 --to 2022-10-05
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_golden_oct3 as V  # noqa: E402

PIP = 0.0001
LEGS = [
    ("LEG 1  ASIAN -> LONDON", (0, 7), (7, 16)),
    ("LEG 2  LONDON -> NEW YORK", (7, 12), (12, 18)),
]


def run_leg(bars, D, ref_hrs, ex_hrs, label):
    rs, re = ref_hrs
    xs, xe = ex_hrs
    ref = V.window(bars, D.replace(hour=rs), D.replace(hour=re))
    ex = V.window(bars, D.replace(hour=xs), D.replace(hour=xe))
    print(f"\n  {label}")
    if len(ref) < 8:
        print("    no reference bars"); return
    lv = V.classify(ref)
    arrow = {"BULLISH_TREND": "up trend", "BEARISH_TREND": "down trend",
             "RANGE": "no trend", "UNCERTAIN": "undecided"}[lv["type"]]
    print(f"    reference {rs:02d}:00-{re:02d}:00 UTC · {lv['n']} bars · "
          f"H {lv['high']:.5f}  L {lv['low']:.5f}  range {lv['range']/PIP:.1f}p")
    print(f"    ER {lv['er']:.3f}  close_loc {lv['loc']:.3f}  ->  {lv['type']} ({arrow})")
    print(f"    R = 25% of range = {lv['R']/PIP:.3f}p   midpoint {lv['mid']:.5f}")

    sig = V.detect(lv, ex)
    for t, s, why in sig.get("rejected", []):
        print(f"    · rejected {t:%H:%M}Z {s}: {why}")
    if not sig.get("setup"):
        print(f"    RESULT: NO TRADE — {sig.get('reason')}")
        return

    d = sig["dir"]
    partial_r = abs(sig["entry"] - sig["tp1"]) / lv["R"]
    print(f"    SETUP: {sig['setup']}  {d}   signal {sig['bar']['t']:%H:%M}Z")
    print(f"      Entry        {sig['entry']:.5f}")
    print(f"      Stop loss    {sig['sl']:.5f}   ({abs(sig['sl']-sig['entry'])/PIP:.1f}p = 1R)")
    print(f"      TP1  75% off {sig['tp1']:.5f}   ({partial_r:.2f}R) then stop -> breakeven")
    print(f"      TP2  runner  {sig['tp2']:.5f}   (5R)")
    for lbl, he in (("run to stop/target", None),
                    (f"close {xe:02d}:00", D.replace(hour=xe)),
                    ("close 22:00", D.replace(hour=22))):
        k, r, mfe = V.simulate(sig, bars, lv["R"], he)
        print(f"      {lbl:<20}{k:<24}{r:+.3f}R   (best {mfe:.2f}R)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d0", required=True)
    ap.add_argument("--to", dest="d1", required=True)
    a = ap.parse_args()
    bars = V.load_bars()
    d0 = dt.datetime.strptime(a.d0, "%Y-%m-%d")
    d1 = dt.datetime.strptime(a.d1, "%Y-%m-%d")

    print(f"CASCADE RUN  {a.d0} .. {a.d1}   EURUSD M15  ·  ASIAN_SESSION_V1 §0")
    print(f"fixture: data/eurusd_m15_2022_10_utc.csv  (UTC, VT Markets, offset +3)")
    D = d0
    while D <= d1:
        if D.weekday() < 5:
            print(f"\n{'='*74}\n{D:%A %d %B %Y}\n{'='*74}")
            for label, rh, xh in LEGS:
                run_leg(bars, D, rh, xh, label)
        D += dt.timedelta(days=1)
    print("\nAnalysis only. Levels are proposals, not signals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
