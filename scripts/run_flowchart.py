#!/usr/bin/env python3
"""
SESSION_FLOW_V1 — the flowchart, literally.

Implements ONLY what the trader's strategy diagram contains:

    BIAS TREND (up/down)
        -> IS RANGE SESSION?  yes -> SWEEP DURING SESSION?  yes -> SWEEP SETUP
                                                            no  -> RANGE SETUP
                              no  -> TREND SETUP

    ENTRY       sweep candle body | session top/bottom | middle of the range
    STOPLOSS    25% of range   (all three)
    TARGET      5x risk to reward   (all three)
    MANAGEMENT  sweep/range: close 75% at session range, then breakeven
                trend:       close 75% at 4R, then trail

EVERYTHING ELSE IS REMOVED. Deleted relative to ASIAN_SESSION_V1 §0:
    sweep_buffer, stop_buffer, touch_tolerance, rejection_quality,
    structural-stop validation, "must open inside the boundary",
    midpoint zone + confirmation candle, opposite-quartile cancellation,
    the UNCERTAIN state, close_location.

FOUR DEFINITIONS THE DIAGRAM DOES NOT SUPPLY. Each is the most literal reading
available; each REQUIRES the trader's sign-off before this contract is used.

  D1  "IS RANGE SESSION?" is binary in the diagram, so there is no UNCERTAIN.
      Implemented as efficiency_ratio <= --er-max (default 0.35).
      The diagram supplies no formula or value.
  D2  "BIAS TREND" — TWO READINGS, and they disagree. Selectable with --bias:
        loc   (default) close_location: closed in the upper half = bullish.
                        Reproduces the USER_CONFIRMED_TRUTH bias for 2022-10-03.
        sign            sign(close - open). Gives BULLISH on 2022-10-03 and
                        therefore selects a LONG sweep the benchmark does not
                        contain. Do not use without re-deriving the benchmarks.
      Bias also gates which side of a sweep is eligible (§D3a), so this single
      definition changes the trade, not just the label.
  D3  "Session Top/Bottom" — bias picks the side: bullish buys the bottom,
      bearish sells the top.
  D4  "Middle of the range" is an unconfirmed limit at the midpoint, entered
      the first time price trades there. The diagram shows no confirmation.

    python scripts/run_flowchart.py --from 2022-10-03 --to 2022-10-21
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_golden_oct3 as V  # noqa: E402

PIP = 0.0001
TP2_R = 5.0


def levels(ref, bias_mode="loc"):
    hi = max(b["h"] for b in ref)
    lo = min(b["l"] for b in ref)
    rng = hi - lo
    o, c = ref[0]["o"], ref[-1]["c"]
    return {"hi": hi, "lo": lo, "rng": rng, "mid": lo + 0.5 * rng,
            "o": o, "c": c, "R": 0.25 * rng,
            "er": abs(c - o) / rng if rng else 0,
            "loc": (c - lo) / rng if rng else 0.5, "n": len(ref),
            "bias": ("BULL" if (c - lo) / rng >= 0.5 else "BEAR") if bias_mode == "loc"
                    else ("BULL" if c > o else "BEAR")}


def detect(lv, ex, er_max):
    """The diagram's three branches. No filters."""
    is_range = lv["er"] <= er_max

    if is_range:
        # SWEEP DURING SESSION?  any breach that closes back inside.
        # D3a: bias gates the eligible side — a bearish session sells the high.
        for b in ex:
            if lv["bias"] == "BEAR" and b["h"] > lv["hi"] and b["c"] < lv["hi"]:
                e = max(b["o"], b["c"])
                return dict(setup="SWEEP", dir="SHORT", bar=b, entry=e,
                            sl=e + lv["R"], tp1=lv["lo"], tp2=e - TP2_R * lv["R"])
            if lv["bias"] == "BULL" and b["l"] < lv["lo"] and b["c"] > lv["lo"]:
                e = min(b["o"], b["c"])
                return dict(setup="SWEEP", dir="LONG", bar=b, entry=e,
                            sl=e - lv["R"], tp1=lv["hi"], tp2=e + TP2_R * lv["R"])
        # no sweep -> RANGE SETUP, limit at the boundary chosen by bias (D3)
        if lv["bias"] == "BULL":
            e = lv["lo"]
            for b in ex:
                if b["l"] <= e:
                    return dict(setup="RANGE", dir="LONG", bar=b, entry=e,
                                sl=e - lv["R"], tp1=lv["hi"], tp2=e + TP2_R * lv["R"])
        else:
            e = lv["hi"]
            for b in ex:
                if b["h"] >= e:
                    return dict(setup="RANGE", dir="SHORT", bar=b, entry=e,
                                sl=e + lv["R"], tp1=lv["lo"], tp2=e - TP2_R * lv["R"])
        return dict(setup=None, reason="RANGE limit never touched")

    # TREND SETUP — unconfirmed limit at the midpoint (D4)
    e = lv["mid"]
    long_ = lv["bias"] == "BULL"
    for b in ex:
        if b["l"] <= e <= b["h"]:
            return dict(setup="TREND", dir="LONG" if long_ else "SHORT", bar=b, entry=e,
                        sl=e - lv["R"] if long_ else e + lv["R"],
                        tp1=e + 4 * lv["R"] if long_ else e - 4 * lv["R"],
                        tp2=e + TP2_R * lv["R"] if long_ else e - TP2_R * lv["R"])
    return dict(setup=None, reason="midpoint never touched")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d0", required=True)
    ap.add_argument("--to", dest="d1", required=True)
    ap.add_argument("--er-max", type=float, default=0.35)
    ap.add_argument("--bias", choices=["loc","sign"], default="loc")
    a = ap.parse_args()

    bars = V.load_bars()
    d0 = dt.datetime.strptime(a.d0, "%Y-%m-%d")
    d1 = dt.datetime.strptime(a.d1, "%Y-%m-%d")
    legs = [("A->L", (0, 7), (7, 16)), ("L->NY", (7, 12), (12, 18))]

    rows = []
    D = d0
    while D <= d1:
        if D.weekday() < 5:
            for tag, (rs, re), (xs, xe) in legs:
                ref = V.window(bars, D.replace(hour=rs), D.replace(hour=re))
                ex = V.window(bars, D.replace(hour=xs), D.replace(hour=xe))
                if len(ref) < 8 or len(ex) < 8:
                    continue
                lv = levels(ref, a.bias)
                s = detect(lv, ex, a.er_max)
                rows.append((D, tag, lv, s, xe))
        D += dt.timedelta(days=1)

    print(f"SESSION_FLOW_V1 — the diagram, literally.   {a.d0} .. {a.d1}   ER<= {a.er_max}  bias={a.bias}")
    print(f"{'date':<11}{'leg':<7}{'bias':<6}{'session':<8}{'setup':<7}{'dir':<6}"
          f"{'entry':>9}{'stop':>9}{'TP1':>9}{'TP2':>9}{'R@stop/tgt':>12}")
    fired = 0
    tot = 0.0
    for D, tag, lv, s, xe in rows:
        sess = "RANGE" if lv["er"] <= a.er_max else "TREND"
        if not s.get("setup"):
            print(f"{D:%Y-%m-%d} {tag:<7}{lv['bias']:<6}{sess:<8}{'—':<7}{'':<6}"
                  f"{'':>9}{'':>9}{'':>9}{'':>9}   no entry: {s['reason']}")
            continue
        fired += 1
        k, r, mfe = V.simulate(s, bars, lv["R"], None)
        tot += r
        print(f"{D:%Y-%m-%d} {tag:<7}{lv['bias']:<6}{sess:<8}{s['setup']:<7}{s['dir']:<6}"
              f"{s['entry']:>9.5f}{s['sl']:>9.5f}{s['tp1']:>9.5f}{s['tp2']:>9.5f}"
              f"{r:>+9.3f}R  {k}")
    n = len(rows)
    print(f"\n{fired}/{n} leg-runs produced an entry ({fired/n*100:.0f}%)   "
          f"net {tot:+.3f}R   mean {tot/fired if fired else 0:+.3f}R/trade")
    print("\nUnvalidated. Definitions D1-D4 are unsigned. Analysis only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
