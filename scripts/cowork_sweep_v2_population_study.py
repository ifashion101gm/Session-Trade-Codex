"""Signal-population study for COWORK_SWEEP_V2; no orders, fills, or P&L."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.session_flow_v2_classification_study import (  # noqa: E402
    END, SOURCES, START, load_bars, weekdays,
)
from session_strategy.cowork_sweep_v2 import detect_range_session_sweeps  # noqa: E402
from session_strategy.session_contract import (  # noqa: E402
    SESSION_FLOW_V2_LEGS, SessionType, classify_trend_range,
    validate_and_freeze_session,
)

PIP_SIZE = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01}
EXECUTION_BARS = {"POST_ASIAN": 32, "POST_LONDON": 24}
OUT_DIR = ROOT / "outputs" / "cowork_sweep_v2_population_2022-10-03_2022-10-21"


def run_study() -> tuple[list[dict], dict]:
    rows = []
    for symbol, source in SOURCES.items():
        indexed = load_bars(source)
        for trading_date in weekdays(START, END):
            for leg_key, leg in SESSION_FLOW_V2_LEGS.items():
                start, end = leg.bounds(trading_date)
                reference = [indexed.get(start + timedelta(minutes=15 * i))
                             for i in range(leg.expected_m15_candles)]
                execution = [indexed.get(end + timedelta(minutes=15 * i))
                             for i in range(EXECUTION_BARS[leg_key])]
                if any(bar is None for bar in reference + execution):
                    rows.append({"symbol": symbol, "trading_date": trading_date.isoformat(),
                                 "leg": leg_key, "status": "INVALID_MISSING_BARS"})
                    continue
                frozen = validate_and_freeze_session(
                    leg, trading_date, reference, leg.activation_utc(trading_date))
                selection = classify_trend_range(frozen)
                row = {"symbol": symbol, "trading_date": trading_date.isoformat(),
                       "leg": leg_key, "status": "VALID",
                       "session_type": selection.session_type.value,
                       "cowork_sweep_count": 0, "first_direction": None,
                       "first_signal_time": None, "first_reference_price": None}
                if selection.session_type is SessionType.RANGE:
                    signals = detect_range_session_sweeps(
                        frozen, selection, execution, PIP_SIZE[symbol])
                    row["cowork_sweep_count"] = len(signals)
                    if signals:
                        row.update({"first_direction": signals[0].direction,
                                    "first_signal_time": signals[0].candle_time.isoformat(),
                                    "first_reference_price": signals[0].reference_price})
                rows.append(row)

    valid = [row for row in rows if row["status"] == "VALID"]
    range_rows = [row for row in valid if row["session_type"] == "RANGE"]
    with_sweep = [row for row in range_rows if row["cowork_sweep_count"] > 0]
    directions = Counter(row["first_direction"] for row in with_sweep)
    by_leg = {}
    for leg_key in SESSION_FLOW_V2_LEGS:
        leg_range = [row for row in range_rows if row["leg"] == leg_key]
        leg_sweep = [row for row in leg_range if row["cowork_sweep_count"] > 0]
        by_leg[leg_key] = {"range_cycles": len(leg_range),
                           "cycles_with_sweep": len(leg_sweep),
                           "cycles_without_sweep": len(leg_range) - len(leg_sweep),
                           "total_sweep_signals": sum(row["cowork_sweep_count"]
                                                      for row in leg_range)}
    summary = {
        "contract": "COWORK_SWEEP_V2",
        "study": "SIGNAL_POPULATION_ONLY_NO_ORDERS_FILLS_OR_PNL",
        "references": len(rows), "valid": len(valid),
        "trend_sessions": sum(row["session_type"] == "TREND" for row in valid),
        "range_sessions": len(range_rows),
        "range_cycles_with_cowork_sweep": len(with_sweep),
        "range_cycles_without_cowork_sweep": len(range_rows) - len(with_sweep),
        "total_cowork_sweep_signals": sum(row["cowork_sweep_count"] for row in range_rows),
        "first_signal_directions": dict(directions), "by_leg": by_leg,
        "retired_completed_box_population_comparable": False,
        "orders_fills_pnl": "NOT_CALCULATED",
    }
    return rows, summary


def main() -> None:
    rows, summary = run_study()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with (OUT_DIR / "records.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
