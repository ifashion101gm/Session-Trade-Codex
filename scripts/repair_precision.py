#!/usr/bin/env python3
"""
Repair float-repr noise in a master CSV, then rebuild its views and manifest.

THE BUG THIS FIXES
------------------
`fetch_mt5_year.py` wrote prices with `repr(float(x))`. Python's repr of a
binary float is exact, so 1.16141 comes back as `1.1614100000000001` — sixteen
decimal places of pure representation artifact.

`backtest_session_flow.py` infers POINT from the decimal count in the file, so
that a 5-digit FX pair, a 3-digit JPY cross and a 2-digit gold quote all work
without a lookup table. Fed sixteen decimals it inferred POINT = 1e-16, which
made every spread cost round to zero — and the backtest reported GROSS in the
NET column with no warning at all.

The measured damage on the 2025-26 pull: EURUSD and GBPUSD were charged
**nothing** for spread or slippage across 524 trades.

THE REPAIR IS LOSSLESS
----------------------
Rounding 1.1614100000000001 back to 1.16141 discards nothing — the extra digits
were never in the broker's quote. The true precision is recovered as the largest
decimal count among values that are NOT artifacts (<= 8 places), which gives 5
for FX, 3 for JPY, 2 for gold.

    python scripts/repair_precision.py            # every master under data/
    python scripts/repair_precision.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dataset as BD  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
COLS = ("open", "high", "low", "close")


def true_digits(rows) -> int:
    """Largest decimal count that is not float-repr noise."""
    c = Counter()
    for r in rows:
        for k in COLS:
            v = r[k]
            n = len(v.split(".")[1]) if "." in v else 0
            if n <= 8:                     # anything longer is an artifact
                c[n] += 1
    return max(c) if c else 5


def repair(master: Path, dry: bool) -> tuple[bool, str]:
    rows = list(csv.DictReader(open(master, newline="", encoding="utf-8")))
    if not rows:
        return False, "empty"
    seen = max((len(r[k].split(".")[1]) if "." in r[k] else 0)
               for r in rows for k in COLS)
    d = true_digits(rows)
    if seen <= 8:
        return False, f"clean already ({seen} decimals)"
    if dry:
        return True, f"{seen} -> {d} decimals, {len(rows)} rows (dry run)"

    bars = []
    for r in rows:
        b = {"timestamp": dt.datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S"),
             "volume": r.get("volume", ""), "spread": r.get("spread", "")}
        for k in COLS:
            b[k] = f"{round(float(r[k]), d):.{d}f}"
        bars.append(b)

    problems = BD.integrity(bars)
    if problems:
        return False, f"REFUSED — {len(problems)} integrity failures after rounding"

    stem = Path(str(master).replace(".master.csv", ""))
    BD.write_csv(master, BD.MASTER_COLS, bars, {})
    mf = Path(f"{stem}.manifest.json")
    m = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
    m.update({
        "repaired_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repair": f"float-repr noise removed; prices rounded to {d} decimals "
                  f"(were being read as {seen}, which zeroed all spread costs)",
        "price_digits": d,
        "rows": len(bars),
        "master": {"file": master.name, "columns": BD.MASTER_COLS,
                   "sha256": BD.sha256(master)},
        "views": {},
    })
    for suffix, spec in BD.VIEWS.items():
        p = Path(f"{stem}{suffix}")
        BD.write_csv(p, spec["columns"], bars, spec["rename"])
        m["views"][p.name] = {"purpose": spec["purpose"], "columns": spec["columns"],
                              "derived_from": master.name, "sha256": BD.sha256(p)}
    mf.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    return True, f"{seen} -> {d} decimals, {len(rows)} rows, views + manifest rebuilt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--include-sealed", action="store_true",
                    help="also repair data/sealed/. Repairing does not reveal any "
                         "result — it only fixes number formatting.")
    a = ap.parse_args()

    targets = sorted(DATA.glob("*.master.csv"))
    if a.include_sealed:
        targets += sorted((DATA / "sealed").glob("*.master.csv"))
    changed = 0
    for m in targets:
        did, msg = repair(m, a.dry_run)
        changed += did
        print(f"{'FIX ' if did else 'skip'}  {m.name:<44}{msg}")
    print(f"\n{changed} of {len(targets)} repaired"
          + ("  (dry run — nothing written)" if a.dry_run else ""))
    if changed and not a.dry_run:
        print("\nre-run:  python scripts/verify_datasets.py")
        print("         python scripts/backtest_session_flow.py --match y12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
