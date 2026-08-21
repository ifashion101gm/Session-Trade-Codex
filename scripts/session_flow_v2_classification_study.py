"""Classification-only SESSION_FLOW_V2_SIMPLE study; no fills or orders."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from session_strategy.session_contract import (
    M15Bar,
    SESSION_FLOW_V2_LEGS,
    classify_completed_box,
)
from session_strategy.v2_funnel import invalid_record, record_from_selection, summarize_funnel


SOURCES = {
    "EURUSD": ROOT / "data" / "eurusd_m15_2022_10.master.csv",
    "GBPUSD": ROOT / "data" / "gbpusd_m15_2022_10.master.csv",
    "USDJPY": ROOT / "data" / "usdjpy_m15_2022_10.master.csv",
}
START = date(2022, 10, 3)
END = date(2022, 10, 21)
OUT_DIR = ROOT / "outputs" / "session_flow_v2_classification_2022-10-03_2022-10-21"


def load_bars(path: Path) -> dict[datetime, M15Bar]:
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            when = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
            result[when] = M15Bar(
                when, float(row["open"]), float(row["high"]),
                float(row["low"]), float(row["close"]),
            )
    return result


def weekdays(start: date, end: date):
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def run_study() -> tuple[list[dict], dict]:
    records = []
    details = []
    for symbol, source in SOURCES.items():
        indexed = load_bars(source)
        for trading_date in weekdays(START, END):
            for leg_key, leg in SESSION_FLOW_V2_LEGS.items():
                start, _ = leg.bounds(trading_date)
                candles = [indexed.get(start + timedelta(minutes=15 * i))
                           for i in range(leg.expected_m15_candles)]
                if any(candle is None for candle in candles):
                    record = invalid_record(symbol, trading_date, leg_key,
                                            leg.reference, "INVALID_REFERENCE_MISSING_BARS")
                    records.append(record)
                    details.append(record.serializable())
                    continue
                selection = classify_completed_box(leg, trading_date, candles)
                record = record_from_selection(symbol, trading_date, leg_key,
                                               leg.reference, selection)
                records.append(record)
                row = record.serializable()
                sweep = selection.sweep
                row.update({
                    "sweep_candidate_index": None if sweep is None else sweep.candidate_index,
                    "sweep_candidate_time": None if sweep is None or sweep.candidate_time is None
                    else sweep.candidate_time.isoformat(),
                    "sweep_side": None if sweep is None or sweep.side is None else sweep.side.value,
                    "sweep_prior_level": None if sweep is None else sweep.prior_level,
                    "sweep_extreme": None if sweep is None else sweep.extreme,
                    "sweep_close": None if sweep is None else sweep.close,
                })
                details.append(row)
    return details, summarize_funnel(records, expected=len(records))


def main() -> None:
    details, summary = run_study()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "classification_records.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    payload = {
        "contract_id": "SESSION_FLOW_V2_SIMPLE",
        "contract_version": "2.1-simple",
        "study": "CLASSIFICATION_ONLY",
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "symbols": list(SOURCES),
        "execution_metrics": "NOT_AUTHORIZED_NOT_CALCULATED",
        **summary,
    }
    (OUT_DIR / "funnel_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
