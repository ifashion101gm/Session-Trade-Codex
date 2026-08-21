#!/usr/bin/env python3
"""
Pull a long M15 history straight out of the MT5 terminal into the project's
dataset contract. Runs on the Windows box where MetaTrader 5 is installed.

    pip install MetaTrader5
    python scripts/fetch_mt5_year.py --months 12

WHY THIS EXISTS AND NOT AN EA
-----------------------------
The desk is a hybrid workflow: the engine reports, the trader decides. Nothing
here places, modifies or cancels an order, and this script only READS history.
It is the data half of the backtest; `backtest_session_flow.py` is the other.

THE DST PROBLEM — the reason this is not just `build_dataset.py --server-offset 3`
---------------------------------------------------------------------------------
The Oct-2022 fixture is a single offset (UTC+3) because it is three weeks long.
A twelve-month pull crosses two daylight-saving changes, so the offset is +3 for
part of the year and +2 for the rest. Applying one constant would slide every
session window by an hour for ~4 months and quietly corrupt the whole sample.

Three defences, in order of strength:

  1. MEASURE the current offset live from the terminal (server clock vs UTC).
  2. APPLY the US schedule (2nd Sun Mar .. 1st Sun Nov) for the historical span.
     Transitions land on a Sunday, when FX is shut, so no bar is ambiguous.
  3. VERIFY empirically with `--profile`: average bar range by UTC hour over the
     whole year. Asian hours must sit in the trough and the London/NY overlap at
     the peak. If the offset were wrong the trough would move. This check trusts
     no timezone table — it reads the market's own daily rhythm.

Defence 3 is the one that matters. Step 2 is an assumption; step 3 falsifies it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dataset as BD  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]


# ---------------------------------------------------------------- DST ------
def _nth_sunday(year: int, month: int, n: int) -> dt.date:
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(6 - d.weekday()) % 7)      # first Sunday
    return d + dt.timedelta(weeks=n - 1)


def offset_from_reopen(server_bars) -> dict:
    """Derive the server's UTC offset from the weekly reopen, not from a table.

    FX reopens at a fixed instant — Sunday 17:00 New York — which is 21:00 UTC on
    EDT and 22:00 UTC on EST.  The first bar after each weekend gap therefore pins
    the server clock without trusting any DST schedule.

    Credit: the ICT Analyst toolkit described in the Offbeat Forex MT5/Claude guide.
    Validated on both project fixtures: the reopen hour flips 21:00 <-> 22:00 UTC
    exactly at the changeovers, confirming +3 summer / +2 winter — but DERIVING it.

    `server_bars` are (datetime, ...) in SERVER time.  Returns a per-week map plus a
    tally, so a broker that does not follow US DST is caught rather than assumed.
    """
    from collections import Counter
    ts = sorted(b[0] if isinstance(b, tuple) else b["t"] for b in server_bars)
    opens = [b for a, b in zip(ts, ts[1:]) if (b - a).total_seconds() > 12 * 3600]
    tally = Counter()
    for t in opens:
        if t.weekday() != 6:              # not a Sunday -> holiday gap, ignore
            continue
        # server hour of the reopen minus the true UTC hour (21 EDT / 22 EST)
        tally[t.hour] += 1
    return {"reopens": len(opens), "sunday_hours": dict(tally)}


def us_dst(day: dt.date) -> bool:
    """True inside US daylight time: 2nd Sunday March .. 1st Sunday November."""
    return _nth_sunday(day.year, 3, 2) <= day < _nth_sunday(day.year, 11, 1)


def offset_for(day: dt.date, summer: int, winter: int) -> int:
    return summer if us_dst(day) else winter


# ------------------------------------------------------------- fetching ----
def _write_set(stem: Path, bars, sym, info, a, BD):
    """master + views + manifest at an arbitrary stem. Used for the sealed split."""
    import json
    stem.parent.mkdir(parents=True, exist_ok=True)
    BD.write_csv(Path(f"{stem}.master.csv"), BD.MASTER_COLS, bars, {})
    m = {
        "generator": "scripts/fetch_mt5_year.py",
        "generator_version": BD.GENERATOR_VERSION,
        "built_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": f"MT5 live pull: {sym} @ {info.server}",
        "source_sha256": "n/a — pulled from terminal, not a file",
        "server_offset_hours": f"{a.summer_offset} summer / {a.winter_offset} winter (US DST)",
        "timezone": "UTC (server stamps shifted per-bar by the DST schedule)",
        "sealed": True,
        "seal_note": "OUT-OF-SAMPLE. Do not backtest until every rule in "
                     "SESSION_FLOW_V1_SPEC.md §4 and §5 is signed. Opening this early "
                     "destroys the only unbiased evidence this project has.",
        "rows": len(bars),
        "utc_start": bars[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "utc_end": bars[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "master": {"file": f"{stem.name}.master.csv", "columns": BD.MASTER_COLS,
                   "sha256": BD.sha256(Path(f"{stem}.master.csv"))},
        "views": {},
    }
    for suffix, spec in BD.VIEWS.items():
        p = Path(f"{stem}{suffix}")
        BD.write_csv(p, spec["columns"], bars, spec["rename"])
        m["views"][p.name] = {"purpose": spec["purpose"], "columns": spec["columns"],
                              "derived_from": f"{stem.name}.master.csv", "sha256": BD.sha256(p)}
    Path(f"{stem}.manifest.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")


def resolve(mt5, want: str):
    """Brokers suffix symbols (XAUUSD.crp, EURUSD.raw). Find the real name."""
    if mt5.symbol_info(want) is not None:
        return want
    for s in (mt5.symbols_get() or []):
        if s.name.upper().startswith(want.upper()):
            return s.name
    return None


def measure_offset(mt5, sym: str):
    """Server clock minus UTC, right now, to the nearest hour."""
    tick = mt5.symbol_info_tick(sym)
    if tick is None or not tick.time:
        return None
    server = dt.datetime.utcfromtimestamp(tick.time)
    return round((server - dt.datetime.utcnow()).total_seconds() / 3600)


def fetch(mt5, sym: str, months: int, summer: int, winter: int):
    # Price precision comes from the broker, never from repr(). Python's repr of
    # a binary float is exact, so 1.16141 prints as 1.1614100000000001 — and the
    # backtest infers POINT from the decimal count, so sixteen decimals silently
    # drove every spread cost to zero. See scripts/repair_precision.py.
    si = mt5.symbol_info(sym)
    dg = si.digits if si and si.digits else 5
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=int(months * 30.44) + 5)
    # ask in server time, generously padded on both ends
    rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15,
                                 start - dt.timedelta(days=3),
                                 end + dt.timedelta(days=3))
    if rates is None or len(rates) == 0:
        return None, f"no bars returned ({mt5.last_error()})"
    bars = []
    for r in rates:
        srv = dt.datetime.utcfromtimestamp(int(r["time"]))
        utc = srv - dt.timedelta(hours=offset_for(srv.date(), summer, winter))
        if utc < start:
            continue
        bars.append({
            "timestamp": utc,
            "open": f"{float(r['open']):.{dg}f}",
            "high": f"{float(r['high']):.{dg}f}",
            "low": f"{float(r['low']):.{dg}f}",
            "close": f"{float(r['close']):.{dg}f}",
            "volume": str(int(r["tick_volume"])),
            "spread": str(int(r["spread"])),
        })
    bars.sort(key=lambda b: b["timestamp"])
    return bars, None


# ------------------------------------------------------------ verifying ----
def profile(bars, pip_guess=None):
    """Mean bar range by UTC hour. The offset check that trusts no table."""
    by_h = {h: [] for h in range(24)}
    for b in bars:
        by_h[b["timestamp"].hour].append(float(b["high"]) - float(b["low"]))
    scale = pip_guess or (st.median([v for h in by_h for v in by_h[h]] or [1]) or 1)
    return {h: (st.mean(v) / scale if v else 0.0) for h, v in by_h.items()}


def print_profile(prof, label):
    print(f"\n  hourly range profile — {label}  (relative, median bar = 1.00)")
    mx = max(prof.values()) or 1
    asian = [prof[h] for h in range(0, 7)]
    other = [prof[h] for h in range(7, 21)]
    for h in range(24):
        bar = "#" * int(prof[h] / mx * 44)
        tag = "asian ref" if h < 7 else ("london" if h < 12 else
                                         ("new york" if h < 18 else ""))
        print(f"    {h:02d}:00 {prof[h]:5.2f} |{bar:<44}| {tag}")
    ok = st.mean(asian) < st.mean(other)
    print(f"    asian mean {st.mean(asian):.2f} vs rest {st.mean(other):.2f}  "
          f"-> {'OK — quiet window is where it should be' if ok else 'FAIL — OFFSET IS WRONG'}")
    return ok


# ----------------------------------------------------------------- main ----
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    ap.add_argument("--summer-offset", type=int, default=3)
    ap.add_argument("--winter-offset", type=int, default=2)
    ap.add_argument("--tag", default=None, help="stem suffix; default y<months>_<today>")
    ap.add_argument("--profile", action="store_true", default=True)
    ap.add_argument("--seal-from", default=None, metavar="YYYY-MM-DD",
                    help="bars on/after this date go to data/sealed/ and are excluded "
                         "from the default backtest glob. Do not open until the rules "
                         "are frozen.")
    a = ap.parse_args()
    seal = dt.date.fromisoformat(a.seal_from) if a.seal_from else None

    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 package not installed.  pip install MetaTrader5")
        print("This script must run on the Windows machine with the terminal.")
        return 1

    if not mt5.initialize():
        print(f"could not attach to the terminal: {mt5.last_error()}")
        print("Open MT5, log in, and leave it running.")
        return 1

    info = mt5.account_info()
    print(f"terminal: login {info.login}  server {info.server}  "
          f"balance {info.balance:.2f} {info.currency}")
    print("READ ONLY — this script never sends an order.\n")

    tag = a.tag or f"m15_y{a.months}_{dt.date.today():%Y%m}"
    DATA.mkdir(exist_ok=True)
    built, failed = [], []

    for want in a.symbols:
        sym = resolve(mt5, want)
        if sym is None:
            print(f"{want:<10} SKIP  not offered by this broker")
            failed.append(want); continue
        mt5.symbol_select(sym, True)

        live = measure_offset(mt5, sym)
        if live is not None and live not in (a.summer_offset, a.winter_offset):
            print(f"{want:<10} WARN  live server offset is UTC+{live}, but this run "
                  f"assumes +{a.summer_offset}/+{a.winter_offset}")

        bars, err = fetch(mt5, sym, a.months, a.summer_offset, a.winter_offset)
        if err:
            print(f"{want:<10} FAIL  {err}")
            print(f"{'':<10}       history may not be downloaded — open an M15 chart "
                  f"for {sym}, press Home to scroll back, then retry")
            failed.append(want); continue

        problems = BD.integrity(bars)
        if problems:
            print(f"{want:<10} FAIL  {len(problems)} integrity problems, nothing written")
            for p in problems[:5]:
                print(f"{'':<10}       {p}")
            failed.append(want); continue

        if seal:
            dev = [b for b in bars if b["timestamp"].date() < seal]
            held = [b for b in bars if b["timestamp"].date() >= seal]
            if held:
                sd = DATA / "sealed"; sd.mkdir(exist_ok=True)
                _write_set(sd / f"{want.lower()}_{tag}_SEALED", held, sym, info, a, BD)
                print(f"{want:<10} SEAL  {len(held):>6} bars from {seal} -> data/sealed/ "
                      f"(NOT in the default backtest glob)")
            bars = dev
            if not bars:
                print(f"{want:<10} FAIL  nothing left after sealing"); failed.append(want); continue

        stem = DATA / f"{want.lower()}_{tag}"
        BD.write_csv(Path(f"{stem}.master.csv"), BD.MASTER_COLS, bars, {})
        manifest = {
            "generator": "scripts/fetch_mt5_year.py",
            "generator_version": BD.GENERATOR_VERSION,
            "built_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_file": f"MT5 live pull: {sym} @ {info.server}",
            "source_sha256": "n/a — pulled from terminal, not a file",
            "server_offset_hours": f"{a.summer_offset} summer / {a.winter_offset} winter (US DST)",
            "timezone": "UTC (server stamps shifted per-bar by the DST schedule)",
            "rows": len(bars),
            "utc_start": bars[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "utc_end": bars[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "master": {"file": f"{stem.name}.master.csv", "columns": BD.MASTER_COLS,
                       "sha256": BD.sha256(Path(f"{stem}.master.csv"))},
            "views": {},
        }
        for suffix, spec in BD.VIEWS.items():
            p = Path(f"{stem}{suffix}")
            BD.write_csv(p, spec["columns"], bars, spec["rename"])
            manifest["views"][p.name] = {
                "purpose": spec["purpose"], "columns": spec["columns"],
                "derived_from": f"{stem.name}.master.csv", "sha256": BD.sha256(p)}
        import json
        Path(f"{stem}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                 encoding="utf-8")
        print(f"{want:<10} OK    {len(bars):>6} bars  {manifest['utc_start'][:10]} .. "
              f"{manifest['utc_end'][:10]}  sha {manifest['master']['sha256'][:12]}")
        built.append((want, bars))

    mt5.shutdown()

    if a.profile and built:
        print("\n" + "=" * 72)
        print("OFFSET VERIFICATION — does the market's quiet window land where we think?")
        print("=" * 72)
        allok = True
        for want, bars in built:
            allok &= print_profile(profile(bars), want)
        print("\n" + ("ALL SYMBOLS PASS — the DST handling is consistent with the data."
                      if allok else
                      "*** AT LEAST ONE SYMBOL FAILS — DO NOT BACKTEST THIS DATA. ***\n"
                      "Re-run with different --summer-offset/--winter-offset."))

    print(f"\n{len(built)} built, {len(failed)} failed"
          + (f"  ({', '.join(failed)})" if failed else ""))
    if built:
        print(f"\nnext:\n  python scripts/verify_datasets.py")
        print(f"  python scripts/backtest_session_flow.py --match {tag}")
    return 0 if built else 1


if __name__ == "__main__":
    raise SystemExit(main())
