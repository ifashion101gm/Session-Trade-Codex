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
import bisect
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
DATA = ROOT / "data"
LEGS = SF.LEGS


def load_master(path: Path):
    """Load a master CSV. POINT is inferred from the price precision in the file,
    so 5-digit FX, 3-digit JPY and 2-digit gold all work without a lookup table."""
    bars, digits = [], 0
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            for k in ("open", "high", "low", "close"):
                d = len(r[k].split(".")[1]) if "." in r[k] else 0
                digits = max(digits, d)
            bars.append({"t": dt.datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S"),
                         "o": float(r["open"]), "h": float(r["high"]),
                         "l": float(r["low"]), "c": float(r["close"]),
                         "sp": int(r["spread"]) if r["spread"] else 0})
    bars.sort(key=lambda b: b["t"])
    if digits > 8:
        raise SystemExit(
            f"{path.name}: inferred {digits} price decimals.\n"
            "  That is float-repr noise (e.g. 1.1614100000000001), not a real quote.\n"
            "  POINT would become 1e-{d} and every spread cost would round to ZERO,\n"
            "  so the backtest would silently report GROSS as if it were NET.\n"
            "  Fix: python scripts/repair_precision.py".format(d=digits))
    point = 10 ** (-digits)
    pip = point * 10 if digits >= 3 else point
    return bars, point, pip


def simulate(p, lv, ex, forward, slip_pips, policy="STOP_FIRST"):
    """Replay one plan.

    COLLISION. When a single bar's range contains BOTH the stop and a live
    target, no bar-level data can say which came first. `policy` decides:
    STOP_FIRST is the conservative default; TARGET_FIRST is the optimistic
    bound. Every such bar is flagged so the assumption can be costed instead
    of assumed away — run both and diff.
    """
    short = p["dir"] == "SHORT"
    e, sl, tp1, tp2, R = p["entry"], p["sl"], p["tp1"], p["tp2"], lv["R"]
    fill = next((b for b in ex if (b["h"] >= e if short else b["l"] <= e)), None)
    if not fill:
        return None
    after = [b for b in forward if b["t"] > fill["t"]]
    partial, banked, mfe, collided = False, 0.0, 0.0, False
    pr = abs(e - tp1) / R

    def done(b, outcome, gross):
        return dict(fill=fill, exit=b, outcome=outcome, gross=gross, mfe=mfe,
                    partial=partial, pr=pr, R=R, collided=collided)

    for b in after:
        mfe = max(mfe, ((e - b["l"]) if short else (b["h"] - e)) / R)
        hit_sl = (b["h"] >= sl) if short else (b["l"] <= sl)
        hit_2 = (b["l"] <= tp2) if short else (b["h"] >= tp2)
        hit_1 = (not partial) and ((b["l"] <= tp1) if short else (b["h"] >= tp1))
        if hit_sl and (hit_1 or hit_2):
            collided = True
        if hit_sl and policy == "STOP_FIRST":
            return done(b, "BREAKEVEN" if partial else "STOP_LOSS",
                        banked + (0.0 if partial else -1.0))
        if hit_2:
            return done(b, "TP5_HIT", banked + SF.TP2_R * (0.25 if partial else 1.0))
        if hit_sl:                      # TARGET_FIRST and no target on this bar
            return done(b, "BREAKEVEN" if partial else "STOP_LOSS",
                        banked + (0.0 if partial else -1.0))
        if hit_1:
            partial, banked, sl = True, pr * 0.75, e
    b = after[-1] if after else fill
    return done(b, "OPEN_AT_END", banked)


def is_range_source(ref, lv):
    """§4-B as the source spec states it, replacing the efficiency ratio.

        "YES - the session's M15 open and close both sit inside the middle
         portion of the range; price returned to both halves of the box."

    "Middle portion" carries no number in the source. Every other quantity in
    the system is a quarter of the range — the stop is 25%, the management level
    is the far boundary — so the middle portion is read as the **middle 50%**,
    the band between the 25% and 75% marks. That is the only reading consistent
    with the rest of the document; it is an interpretation and is flagged as one.
    """
    lo, hi = lv["lo"], lv["hi"]
    rng = hi - lo
    if rng <= 0:
        return True
    band_lo, band_hi = lo + 0.25 * rng, lo + 0.75 * rng
    o, c = ref[0]["o"], ref[-1]["c"]
    return band_lo <= o <= band_hi and band_lo <= c <= band_hi


def equity_curve(trades):
    """Realized equity in R, ordered by EXIT time across every symbol and both
    legs interleaved as they actually occurred. A drawdown taken over a pooled,
    symbol-major trade list is not a drawdown anyone experienced."""
    seq = sorted(trades, key=lambda t: t["exit_t"])
    eq = peak = dd = 0.0
    dd_at = dd_from = None
    pts = []
    for t in seq:
        eq += t["net"]
        if eq > peak:
            peak, dd_from = eq, t["exit_t"]
        if peak - eq > dd:
            dd, dd_at = peak - eq, t["exit_t"]
        pts.append((t["exit_t"], eq))
    return seq, pts, dd, dd_from, dd_at


def net_of(s, slip_pips, point, pip):
    cost_price = (s["fill"]["sp"] + s["exit"]["sp"]) * point + slip_pips * pip
    return s["gross"] - cost_price / s["R"], cost_price / s["R"]


def run_symbol(bars, point, pip, sym, a, policy="STOP_FIRST"):
    """Indexed with bisect. The naive version rescans all bars for every window,
    which is invisible on a 1,440-bar fixture and quadratic on a year of data —
    18k bars x 250 days x 2 legs was the difference between 2 seconds and never."""
    trades, unfilled = [], 0
    d0, d1 = bars[0]["t"], bars[-1]["t"]
    times = [b["t"] for b in bars]

    def wnd(t0, t1):                       # half-open [t0, t1), same as SF.V.window
        return bars[bisect.bisect_left(times, t0):bisect.bisect_left(times, t1)]

    by_day = defaultdict(list)
    for b in bars:
        by_day[b["t"].date()].append(b)
    D = dt.datetime(d0.year, d0.month, d0.day)
    while D <= d1:
        if D.weekday() < 5 and by_day.get(D.date()):
            for tag, rn, xn, (rs, re), (xs, xe) in LEGS:
                ref = wnd(D.replace(hour=rs), D.replace(hour=re))
                ex = wnd(D.replace(hour=xs), D.replace(hour=xe))
                if len(ref) < 8 or len(ex) < 8:
                    continue
                lv = SF.levels(ref)
                if a.range_test == "source":
                    # force the branch, leave every other rule untouched, so the
                    # delta is attributable to §4-B alone
                    p = SF.plan(ref, lv, 1.0 if is_range_source(ref, lv) else -1.0)
                else:
                    p = SF.plan(ref, lv, a.er_max)
                x0 = bisect.bisect_left(times, D.replace(hour=xs))
                fwd = bars[x0:x0 + a.max_hold]
                s = simulate(p, lv, ex, fwd, a.slippage, policy)
                if s is None:
                    unfilled += 1
                    continue
                net, cost = net_of(s, a.slippage, point, pip)
                trades.append(dict(date=D, sym=sym, leg=tag, setup=p["setup"], dir=p["dir"],
                                   outcome=s["outcome"], gross=s["gross"], net=net,
                                   cost=cost, mfe=s["mfe"], d0=d0, d1=d1,
                                   fill_t=s["fill"]["t"], exit_t=s["exit"]["t"],
                                   collided=s["collided"], entry=p["entry"],
                                   Rp=lv["R"] / pip))
        D += dt.timedelta(days=1)
    return trades, unfilled


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slippage", type=float, default=0.2)
    ap.add_argument("--er-max", type=float, default=0.35)
    ap.add_argument("--dataset", help="stem under data/, e.g. eurusd_m15_2022_10; omit to pool all")
    ap.add_argument("--range-test", choices=("er", "source"), default="er",
                    help="er = efficiency_ratio <= --er-max (inherited, never sourced). "
                         "source = the spec's own definition: session open AND close "
                         "both inside the middle 50%% of the range.")
    ap.add_argument("--exclude", nargs="*", default=[], metavar="SYM",
                    help="drop symbols, e.g. --exclude xauusd")
    ap.add_argument("--max-hold", type=int, default=400, metavar="BARS",
                    help="give a position at most this many M15 bars to resolve "
                         "(400 = 4 trading days). Beyond it the trade is reported "
                         "OPEN_AT_END. Mean holding time is ~22 bars, so this binds "
                         "only on positions that never resolve. Raising it changes "
                         "nothing but the exit bar of those few, and with it their "
                         "exit spread.")
    ap.add_argument("--match", help="only datasets whose stem contains this, e.g. 2025_2026")
    ap.add_argument("--json", help="write the trade list here for the journal")
    a = ap.parse_args()
    masters = ([DATA / f"{a.dataset}.master.csv"] if a.dataset
               else sorted(DATA.glob("*.master.csv")))
    if a.match:
        masters = [m for m in masters if a.match in m.name]
    for x in a.exclude:
        masters = [m for m in masters if x.lower() not in m.name.lower()]
    masters = [m for m in masters if m.exists()]
    if not masters:
        print("no *.master.csv under data/ — run build_dataset.py first"); return 1
    # data/sealed/ is out-of-sample and deliberately outside this non-recursive glob.
    sealed = sorted((DATA / "sealed").glob("*.master.csv"))
    if sealed:
        print(f"[{len(sealed)} sealed dataset(s) in data/sealed/ — EXCLUDED, out-of-sample]")
    trades, unfilled, alt = [], 0, []
    for M in masters:
        sym = M.name.split("_")[0].upper()
        bars, point, pip = load_master(M)
        trades_s, unf = run_symbol(bars, point, pip, sym, a, "STOP_FIRST")
        trades += trades_s; unfilled += unf
        alt += run_symbol(bars, point, pip, sym, a, "TARGET_FIRST")[0]
    if not trades:
        print("no trades"); return 0
    d0 = min(t["d0"] for t in trades); d1 = max(t["d1"] for t in trades)


    print(f"BACKTEST · SESSION_FLOW_V1 · M15 · {d0:%Y-%m-%d} to {d1:%Y-%m-%d}")
    print(f"symbols: {', '.join(sorted({t[chr(39)+chr(39)] if False else t['sym'] for t in trades}))}")
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
    for sym in sorted({t["sym"] for t in trades}):
        block(f"  {sym}", [t for t in trades if t["sym"] == sym])
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

    pooled_eq, pooled_peak, pooled_dd = 0.0, 0.0, 0.0
    for t in trades:
        pooled_eq += t["net"]; pooled_peak = max(pooled_peak, pooled_eq)
        pooled_dd = max(pooled_dd, pooled_peak - pooled_eq)
    seq, pts, dd, dd_from, dd_at = equity_curve(trades)
    print(f"max drawdown      {dd:.3f}R   CHRONOLOGICAL "
          f"(all symbols and both legs interleaved by exit time)")
    if dd_at:
        print(f"                  peak {dd_from:%Y-%m-%d} -> trough {dd_at:%Y-%m-%d}")
    print(f"                  {pooled_dd:.3f}R if measured symbol-major — reported for "
          f"comparison only, nobody trades in that order")

    # ---- collision audit -------------------------------------------------
    col = [t for t in trades if t["collided"]]
    alt_net = sum(t["net"] for t in alt)
    print(f"\ncollision audit ({len(col)} of {n} trades, {len(col)/n*100:.1f}%)")
    print("  bars containing both the stop and a live target — no bar data can order them")
    print(f"  STOP_FIRST   (used)  net {sum(nt):+.3f}R   {m:+.3f}R/trade")
    print(f"  TARGET_FIRST (bound) net {alt_net:+.3f}R   {alt_net/len(alt):+.3f}R/trade")
    print(f"  the assumption is worth {alt_net - sum(nt):+.3f}R over the sample")
    if col:
        print("  affected:")
        for t in sorted(col, key=lambda x: x["exit_t"])[:8]:
            print(f"    {t['date']:%Y-%m-%d} {t['sym']:<7}{t['leg']:<6}{t['setup']:<6}"
                  f"{t['outcome']:<11}{t['net']:+.3f}R")
        if len(col) > 8:
            print(f"    ... and {len(col)-8} more")

    # ---- monthly, so a 12-month sample cannot hide a bad stretch ----------
    months = defaultdict(list)
    for t in seq:
        months[t["exit_t"].strftime("%Y-%m")].append(t)
    if len(months) > 1:
        print(f"\nby month{'':<14}{'n':>4}{'net R':>10}{'net/trade':>11}{'win%':>7}")
        run = 0.0
        for k in sorted(months):
            s = months[k]; v = sum(x["net"] for x in s); run += v
            w = sum(1 for x in s if x["net"] > 0)
            print(f"  {k:<20}{len(s):>4}{v:>+10.3f}{v/len(s):>+11.3f}"
                  f"{w/len(s)*100:>6.0f}%   cum {run:+8.3f}R")
        pos = sum(1 for k in months if sum(x['net'] for x in months[k]) > 0)
        print(f"  {pos} of {len(months)} months positive")

    print(f"\nagainst config/lifecycle.json Stage-2 thresholds:")
    for lab, ok, got in (("trades >= 50", n >= 50, n),
                         ("expectancy >= 0.10R", m >= 0.10, f"{m:+.3f}"),
                         ("profit factor >= 1.20", pf >= 1.20, f"{pf:.3f}"),
                         ("max drawdown <= 10R", dd <= 10, f"{dd:.3f}")):
        print(f"  {'PASS' if ok else 'FAIL'}  {lab:<24}{got}")

    if a.json:
        import json as _j
        Path(a.json).write_text(_j.dumps([
            {k: (v.isoformat() if isinstance(v, dt.datetime) else v)
             for k, v in t.items() if k not in ("d0", "d1")} for t in seq
        ], indent=2), encoding="utf-8")
        print(f"\ntrade list -> {a.json}")

    span = (d1 - d0).days
    print(f"\n{span} calendar days, {len({t['sym'] for t in trades})} symbols. "
          f"{'Thresholds passed means the configured rules passed — nothing more.' if span > 300 else 'IN-SAMPLE. Not a Stage-2 result.'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
