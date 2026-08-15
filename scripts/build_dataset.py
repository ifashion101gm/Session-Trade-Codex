#!/usr/bin/env python3
"""
Single-source dataset builder for the Session Trade Codex.

THE COLUMN CONTRACT
-------------------
Two consumers in this repo want different column names for the same bars:

    asian_session_backtester.py   time, open, high, low, close, spread
    audit_ohlcv.py (skill)        timestamp, open, high, low, close, volume

Neither is wrong and neither is changed. Instead there is ONE master file
holding the superset, and the two narrow views are GENERATED from it:

    <stem>.master.csv    timestamp, open, high, low, close, volume, spread   <- edit nothing else
    <stem>_utc.csv       time, open, high, low, close, spread                <- engine view
    <stem>_audit.csv     timestamp, open, high, low, close, volume           <- audit view
    <stem>.manifest.json provenance + sha256 of master and every view

Views are derived artifacts. Never hand-edit them. `--verify` recomputes every
hash and fails loudly if a view drifted from its master, which is the failure
mode this design exists to catch.

USAGE
-----
    # build from a raw MT5 export (server time -> UTC)
    python scripts/build_dataset.py build EURUSD_M15_202210030000_202210212345.csv \
        --server-offset 3 --stem data/eurusd_m15_2022_10

    # check nothing drifted (CI / pre-commit)
    python scripts/build_dataset.py verify --stem data/eurusd_m15_2022_10

MT5 export shape accepted:
    <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>
tab- or comma-separated. Volume is TICKVOL; broker VOL is usually 0 on FX.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

GENERATOR_VERSION = "1.0"

MASTER_COLS = ["timestamp", "open", "high", "low", "close", "volume", "spread"]
VIEWS = {
    "_utc.csv": {
        "purpose": "engine — asian_session_backtester.py, validate_golden_oct3.py",
        "columns": ["time", "open", "high", "low", "close", "spread"],
        "rename": {"timestamp": "time"},
    },
    "_audit.csv": {
        "purpose": "tooling — .claude/skills/market-data-quality/scripts/audit_ohlcv.py",
        "columns": ["timestamp", "open", "high", "low", "close", "volume"],
        "rename": {},
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_mt5_export(path: Path, offset_hours: float) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    delim = "\t" if text.count("\t") > text.count(",") else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    if not rows:
        sys.exit(f"empty file: {path}")

    header = [c.strip().strip("<>").lower() for c in rows[0]]

    def idx(*names):
        for n in names:
            if n in header:
                return header.index(n)
        return None

    i_date, i_time = idx("date"), idx("time")
    i_dt = idx("datetime", "timestamp")
    i_o, i_h, i_l, i_c = idx("open"), idx("high"), idx("low"), idx("close")
    i_v = idx("tickvol", "volume", "tick_volume")
    i_s = idx("spread")
    if None in (i_o, i_h, i_l, i_c):
        sys.exit(f"could not locate OHLC columns in header: {header}")

    fmts = ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y.%m.%d")
    out = []
    for r in rows[1:]:
        if len(r) <= max(x for x in (i_o, i_h, i_l, i_c) if x is not None):
            continue
        stamp = (f"{r[i_date].strip()} {r[i_time].strip()}"
                 if i_date is not None and i_time is not None
                 else r[(i_date if i_date is not None else i_dt)].strip())
        ts = None
        for f in fmts:
            try:
                ts = dt.datetime.strptime(stamp, f)
                break
            except ValueError:
                continue
        if ts is None:
            continue
        try:
            out.append({
                "timestamp": ts - dt.timedelta(hours=offset_hours),
                "open": r[i_o].strip(), "high": r[i_h].strip(),
                "low": r[i_l].strip(), "close": r[i_c].strip(),
                "volume": r[i_v].strip() if i_v is not None and i_v < len(r) else "",
                "spread": r[i_s].strip() if i_s is not None and i_s < len(r) else "",
            })
        except IndexError:
            continue
    if not out:
        sys.exit("no parseable rows — check the export format")
    out.sort(key=lambda b: b["timestamp"])
    return out


def integrity(bars: list[dict]) -> list[str]:
    """Cheap invariants the structural audit cannot express."""
    problems = []
    seen = set()
    prev = None
    for b in bars:
        t = b["timestamp"]
        if t in seen:
            problems.append(f"duplicate timestamp {t}")
        seen.add(t)
        try:
            o, h, l, c = (float(b[k]) for k in ("open", "high", "low", "close"))
        except ValueError:
            problems.append(f"non-numeric OHLC at {t}")
            continue
        if not (l <= o <= h and l <= c <= h):
            problems.append(f"OHLC violation at {t}: o={o} h={h} l={l} c={c}")
        if h < l:
            problems.append(f"high < low at {t}")
        prev = t
    return problems


def write_csv(path: Path, cols: list[str], bars: list[dict], rename: dict) -> None:
    inv = {v: k for k, v in rename.items()}
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for b in bars:
            row = []
            for c in cols:
                src = inv.get(c, c)
                v = b[src]
                row.append(v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, dt.datetime) else v)
            w.writerow(row)


def cmd_build(a: argparse.Namespace) -> int:
    stem = Path(a.stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    src = Path(a.source)
    bars = read_mt5_export(src, a.server_offset)

    problems = integrity(bars)
    if problems:
        print(f"INTEGRITY FAILURES ({len(problems)}) — nothing written:")
        for p in problems[:20]:
            print(f"  {p}")
        return 1

    master = Path(f"{stem}.master.csv")
    write_csv(master, MASTER_COLS, bars, {})
    print(f"master  {master.name:<34}{len(bars)} rows")

    manifest = {
        "generator": "scripts/build_dataset.py",
        "generator_version": GENERATOR_VERSION,
        "built_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": src.name,
        "source_sha256": sha256(src),
        "server_offset_hours": a.server_offset,
        "timezone": "UTC (server stamps shifted by -offset)",
        "rows": len(bars),
        "utc_start": bars[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "utc_end": bars[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "master": {"file": master.name, "columns": MASTER_COLS, "sha256": sha256(master)},
        "views": {},
    }

    for suffix, spec in VIEWS.items():
        p = Path(f"{stem}{suffix}")
        write_csv(p, spec["columns"], bars, spec["rename"])
        manifest["views"][p.name] = {
            "purpose": spec["purpose"],
            "columns": spec["columns"],
            "derived_from": master.name,
            "sha256": sha256(p),
        }
        print(f"view    {p.name:<34}{', '.join(spec['columns'])}")

    mf = Path(f"{stem}.manifest.json")
    mf.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest {mf.name}")
    print(f"\n  {manifest['utc_start']} .. {manifest['utc_end']} UTC (offset UTC+{a.server_offset:g})")
    print(f"  master sha256 {manifest['master']['sha256'][:16]}")
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    stem = Path(a.stem)
    mf = Path(f"{stem}.manifest.json")
    if not mf.exists():
        print(f"FAIL  no manifest at {mf} — run `build` first")
        return 1
    m = json.loads(mf.read_text(encoding="utf-8"))
    bad = 0

    master = stem.parent / m["master"]["file"]
    if not master.exists():
        print(f"FAIL  master missing: {master}")
        return 1
    got = sha256(master)
    ok = got == m["master"]["sha256"]
    bad += not ok
    print(f"{'OK  ' if ok else 'FAIL'}  master {master.name}  {got[:16]}")

    for name, v in m["views"].items():
        p = stem.parent / name
        if not p.exists():
            print(f"FAIL  view missing: {name}"); bad += 1; continue
        got = sha256(p)
        ok = got == v["sha256"]
        bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'}  view   {name}  {got[:16]}"
              f"{'' if ok else '   <-- DRIFTED from master; rebuild, do not hand-edit'}")

    print(f"\n{'all artifacts consistent' if not bad else f'{bad} artifact(s) drifted'}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build master + views + manifest from a raw MT5 export")
    b.add_argument("source")
    b.add_argument("--server-offset", type=float, required=True)
    b.add_argument("--stem", required=True, help="e.g. data/eurusd_m15_2022_10")
    b.set_defaults(fn=cmd_build)

    v = sub.add_parser("verify", help="recompute hashes and detect drift")
    v.add_argument("--stem", required=True)
    v.set_defaults(fn=cmd_verify)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
