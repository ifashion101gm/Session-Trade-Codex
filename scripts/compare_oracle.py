#!/usr/bin/env python3
"""
Compare the engine's 30 plans against the source video's worked examples.

    python scripts/compare_oracle.py
    python scripts/compare_oracle.py --tol-pips 1.0

INPUT   benchmarks/oracle_30.csv
        engine columns (eng_*) are pre-filled from 30_WORKED_EXAMPLES.md.
        Fill the vid_* columns from the video. Leave a row's vid_* blank and set
        vid_shown=N when the video shows nothing for that session — absences are
        rows, not omissions.

WHAT THIS IS FOR — and what it is NOT
------------------------------------
This is a **conformance** test (Stage 1): does the tool apply the rules the source
demonstrates?  It is NOT evidence of edge (Stage 2).

The distinction matters because the two have opposite rules about fitting:

  CONFORMANCE   adjusting a rule so the engine reproduces the author's own worked
                examples is legitimate.  That is what §0.0 benchmark primacy
                instructs: "the engine must reproduce them; where it does not, the
                strategy is refined - not the example."

  EDGE          adjusting a rule because it improves R is overfitting, and every
                such adjustment enters the hypothesis register.

So: refine freely to match the examples. Then re-measure edge on the SEALED period,
never on these 30.

READING THE OUTPUT
------------------
The diagnostic is not the match rate. It is whether mismatches CLUSTER:

  clustered on one setup   -> that setup's rule is wrong        (fix the rule)
  clustered on one leg     -> the leg-2 window or scope is wrong
  clustered on one field   -> that field's formula is wrong
  scattered                -> transcription noise or feed difference
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORACLE = ROOT / "benchmarks" / "oracle_30.csv"

PRICE = [("eng_entry", "vid_entry"), ("eng_stop", "vid_stop"), ("eng_target", "vid_target")]
CAT   = [("eng_setup", "vid_setup"), ("eng_dir", "vid_dir")]


def pipsize(v: float) -> float:
    return 0.01 if v > 20 else 0.0001          # JPY/gold vs FX


def num(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol-pips", type=float, default=1.0,
                    help="EXACT within this; CLOSE within 3x this; else MISMATCH")
    a = ap.parse_args()
    if not ORACLE.exists():
        print(f"missing {ORACLE}"); return 1
    rows = list(csv.DictReader(open(ORACLE, newline="", encoding="utf-8")))

    shown = [r for r in rows if (r.get("vid_shown") or "").strip().upper() == "Y"]
    absent = [r for r in rows if (r.get("vid_shown") or "").strip().upper() == "N"]
    blank = len(rows) - len(shown) - len(absent)

    print(f"ORACLE CONFORMANCE — {ORACLE.name}\n")
    print(f"  possible entries   {len(rows)}")
    print(f"  shown in video     {len(shown)}")
    print(f"  marked absent      {len(absent)}")
    if blank:
        print(f"  NOT YET FILLED     {blank}   <- vid_shown is blank on these rows")
    if not shown:
        print("\n  nothing to compare yet. Fill vid_shown and the vid_* columns.")
        return 0

    # ---- absences vs the engine's own UNFILLED --------------------------------
    if absent:
        unf = [r for r in absent if r["eng_fill_state"] == "UNFILLED"]
        print(f"\nABSENCES ({len(absent)})")
        print(f"  {len(unf)} coincide with an engine UNFILLED plan — explained by the")
        print(f"    contract as it stands, no skip rule required")
        rest = [r for r in absent if r["eng_fill_state"] != "UNFILLED"]
        if rest:
            print(f"  {len(rest)} do NOT — these are the ones that could imply a skip rule:")
            for r in rest:
                why = (r.get("skip_reason_stated") or "").strip() or "(no reason stated)"
                print(f"      {r['date']} {r['traded_session']:<8} engine={r['eng_setup']:<6} {why}")

    # ---- field-by-field -------------------------------------------------------
    tally = defaultdict(lambda: [0, 0])           # field -> [ok, total]
    bad = []
    for r in shown:
        issues = []
        for e, v in CAT:
            ev, vv = (r.get(e) or "").strip().upper(), (r.get(v) or "").strip().upper()
            if not vv:
                continue
            tally[e][1] += 1
            if ev == vv:
                tally[e][0] += 1
            else:
                issues.append(f"{e[4:]}: engine {ev} vs video {vv}")
        for e, v in PRICE:
            ev, vv = num(r.get(e)), num(r.get(v))
            if ev is None or vv is None:
                continue
            p = pipsize(ev)
            d = abs(ev - vv) / p
            tally[e][1] += 1
            if d <= a.tol_pips:
                tally[e][0] += 1
            else:
                issues.append(f"{e[4:]}: {d:.1f}p apart"
                              + ("  (CLOSE)" if d <= 3 * a.tol_pips else "  (MISMATCH)"))
        if issues:
            bad.append((r, issues))

    print(f"\nFIELD CONFORMANCE   (price tolerance {a.tol_pips} pip)")
    for f in [e for e, _ in CAT] + [e for e, _ in PRICE]:
        ok, n = tally[f]
        if n:
            print(f"  {f[4:]:<8}{ok:>3} / {n:<3}  {ok/n*100:5.1f}%")

    if not bad:
        print("\n  every compared field matches. Conformance PASS.")
        return 0

    # ---- clustering: the actual diagnostic ------------------------------------
    print(f"\nMISMATCHES ({len(bad)} rows)")
    for r, iss in bad:
        print(f"  {r['date']} {r['traded_session']:<8} {r['eng_setup']:<6} {r['eng_dir']:<5}")
        for i in iss:
            print(f"      {i}")

    print("\nCLUSTERING — this is the diagnostic, not the match rate")
    for key, label in (("eng_setup", "by setup"), ("leg", "by leg")):
        tot, mis = defaultdict(int), defaultdict(int)
        for r in shown:
            tot[r[key]] += 1
        for r, _ in bad:
            mis[r[key]] += 1
        print(f"  {label}")
        for k in sorted(tot):
            n, m = tot[k], mis[k]
            flag = "  <== clustered, suspect this rule" if n and m / n >= 0.5 and m >= 2 else ""
            print(f"    {k:<8}{m:>3} / {n:<3} mismatched{flag}")
    print("\n  clustered -> fix the rule, tag it, issue a NEW version id")
    print("  scattered -> transcription noise or a feed difference; do not change rules")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
