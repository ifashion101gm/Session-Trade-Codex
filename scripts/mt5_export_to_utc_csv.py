#!/usr/bin/env python3
"""
Convert an MT5 bar export into the UTC CSV that asian_session_backtester.py expects,
and self-check the result against the Oct-3 golden case.

MT5 exports bars in SERVER time (VT Markets = UTC+3 in summer, UTC+2 in winter).
October 2022: Europe left DST on 30 Oct, so 1-21 Oct 2022 is UTC+3.

    python scripts/mt5_export_to_utc_csv.py EURUSD_M15_202210.csv \
        --server-offset 3 --out data/eurusd_m15_2022_10_utc.csv

Output columns: time,open,high,low,close,spread   (time = UTC, spread = broker points)

--------------------------------------------------------------------------
HOW TO PRODUCE THE INPUT (2 minutes, and it is YOUR broker's feed — which is
the only feed the golden case is valid on)

  1. MT5 -> View -> Symbols (Ctrl+U) -> find EURUSD -> Bars tab
  2. Set the period to M15, request 2022.10.01 - 2022.10.22, click Request
  3. Click Export -> save as CSV
  Alternative: open an M15 EURUSD chart, scroll back to Oct 2022 so the bars
  load, then Tools -> History Center, or right-click the chart -> Save As.

Both give a tab- or comma-separated file with a header like
    <DATE>  <TIME>  <OPEN>  <HIGH>  <LOW>  <CLOSE>  <TICKVOL>  <VOL>  <SPREAD>
This script accepts that shape, and also plain `time,open,high,low,close,spread`.
--------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timedelta

GOLDEN_DATE = "2022-10-03"
GOLDEN_HIGH = 0.98344
GOLDEN_LOW = 0.97843
GOLDEN_RANGE_PIPS = 50.1
PIP = 0.0001


def sniff_and_read(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        delim = "\t" if sample.count("\t") > sample.count(",") else ","
        rows = list(csv.reader(fh, delimiter=delim))

    if not rows:
        sys.exit("empty file")

    header = [c.strip().strip("<>").lower() for c in rows[0]]
    body = rows[1:]

    def idx(*names):
        for n in names:
            if n in header:
                return header.index(n)
        return None

    i_date, i_time = idx("date"), idx("time")
    i_dt = idx("datetime", "timestamp") if i_date is None else None
    i_o, i_h = idx("open"), idx("high")
    i_l, i_c = idx("low"), idx("close")
    i_s = idx("spread")

    if i_o is None or i_h is None or i_l is None or i_c is None:
        sys.exit(f"could not find OHLC columns in header: {header}")

    out = []
    for r in body:
        if not r or len(r) <= max(x for x in (i_o, i_h, i_l, i_c) if x is not None):
            continue
        if i_date is not None and i_time is not None:
            stamp = f"{r[i_date].strip()} {r[i_time].strip()}"
        elif i_date is not None:
            stamp = r[i_date].strip()
        else:
            stamp = r[i_dt].strip()

        dt = None
        for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M", "%Y.%m.%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(stamp, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            continue

        try:
            out.append({
                "dt": dt,
                "open": float(r[i_o]), "high": float(r[i_h]),
                "low": float(r[i_l]), "close": float(r[i_c]),
                "spread": (r[i_s].strip() if i_s is not None and i_s < len(r) else ""),
            })
        except ValueError:
            continue

    if not out:
        sys.exit("no parseable rows — check the export format")
    return out


def session_levels(bars: list[dict], date_str: str, start_h: int, end_h: int):
    """Half-open [start, end) in UTC. Window may cross midnight (start > end)."""
    end_d = datetime.strptime(date_str, "%Y-%m-%d")
    end_t = end_d.replace(hour=end_h)
    start_t = end_t - timedelta(hours=(end_h - start_h) % 24)
    sel = [b for b in bars if start_t <= b["utc"] < end_t]
    if not sel:
        return None
    return {
        "n": len(sel), "start": start_t, "end": end_t,
        "high": max(b["high"] for b in sel), "low": min(b["low"] for b in sel),
        "open": sel[0]["open"], "close": sel[-1]["close"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--server-offset", type=float, required=True,
                    help="Broker server UTC offset in hours (VT Markets Oct 2022 = 3)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()

    bars = sniff_and_read(a.infile)
    for b in bars:
        b["utc"] = b["dt"] - timedelta(hours=a.server_offset)
    bars.sort(key=lambda b: b["utc"])

    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "open", "high", "low", "close", "spread"])
        for b in bars:
            w.writerow([b["utc"].strftime("%Y-%m-%d %H:%M:%S"),
                        b["open"], b["high"], b["low"], b["close"], b["spread"]])

    print(f"wrote {len(bars)} bars -> {a.out}")
    print(f"  range {bars[0]['utc']} .. {bars[-1]['utc']} UTC "
          f"(server offset applied: UTC+{a.server_offset:g})")

    if a.no_check:
        return 0

    # ---- self-check: the golden case doubles as an offset validator ----
    print(f"\nGOLDEN CASE CHECK — {GOLDEN_DATE}")
    print(f"  expected reference high/low {GOLDEN_HIGH} / {GOLDEN_LOW} "
          f"({GOLDEN_RANGE_PIPS} pips)\n")

    ok_any = False
    for label, sh, eh in (("truth   00:00-07:00 UTC", 0, 7),
                          ("contract 22:00-07:00 UTC", 22, 7)):
        s = session_levels(bars, GOLDEN_DATE, sh, eh)
        if not s:
            print(f"  {label}: NO BARS IN WINDOW")
            continue
        rng = (s["high"] - s["low"]) / PIP
        hit = abs(s["high"] - GOLDEN_HIGH) < 1e-5 and abs(s["low"] - GOLDEN_LOW) < 1e-5
        ok_any = ok_any or hit
        print(f"  {label}: {s['n']:>2} bars  high {s['high']:.5f}  low {s['low']:.5f}  "
              f"range {rng:.1f}p  {'<-- MATCHES TRUTH' if hit else ''}")

    print()
    if ok_any:
        print("  Offset looks correct. Whichever window matched is the one the")
        print("  confirmed-truth case was derived on — that settles defect D3.")
    else:
        print("  NEITHER window reproduces the golden levels.")
        print("  Most likely the --server-offset is wrong. Try 2 instead of 3,")
        print("  or check the export is EURUSD M15 and covers 2022-10-03.")
        print("  Do NOT proceed to backtest until one window matches; every")
        print("  downstream level derives from these two numbers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
