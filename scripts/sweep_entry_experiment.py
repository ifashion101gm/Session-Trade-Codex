#!/usr/bin/env python3
"""Causal research comparison from the shared session-range discussion.

This module is intentionally separate from SESSION_FLOW_V1. It tests two entry
variants without changing the current contract and never reads data/sealed/.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "eurusd_m15_2022_10.master.csv"
PIP = 0.0001
SOURCE_UTC_OFFSET_HOURS = 3


@dataclass(frozen=True)
class Signal:
    date: str
    variant: str
    direction: str
    source_sweep_time: str
    normalized_timestamp_utc: str
    source_timestamp_broker: str
    source_timezone: str
    source_utc_offset_hours: int
    reference_start_broker: str
    reference_end_broker: str
    reference_start_utc: str
    reference_end_utc: str
    attack_start_time_utc: str
    sweep_extreme_time_utc: str
    sweep_extreme_time_broker: str
    reclaim_time_utc: str
    reclaim_time_broker: str
    confirmation_time_utc: str | None
    confirmation_time_broker: str | None
    signal_time_utc: str
    order_time_utc: str
    fill_time_utc: str
    fill_model: str
    sweep_extreme: float
    reclaim_clearance_fraction: float
    entry: float
    stop: float
    target_4r: float
    target_5r: float
    structural_margin: float
    required_structural_risk_pct: float
    contract_risk_pct: float
    setup_status: str
    entry_status: str
    all_failed_gates: tuple[str, ...]
    status: str
    reason_code: str


def load_bars(path: Path) -> list[dict]:
    if "sealed" in {p.lower() for p in path.parts}:
        raise ValueError("sealed datasets are forbidden for this experiment")
    bars = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            bars.append({
                "t": dt.datetime.fromisoformat(row["timestamp"]),
                "o": float(row["open"]), "h": float(row["high"]),
                "l": float(row["low"]), "c": float(row["close"]),
            })
    return sorted(bars, key=lambda b: b["t"])


def window(bars: list[dict], start: dt.datetime, end: dt.datetime) -> list[dict]:
    return [b for b in bars if start <= b["t"] < end]


def reference_levels(ref: list[dict]) -> dict:
    if len(ref) != 32:
        raise ValueError(f"REFERENCE_BAR_COUNT: expected 32, got {len(ref)}")
    high, low = max(b["h"] for b in ref), min(b["l"] for b in ref)
    rng = high - low
    if rng <= 0:
        raise ValueError("INVALID_REFERENCE_RANGE")
    opened, closed = ref[0]["o"], ref[-1]["c"]
    return {
        "high": high, "low": low, "range": rng, "mid": (high + low) / 2,
        "open": opened, "close": closed,
        "bias": "LONG" if closed > (high + low) / 2 else "SHORT",
        "er": abs(closed - opened) / rng,
    }


def _iso(t: dt.datetime) -> str:
    return t.isoformat(timespec="minutes") + "Z"


def _broker_iso(t: dt.datetime) -> str:
    return (t + dt.timedelta(hours=SOURCE_UTC_OFFSET_HOURS)).isoformat(timespec="minutes")


def find_sweep_signal(
    date: dt.datetime,
    ref: list[dict],
    execution: list[dict],
    variant: str,
    clearance_fraction: float = 0.025,
    direction_filter: str | None = None,
) -> Signal | None:
    """Return the first causal, bias-aligned qualifying reclaim.

    The sweep extreme is accumulated only through the entry candle. Later bars
    cannot retroactively invalidate or improve an earlier signal.
    """
    lv = reference_levels(ref)
    if lv["er"] >= 0.60:  # shared experiment keeps the SSPF-v1.3 classifier fixed
        return None
    R = 0.25 * lv["range"]
    running_high, running_low = lv["high"], lv["low"]
    running_high_time = running_low_time = ref[-1]["t"]
    high_attack_start = low_attack_start = None
    for i, bar in enumerate(execution):
        if bar["h"] > running_high:
            running_high, running_high_time = bar["h"], bar["t"]
        if bar["l"] < running_low:
            running_low, running_low_time = bar["l"], bar["t"]
        if bar["h"] > lv["high"] and high_attack_start is None:
            high_attack_start = bar["t"]
        if bar["l"] < lv["low"] and low_attack_start is None:
            low_attack_start = bar["t"]
        candidates = []
        if bar["h"] > lv["high"]:
            clearance = (lv["high"] - bar["c"]) / lv["range"]
            if clearance >= clearance_fraction:
                candidates.append(("SHORT", running_high, running_high_time, clearance))
        if bar["l"] < lv["low"]:
            clearance = (bar["c"] - lv["low"]) / lv["range"]
            if clearance >= clearance_fraction:
                candidates.append(("LONG", running_low, running_low_time, clearance))

        for direction, extreme, extreme_time, clearance in candidates:
            if direction_filter and direction != direction_filter:
                continue
            entry_bar = bar
            confirmation_time = None
            if variant == "POST_SWEEP_CONFIRMATION_ENTRY":
                if i + 1 >= len(execution):
                    return None
                nxt = execution[i + 1]
                confirms = ((direction == "SHORT" and nxt["c"] < nxt["o"] and nxt["c"] < bar["c"]) or
                            (direction == "LONG" and nxt["c"] > nxt["o"] and nxt["c"] > bar["c"]))
                if not confirms:
                    continue
                entry_bar = nxt
                confirmation_time = nxt["t"]
                # The confirmation candle is fully known at its close, so its
                # adverse extreme belongs in the structural check at entry.
                if direction == "SHORT" and nxt["h"] > extreme:
                    extreme, extreme_time = nxt["h"], nxt["t"]
                if direction == "LONG" and nxt["l"] < extreme:
                    extreme, extreme_time = nxt["l"], nxt["t"]
            elif variant != "SWEEP_CLOSE_ENTRY":
                raise ValueError(f"unknown variant: {variant}")

            entry = entry_bar["c"]
            short = direction == "SHORT"
            stop = entry + R if short else entry - R
            margin = (stop - extreme) if short else (extreme - stop)
            structural_ok = margin > 0
            required_risk = (extreme - entry) if short else (entry - extreme)
            required_risk_pct = required_risk / lv["range"]
            failed = () if structural_ok else ("FIXED_RISK_SL_INSIDE_SWEEP_EXTREME",)
            attack_start = high_attack_start if short else low_attack_start
            reference_start = ref[0]["t"]
            reference_end = ref[-1]["t"] + dt.timedelta(minutes=15)
            sign = -1 if short else 1
            return Signal(
                date=date.date().isoformat(), variant=variant, direction=direction,
                source_sweep_time=_broker_iso(bar["t"]),
                normalized_timestamp_utc=_iso(entry_bar["t"]),
                source_timestamp_broker=_broker_iso(entry_bar["t"]),
                source_timezone="BROKER_SERVER",
                source_utc_offset_hours=SOURCE_UTC_OFFSET_HOURS,
                reference_start_broker=_broker_iso(reference_start),
                reference_end_broker=_broker_iso(reference_end),
                reference_start_utc=_iso(reference_start),
                reference_end_utc=_iso(reference_end),
                attack_start_time_utc=_iso(attack_start),
                sweep_extreme_time_utc=_iso(extreme_time),
                sweep_extreme_time_broker=_broker_iso(extreme_time),
                reclaim_time_utc=_iso(bar["t"]),
                reclaim_time_broker=_broker_iso(bar["t"]),
                confirmation_time_utc=_iso(confirmation_time) if confirmation_time else None,
                confirmation_time_broker=_broker_iso(confirmation_time) if confirmation_time else None,
                signal_time_utc=_iso(entry_bar["t"]),
                order_time_utc=_iso(entry_bar["t"]),
                fill_time_utc=_iso(entry_bar["t"]),
                fill_model="IDEALIZED_SIGNAL_BAR_CLOSE",
                sweep_extreme=extreme, reclaim_clearance_fraction=clearance,
                entry=entry, stop=stop, target_4r=entry + sign * 4 * R,
                target_5r=entry + sign * 5 * R, structural_margin=margin,
                required_structural_risk_pct=required_risk_pct,
                contract_risk_pct=0.25,
                setup_status="DETECTED",
                entry_status="ELIGIBLE" if structural_ok else "REJECTED",
                all_failed_gates=failed,
                status="CANDIDATE" if structural_ok else "REJECTED",
                reason_code="SIGNAL_ACCEPTED" if structural_ok else "FIXED_RISK_SL_INSIDE_SWEEP_EXTREME",
            )
    return None


def realize(signal: Signal, future: list[dict]) -> dict:
    if signal.status != "CANDIDATE":
        return {"outcome": "STRUCTURAL_REJECT", "r": None}
    short = signal.direction == "SHORT"
    partial = False
    for bar in future:
        stop = bar["h"] >= signal.stop if short else bar["l"] <= signal.stop
        hit4 = bar["l"] <= signal.target_4r if short else bar["h"] >= signal.target_4r
        hit5 = bar["l"] <= signal.target_5r if short else bar["h"] >= signal.target_5r
        if stop:  # STOP_FIRST, including collisions
            return {"outcome": "PARTIAL_THEN_BE" if partial else "STOP", "r": 3.0 if partial else -1.0}
        if hit5:
            return {"outcome": "TP5", "r": 4.25 if partial else 5.0}
        if hit4 and not partial:
            partial = True
    return {"outcome": "OPEN_AT_END", "r": 3.0 if partial else 0.0}


def run(path: Path, d0: dt.date, d1: dt.date, clearance: float) -> list[dict]:
    bars = load_bars(path)
    results = []
    day = d0
    while day <= d1:
        D = dt.datetime.combine(day, dt.time())
        ref = window(bars, D, D.replace(hour=8))
        execution = window(bars, D.replace(hour=8), D.replace(hour=16))
        if len(ref) == 32 and execution:
            for variant in ("SWEEP_CLOSE_ENTRY", "POST_SWEEP_CONFIRMATION_ENTRY"):
                for direction in ("LONG", "SHORT"):
                    sig = find_sweep_signal(D, ref, execution, variant, clearance, direction)
                    if sig:
                        entry_t = dt.datetime.fromisoformat(sig.normalized_timestamp_utc.removesuffix("Z"))
                        future = [b for b in bars if b["t"] > entry_t and b["t"] < D + dt.timedelta(days=1)]
                        results.append({**asdict(sig), "bias_gate": "DEFERRED_B1",
                                        **realize(sig, future)})
        day += dt.timedelta(days=1)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--from", dest="d0", default="2022-10-03")
    ap.add_argument("--to", dest="d1", default="2022-10-21")
    ap.add_argument("--clearance", type=float, default=0.025)
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = run(args.data, dt.date.fromisoformat(args.d0), dt.date.fromisoformat(args.d1), args.clearance)
    print("SESSION_SWEEP_ENTRY_EXPERIMENT 0.2.0 · RESEARCH ONLY · sealed data excluded")
    for variant in ("SWEEP_CLOSE_ENTRY", "POST_SWEEP_CONFIRMATION_ENTRY"):
        sample = [r for r in rows if r["variant"] == variant]
        accepted = [r for r in sample if r["status"] == "CANDIDATE"]
        net = sum(r["r"] for r in accepted if r["r"] is not None)
        print(f"{variant:<32} signals={len(sample):2d} accepted={len(accepted):2d} "
              f"structural_rejects={len(sample)-len(accepted):2d} net={net:+.3f}R")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"records -> {args.json}")
    print("Diagnostic sample only. No rule is promoted by this result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
