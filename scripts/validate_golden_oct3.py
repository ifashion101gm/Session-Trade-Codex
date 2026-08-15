#!/usr/bin/env python3
"""
Engine validation — 2022-10-03 only, both cascade legs, against
benchmarks/truth_source_setups.json.

Implements STRATEGY_SPEC.md §0 exactly as written. No momentum filter, no
cooldown, no session-loss lock — those constants live in
asian_session_backtester.py and appear nowhere in §0 (defect D2).

    python scripts/validate_golden_oct3.py

Fixture: data/eurusd_m15_2022_10_utc.csv  (UTC, from a VT Markets MT5 export)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "data" / "eurusd_m15_2022_10_utc.csv"
TRUTH = ROOT / "benchmarks" / "truth_source_setups.json"

PIP = 0.0001
SWEEP_BUFFER_FRACTION = 0.02
STOP_BUFFER_FRACTION = 0.02
TOUCH_TOLERANCE_FRACTION = 0.05
REJECTION_QUALITY_FRACTION = 0.50
ER_RANGE_MAX = 0.35
TREND_CLOSE_LOCATION = 0.65
RISK_FRACTION = 0.25          # stop = 25% of range
TP2_R = 5.0


def load_bars():
    bars = []
    with open(FIXTURE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            bars.append({
                "t": dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                "o": float(r["open"]), "h": float(r["high"]),
                "l": float(r["low"]), "c": float(r["close"]),
                "sp": int(r["spread"]) if r.get("spread") else 0,
            })
    bars.sort(key=lambda b: b["t"])
    return bars


def window(bars, start, end):
    return [b for b in bars if start <= b["t"] < end]


def classify(ref):
    hi = max(b["h"] for b in ref)
    lo = min(b["l"] for b in ref)
    rng = hi - lo
    op, cl = ref[0]["o"], ref[-1]["c"]
    er = abs(cl - op) / rng
    loc = (cl - lo) / rng
    if er <= ER_RANGE_MAX:
        st = "RANGE"
    elif loc >= TREND_CLOSE_LOCATION and cl > op:
        st = "BULLISH_TREND"
    elif loc <= (1 - TREND_CLOSE_LOCATION) and cl < op:
        st = "BEARISH_TREND"
    else:
        st = "UNCERTAIN"
    return {"high": hi, "low": lo, "range": rng, "mid": lo + 0.5 * rng,
            "lq": lo + 0.25 * rng, "uq": hi - 0.25 * rng,
            "open": op, "close": cl, "er": er, "loc": loc,
            "type": st, "R": RISK_FRACTION * rng, "n": len(ref)}


def detect(lv, ex):
    """§0.6 -> §0.7 -> §0.8, first qualifying closed candle. Returns a signal dict."""
    sb = SWEEP_BUFFER_FRACTION * lv["range"]
    stb = STOP_BUFFER_FRACTION * lv["range"]
    tt = TOUCH_TOLERANCE_FRACTION * lv["range"]
    R = lv["R"]
    rejected = []

    if lv["type"] == "RANGE":
        # --- Setup A: liquidity sweep ---
        for b in ex:
            cr = b["h"] - b["l"]
            if cr <= 0:
                continue
            # short: sweep the high
            if b["h"] > lv["high"] + sb and b["c"] < lv["high"] and b["o"] < lv["high"]:
                if b["c"] > b["h"] - REJECTION_QUALITY_FRACTION * cr:
                    rejected.append((b["t"], "SWEEP_SHORT", "rejection quality"))
                    continue
                entry = max(b["o"], b["c"])
                sl = entry + R
                if not (sl > b["h"] + stb):
                    rejected.append((b["t"], "SWEEP_SHORT", "FIXED_STOP_NOT_BEYOND_SWEEP"))
                    continue
                return {"setup": "SWEEP", "dir": "SHORT", "bar": b, "entry": entry,
                        "sl": sl, "tp1": lv["low"], "tp2": entry - TP2_R * R,
                        "rejected": rejected}
            # long: sweep the low
            if b["l"] < lv["low"] - sb and b["c"] > lv["low"] and b["o"] > lv["low"]:
                if b["c"] < b["l"] + REJECTION_QUALITY_FRACTION * cr:
                    rejected.append((b["t"], "SWEEP_LONG", "rejection quality"))
                    continue
                entry = min(b["o"], b["c"])
                sl = entry - R
                if not (sl < b["l"] - stb):
                    rejected.append((b["t"], "SWEEP_LONG", "FIXED_STOP_NOT_BEYOND_SWEEP"))
                    continue
                return {"setup": "SWEEP", "dir": "LONG", "bar": b, "entry": entry,
                        "sl": sl, "tp1": lv["high"], "tp2": entry + TP2_R * R,
                        "rejected": rejected}
        # --- Setup B: range rejection ---
        for b in ex:
            if b["h"] >= lv["high"] - tt and b["c"] < lv["high"] and b["c"] < b["o"] and b["o"] < lv["high"]:
                e = lv["high"]
                return {"setup": "RANGE_REJECTION", "dir": "SHORT", "bar": b, "entry": e,
                        "sl": e + R, "tp1": lv["low"], "tp2": e - TP2_R * R,
                        "rejected": rejected}
            if b["l"] <= lv["low"] + tt and b["c"] > lv["low"] and b["c"] > b["o"] and b["o"] > lv["low"]:
                e = lv["low"]
                return {"setup": "RANGE_REJECTION", "dir": "LONG", "bar": b, "entry": e,
                        "sl": e - R, "tp1": lv["high"], "tp2": e + TP2_R * R,
                        "rejected": rejected}
        return {"setup": None, "reason": "NO_QUALIFYING_SETUP", "rejected": rejected}

    if lv["type"] in ("BULLISH_TREND", "BEARISH_TREND"):
        # §0.8 — "An opposite-quartile violation cancels the pending trend setup for
        # the session." This is a SESSION-level latch, not a per-candle filter.
        zlo = lv["low"] + 0.45 * lv["range"]
        zhi = lv["low"] + 0.55 * lv["range"]
        bull = lv["type"] == "BULLISH_TREND"
        R = lv["R"]
        for b in ex:
            violated = (b["l"] < lv["lq"]) if bull else (b["h"] > lv["uq"])
            if violated:
                rejected.append((b["t"], "TREND_CONTINUATION",
                                 f"OPPOSITE_QUARTILE_VIOLATED "
                                 f"({b['l' if bull else 'h']:.5f} vs "
                                 f"{lv['lq' if bull else 'uq']:.5f}) — setup cancelled for the session"))
                return {"setup": None, "reason": "TREND_CANCELLED_OPPOSITE_QUARTILE",
                        "rejected": rejected}
            in_zone = (zlo <= b["l"] <= zhi) or (zlo <= b["h"] <= zhi) or \
                      (b["l"] < zlo and b["h"] > zhi)
            if not in_zone:
                continue
            if bull and b["c"] > b["o"]:
                e = lv["mid"]
                return {"setup": "TREND_CONTINUATION", "dir": "LONG", "bar": b, "entry": e,
                        "sl": e - R, "tp1": e + 4 * R, "tp2": e + TP2_R * R,
                        "rejected": rejected}
            if (not bull) and b["c"] < b["o"]:
                e = lv["mid"]
                return {"setup": "TREND_CONTINUATION", "dir": "SHORT", "bar": b, "entry": e,
                        "sl": e + R, "tp1": e - 4 * R, "tp2": e - TP2_R * R,
                        "rejected": rejected}
        return {"setup": None, "reason": "NO_QUALIFYING_SETUP", "rejected": rejected}

    return {"setup": None, "reason": "SESSION_UNCERTAIN", "rejected": rejected}


def simulate(sig, bars, R, hold_end=None):
    """STOP_FIRST. Partial 75% at tp1 then stop to breakeven. Returns (label, R, mfe)."""
    short = sig["dir"] == "SHORT"
    e, sl, tp1, tp2 = sig["entry"], sig["sl"], sig["tp1"], sig["tp2"]
    fwd = [b for b in bars if b["t"] > sig["bar"]["t"]]
    partial = False
    banked = 0.0
    mfe = 0.0
    for b in fwd:
        fav = (e - b["l"]) if short else (b["h"] - e)
        mfe = max(mfe, fav / R)
        if hold_end and b["t"] >= hold_end:
            r = ((e - b["o"]) if short else (b["o"] - e)) / R
            return (f"WINDOW_CLOSE {b['t']:%H:%M}", banked + r * (0.25 if partial else 1.0), mfe)
        hit_stop = b["h"] >= sl if short else b["l"] <= sl
        hit_tp2 = b["l"] <= tp2 if short else b["h"] >= tp2
        if hit_stop:                       # STOP_FIRST
            r = 0.0 if partial else -1.0
            return ("BREAKEVEN" if partial else "STOP_LOSS", banked + r * (0.25 if partial else 1.0), mfe)
        if hit_tp2:
            return ("TP5_HIT", banked + TP2_R * (0.25 if partial else 1.0), mfe)
        if not partial:
            hit_tp1 = b["l"] <= tp1 if short else b["h"] >= tp1
            if hit_tp1:
                partial = True
                banked = ((e - tp1) if short else (tp1 - e)) / R * 0.75
                sl = e
    return ("OPEN_AT_DATA_END", banked, mfe)


def run_leg(name, bars, ref_start, ref_end, ex_start, ex_end, truth):
    print(f"\n{'='*74}\n{name}\n{'='*74}")
    ref = window(bars, ref_start, ref_end)
    print(f"reference {ref_start:%H:%M}-{ref_end:%H:%M} UTC   {len(ref)} M15 bars")
    if not ref:
        print("  NO BARS — leg skipped"); return
    lv = classify(ref)
    print(f"  high {lv['high']:.5f}   low {lv['low']:.5f}   range {lv['range']/PIP:.1f}p")
    print(f"  open {lv['open']:.5f}  close {lv['close']:.5f}")
    print(f"  ER {lv['er']:.3f}  close_loc {lv['loc']:.3f}  ->  {lv['type']}")
    print(f"  R (25% of range) = {lv['R']/PIP:.3f} pips")

    ex = window(bars, ex_start, ex_end)
    sig = detect(lv, ex)
    for t, s, why in sig.get("rejected", []):
        print(f"  rejected {t:%H:%M}Z  {s}: {why}")
    if not sig.get("setup"):
        print(f"  NO_TRADE — {sig.get('reason')}"); return

    print(f"\nSIGNAL  {sig['setup']} {sig['dir']}  at {sig['bar']['t']:%Y-%m-%d %H:%M}Z")
    print(f"  entry {sig['entry']:.5f}   stop {sig['sl']:.7f}   "
          f"TP1 {sig['tp1']:.5f}   TP2(5R) {sig['tp2']:.7f}")

    if truth:
        print("\n  vs USER_CONFIRMED_TRUTH:")
        checks = [
            ("reference_high", lv["high"], truth["reference_high"]),
            ("reference_low", lv["low"], truth["reference_low"]),
            ("range_pips", round(lv["range"] / PIP, 1), truth["reference_range_pips"]),
            ("setup", sig["setup"], truth["setup"]),
            ("direction", sig["dir"], truth["direction"]),
            ("signal_time", f"{sig['bar']['t']:%Y-%m-%dT%H:%M:00Z}", truth["signal_time"]),
            ("entry", round(sig["entry"], 5), truth["entry"]),
            ("stop", round(sig["sl"], 7), round(truth["stop"], 7)),
            ("partial", round(sig["tp1"], 5), truth["leg_a_75pct_target"]),
            ("target_5r", round(sig["tp2"], 7), round(truth["target_5r"], 7)),
        ]
        ok = 0
        for k, got, want in checks:
            same = (abs(got - want) < 1e-6) if isinstance(got, float) else (str(got) == str(want))
            ok += same
            print(f"    {'PASS' if same else 'FAIL'}  {k:<15} engine={got}   truth={want}")
        print(f"    ---- {ok}/{len(checks)} fields match ----")

    print("\n  outcome under each position-hold policy:")
    for lbl, he in (("no time exit (§0 as written)", None),
                    ("hold to 16:00 UTC", dt.datetime(2022, 10, 3, 16)),
                    ("hold to 18:00 UTC", dt.datetime(2022, 10, 3, 18)),
                    ("hold to 22:00 UTC", dt.datetime(2022, 10, 3, 22))):
        k, r, mfe = simulate(sig, bars, lv["R"], he)
        print(f"    {lbl:<30} {k:<22} {r:+.3f}R   (MFE {mfe:.2f}R)")
    if truth:
        tr = truth.get("target_r")
        tr = f"{tr:+.3f}R" if isinstance(tr, (int, float)) else "n/a"
        print(f"    {'truth':<30} {truth.get('outcome','?'):<22} {tr}")


def main():
    if not FIXTURE.exists():
        sys.exit(f"missing fixture: {FIXTURE}")
    bars = load_bars()
    truths = {b["id"]: b for b in json.load(open(TRUTH))["benchmarks"]}
    D = dt.date(2022, 10, 3)
    print(f"ENGINE VALIDATION — {D} only")
    print(f"fixture {FIXTURE.name}: {len(bars)} bars, "
          f"{bars[0]['t']:%Y-%m-%d %H:%M} .. {bars[-1]['t']:%Y-%m-%d %H:%M} UTC")

    run_leg("LEG 1 — reference ASIAN 00:00-07:00  ->  execution LONDON 07:00-16:00",
            bars, dt.datetime(2022, 10, 3, 0), dt.datetime(2022, 10, 3, 7),
            dt.datetime(2022, 10, 3, 7), dt.datetime(2022, 10, 3, 16),
            truths.get("eurusd-2022-10-03-asian-to-london-short-sweep"))

    run_leg("LEG 2 — reference LONDON 07:00-12:00  ->  execution NEW YORK 12:00-18:00",
            bars, dt.datetime(2022, 10, 3, 7), dt.datetime(2022, 10, 3, 12),
            dt.datetime(2022, 10, 3, 12), dt.datetime(2022, 10, 3, 18),
            truths.get("eurusd-2022-10-03-london-to-new-york-short-sweep"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
