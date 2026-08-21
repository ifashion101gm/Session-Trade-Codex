#!/usr/bin/env python3
"""
SESSION_FLOW_V1 — canonical engine.

CORRECTED 2026-08-15. "SWEEP DURING SESSION?" refers to the REFERENCE session,
not the execution session. All three questions are therefore answerable the
moment the reference session closes, which is what makes the desk workflow work:
one run at the reference close, one report, one resting order.

    RUN 1   07:00 UTC   Asian complete   ->  plan for LONDON
    RUN 2   12:00 UTC   London complete  ->  plan for NEW YORK

THE THREE QUESTIONS, all answered from the completed reference session:

  1  bull or bear?     close_location >= 0.50 -> BULL, else BEAR
  2  range or trend?   efficiency_ratio <= er_max -> RANGE, else TREND
  3  swept?            did the candle that MADE the relevant extreme close
                       its BODY back inside the range?
                         bear -> look at the session high
                         bull -> look at the session low
                       body back inside  ->  SWEEP SETUP
                       body at the extreme (no rejection) -> RANGE SETUP

THE THREE SETUPS

  SWEEP   entry = the sweep candle's body edge   max(o,c) bear / min(o,c) bull
  RANGE   entry = the session boundary            high bear / low bull
  TREND   entry = the midpoint

  all three:  stop = entry -/+ 25% of range       target = 5R
  management: SWEEP/RANGE  75% at the opposite boundary, then breakeven
              TREND        75% at 4R, then trail (unsigned)

Every entry is a resting limit, fixed at the reference close. Nothing is watched.

    python scripts/session_flow.py --from 2022-10-03 --to 2022-10-21
    python scripts/session_flow.py --date 2022-10-03 --report
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
LEGS = [("A->L", "ASIAN", "LONDON", (0, 7), (7, 16)),
        ("L->NY", "LONDON", "NEW YORK", (7, 12), (12, 18))]


def levels(ref):
    hi = max(b["h"] for b in ref)
    lo = min(b["l"] for b in ref)
    rng = hi - lo
    o, c = ref[0]["o"], ref[-1]["c"]
    loc = (c - lo) / rng if rng else 0.5
    return {"hi": hi, "lo": lo, "rng": rng, "R": 0.25 * rng, "mid": lo + 0.5 * rng,
            "o": o, "c": c, "n": len(ref), "loc": loc,
            "er": abs(c - o) / rng if rng else 0.0,
            "bias": "BULL" if loc >= 0.50 else "BEAR"}


THETA_REJ = 0.05          # signed 2026-08-16 — see Q3 below


def plan(ref, lv, er_max, theta_rej=THETA_REJ):
    """All three questions, answered from the reference session alone."""
    bear = lv["bias"] == "BEAR"
    sgn = -1 if bear else 1          # direction multiplier for a short/long
    R = lv["R"]

    if lv["er"] > er_max:
        e = lv["mid"]
        return dict(setup="TREND", dir="SHORT" if bear else "LONG", entry=e,
                    sl=e - sgn * R, tp1=e + sgn * 4 * R, tp2=e + sgn * TP2_R * R,
                    swept=None, sweep_bar=None)

    # Q3 — did the candle that made the relevant extreme REJECT it?
    #
    # SIGNED 2026-08-16.  The old test was `body < ext`, which is true unless the
    # candle closed exactly on its own extreme — so SWEEP fired 1486/1486 and
    # RANGE was unreachable code.  A body edge is always inside its own wick;
    # asking "is it inside" asks nothing.  The question is HOW FAR inside, as a
    # fraction of the session range:
    #
    #     rejection_ratio = (high - body_high) / range     bear
    #                     = (body_low - low)   / range     bull
    #
    #   >= THETA_REJ  ->  liquidity was pushed back  ->  SWEEP
    #   <  THETA_REJ  ->  price held at the boundary ->  RANGE
    #
    # THETA_REJ is [UNSIGNED-derived]: chosen on the 1486-session distribution
    # (median 0.089) to land RANGE at 27.3%, inside the 20-50% acceptance band.
    # It is a declared parameter, not a source rule.  Registry: AGENT_SKILLS B7.
    # FIX 1, 2026-08-17 — detect BOTH sides independently, then let the swept
    # side choose the direction.
    #
    # The old code did:   bias -> pick a side -> look for a sweep there
    # which finds the sweep it already expects. The source says the opposite:
    # observe which boundary was swept, and trade AWAY from it. Under the old
    # form that rule never executed.
    def _rejection(high_side):
        ext = lv["hi"] if high_side else lv["lo"]
        sw = [b for b in ref if (b["h"] if high_side else b["l"]) == ext][-1]
        body = max(sw["o"], sw["c"]) if high_side else min(sw["o"], sw["c"])
        rej = ((ext - body) if high_side else (body - ext)) / lv["rng"] if lv["rng"] else 0.0
        return rej, sw, body

    rej_h, sw_h, body_h = _rejection(True)
    rej_l, sw_l, body_l = _rejection(False)
    high_swept, low_swept = rej_h >= theta_rej, rej_l >= theta_rej

    if high_swept and low_swept:
        # both extremes rejected — take the LATER one, it is the live liquidity
        # event going into the execution session.  [UNSIGNED — declared]
        take_high = sw_h["t"] >= sw_l["t"]
    elif high_swept or low_swept:
        take_high = high_swept
    else:
        take_high = None

    if take_high is not None:
        # SWEEP — direction is set by the SWEPT SIDE, not by bias
        e = body_h if take_high else body_l
        sgn_s = -1 if take_high else 1            # high swept -> SHORT
        return dict(setup="SWEEP", dir="SHORT" if take_high else "LONG", entry=e,
                    sl=e - sgn_s * R, tp1=lv["lo"] if take_high else lv["hi"],
                    tp2=e + sgn_s * TP2_R * R, swept=True,
                    sweep_bar=sw_h if take_high else sw_l,
                    dir_source="swept_side", both_swept=high_swept and low_swept,
                    rej_high=rej_h, rej_low=rej_l)

    # RANGE — neither extreme rejected. Bias is the SELECTOR here, and only here:
    # bull buys the bottom, bear sells the top.  (§1 ruling: no NO-TRADE terminal.)
    e = lv["hi"] if bear else lv["lo"]
    return dict(setup="RANGE", dir="SHORT" if bear else "LONG", entry=e,
                sl=e - sgn * R, tp1=lv["lo"] if bear else lv["hi"],
                tp2=e + sgn * TP2_R * R, swept=False,
                sweep_bar=sw_h if bear else sw_l,
                dir_source="bias_selector", both_swept=False,
                rej_high=rej_h, rej_low=rej_l)


def simulate(p, lv, ex, forward):
    """Resting limit. STOP_FIRST. 75% at tp1 then stop to breakeven."""
    short = p["dir"] == "SHORT"
    e, sl, tp1, tp2, R = p["entry"], p["sl"], p["tp1"], p["tp2"], lv["R"]
    fill = next((b for b in ex if (b["h"] >= e if short else b["l"] <= e)), None)
    if not fill:
        return dict(fill=None, outcome="UNFILLED", r=0.0, mfe=0.0)
    after = [b for b in forward if b["t"] > fill["t"]]
    partial = False
    banked = 0.0
    pr = abs(e - tp1) / R
    mfe = 0.0
    for b in after:
        fav = (e - b["l"]) if short else (b["h"] - e)
        mfe = max(mfe, fav / R)
        if (b["h"] >= sl) if short else (b["l"] <= sl):
            r = banked + (0.0 if partial else -1.0)
            return dict(fill=fill, outcome="BREAKEVEN" if partial else "STOP_LOSS",
                        r=r, mfe=mfe)
        if (b["l"] <= tp2) if short else (b["h"] >= tp2):
            r = banked + TP2_R * (0.25 if partial else 1.0)
            return dict(fill=fill, outcome="TP5_HIT", r=r, mfe=mfe)
        if not partial and ((b["l"] <= tp1) if short else (b["h"] >= tp1)):
            partial = True
            banked = pr * 0.75
            sl = e
    return dict(fill=fill, outcome="OPEN_AT_END", r=banked, mfe=mfe)


def run_day(bars, D, er_max, verbose):
    rows = []
    for tag, rn, xn, (rs, re), (xs, xe) in LEGS:
        ref = V.window(bars, D.replace(hour=rs), D.replace(hour=re))
        ex = V.window(bars, D.replace(hour=xs), D.replace(hour=xe))
        if len(ref) < 8 or len(ex) < 8:
            continue
        lv = levels(ref)
        p = plan(ref, lv, er_max)
        fwd = [b for b in bars if b["t"] >= D.replace(hour=xs)]
        s = simulate(p, lv, ex, fwd)
        rows.append((D, tag, rn, xn, lv, p, s))
        if verbose:
            print(f"\n{'='*70}\nRUN · {re:02d}:00 UTC · {rn} complete → plan for {xn}\n{'='*70}")
            print(f"  {rn} {rs:02d}:00–{re:02d}:00 · {lv['n']} bars · "
                  f"H {lv['hi']:.5f}  L {lv['lo']:.5f}  range {lv['rng']/PIP:.1f}p")
            print(f"  1 bias      close_loc {lv['loc']:.3f} → {lv['bias']}")
            print(f"  2 range?    ER {lv['er']:.3f} → {'RANGE' if lv['er']<=er_max else 'TREND'}")
            if p["sweep_bar"] is not None:
                sw = p["sweep_bar"]
                print(f"  3 swept?    extreme made {sw['t']:%H:%M}Z  "
                      f"O {sw['o']:.5f} C {sw['c']:.5f} → {'YES' if p['swept'] else 'NO'}")
            print(f"\n  {p['setup']} {p['dir']}   R = {lv['R']/PIP:.3f}p")
            print(f"    entry  {p['entry']:.5f}   (resting limit, fixed now)")
            print(f"    stop   {p['sl']:.5f}")
            print(f"    TP1    {p['tp1']:.5f}   ({abs(p['entry']-p['tp1'])/lv['R']:.2f}R) → breakeven")
            print(f"    TP2    {p['tp2']:.5f}   (5R)")
            if s["fill"]:
                print(f"\n  filled {s['fill']['t']:%H:%M}Z → {s['outcome']}  {s['r']:+.3f}R  (best {s['mfe']:.2f}R)")
            else:
                print(f"\n  {s['outcome']}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d0")
    ap.add_argument("--to", dest="d1")
    ap.add_argument("--date")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--er-max", type=float, default=0.35)
    a = ap.parse_args()
    bars = V.load_bars()
    if a.date:
        d0 = d1 = dt.datetime.strptime(a.date, "%Y-%m-%d")
    else:
        d0 = dt.datetime.strptime(a.d0, "%Y-%m-%d")
        d1 = dt.datetime.strptime(a.d1, "%Y-%m-%d")

    print(f"SESSION_FLOW_V1 · sweep read in the REFERENCE session · ER≤{a.er_max}")
    all_rows = []
    D = d0
    while D <= d1:
        if D.weekday() < 5:
            if a.report:
                print(f"\n{D:%A %d %B %Y}")
            all_rows += run_day(bars, D, a.er_max, a.report)
        D += dt.timedelta(days=1)

    if not a.report:
        print(f"\n{'date':<11}{'leg':<7}{'bias':<6}{'setup':<7}{'dir':<6}"
              f"{'entry':>9}{'stop':>9}{'TP1':>9}{'TP2':>9}{'fill':>7}{'R':>9}")
        tot = fired = 0.0, 0
        net = 0.0
        n_fill = 0
        for D, tag, rn, xn, lv, p, s in all_rows:
            f = f"{s['fill']['t']:%H:%M}" if s["fill"] else "—"
            print(f"{D:%Y-%m-%d} {tag:<7}{lv['bias']:<6}{p['setup']:<7}{p['dir']:<6}"
                  f"{p['entry']:>9.5f}{p['sl']:>9.5f}{p['tp1']:>9.5f}{p['tp2']:>9.5f}"
                  f"{f:>7}{s['r']:>+9.3f}  {s['outcome']}")
            net += s["r"]
            n_fill += 1 if s["fill"] else 0
        n = len(all_rows)
        print(f"\n{n_fill}/{n} filled ({n_fill/n*100:.0f}%)   net {net:+.3f}R   "
              f"mean {net/n_fill if n_fill else 0:+.3f}R per filled trade")
    print("\nAnalysis only. In-sample. §4-A/B/C unsigned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
