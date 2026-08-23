"""Create the non-authoritative October V2 feature and reconciliation reports."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from session_strategy.session_contract import M15Bar
from session_strategy.v2_research import (
    V2_REFERENCE_LEGS,
    er_040_research_candidate,
    extract_reference_features,
    freeze_v2_reference_box,
    midpoint_side_research_candidate,
)


DATA = ROOT / "data" / "eurusd_m15_2022_10.master.csv"
ORACLE = ROOT / "benchmarks" / "oracle_30.csv"
OUT_FEATURES = ROOT / "SESSION_V2_REGIME_FEATURES.csv"
OUT_RECON = ROOT / "SESSION_V2_ROUTER_RECONCILIATION.csv"
OUT_REPORT = ROOT / "SESSION_V2_REGIME_RESEARCH.md"

# Owner-supplied validation labels from the attached V2 upgrade ruling. These are
# reconciliation data, never inputs to the strategy engine.
EXPECTED = {
    ("2022-10-03", "A->L"): ("SWEEP", "SHORT"), ("2022-10-03", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-04", "A->L"): ("RANGE", "LONG"), ("2022-10-04", "L->NY"): ("TREND", "LONG"),
    ("2022-10-05", "A->L"): ("TREND", "LONG"), ("2022-10-05", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-06", "A->L"): ("RANGE", "LONG"), ("2022-10-06", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-07", "A->L"): ("RANGE", "SHORT"), ("2022-10-07", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-10", "A->L"): ("RANGE", "SHORT"), ("2022-10-10", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-11", "A->L"): ("SWEEP", "LONG"), ("2022-10-11", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-12", "A->L"): ("RANGE", "LONG"), ("2022-10-12", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-13", "A->L"): ("RANGE", "SHORT"), ("2022-10-13", "L->NY"): ("TREND", "LONG"),
    ("2022-10-14", "A->L"): ("SWEEP", "SHORT"), ("2022-10-14", "L->NY"): ("RANGE", "SHORT"),
    ("2022-10-17", "A->L"): ("RANGE", "SHORT"), ("2022-10-17", "L->NY"): ("SWEEP", "LONG"),
    ("2022-10-18", "A->L"): ("TREND", "LONG"), ("2022-10-18", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-19", "A->L"): ("TREND", "SHORT"), ("2022-10-19", "L->NY"): ("TREND", "SHORT"),
    ("2022-10-20", "A->L"): ("TREND", "LONG"), ("2022-10-20", "L->NY"): ("RANGE", "LONG"),
    ("2022-10-21", "A->L"): ("TREND", "SHORT"), ("2022-10-21", "L->NY"): ("TREND", "SHORT"),
}


def load_bars() -> dict[datetime, M15Bar]:
    result = {}
    with DATA.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            when = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
            result[when] = M15Bar(when, float(row["open"]), float(row["high"]),
                                  float(row["low"]), float(row["close"]))
    return result


def build_rows():
    indexed = load_bars()
    features = []
    reconciliation = []
    with ORACLE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            trading_date = date.fromisoformat(row["date"])
            reference = "ASIAN_REFERENCE" if row["leg"] == "A->L" else "LONDON_REFERENCE"
            _, start_time, _, expected = V2_REFERENCE_LEGS[reference]
            start = datetime.combine(trading_date, start_time, tzinfo=timezone.utc)
            candles = [indexed[start + timedelta(minutes=15 * index)]
                        for index in range(expected)]
            session = freeze_v2_reference_box(reference, trading_date, candles,
                                               start + timedelta(minutes=15 * expected))
            values = extract_reference_features(session).serializable()
            values.update({"slot": row["slot"], "date": row["date"], "leg": row["leg"],
                           "reference_session": reference})
            features.append(values)
            expected_setup_value, expected_direction = EXPECTED[(row["date"], row["leg"])]
            expected_regime = "TREND" if expected_setup_value == "TREND" else "RANGE"
            er_candidate = er_040_research_candidate(extract_reference_features(session))
            midpoint_candidate = midpoint_side_research_candidate(extract_reference_features(session))
            reconciliation.append({
                "slot": row["slot"], "date": row["date"], "leg": row["leg"],
                "reference_session": reference, "expected_setup": expected_setup_value,
                "expected_regime": expected_regime, "er_040_candidate": er_candidate,
                "midpoint_side_candidate": midpoint_candidate,
                "er_regime_match": er_candidate == expected_regime,
                "midpoint_regime_match": midpoint_candidate == expected_regime,
                "expected_direction": expected_direction,
                "legacy_csv_setup": row["eng_setup"],
                "legacy_csv_direction": row["eng_dir"],
                "bias_status": "RESEARCH_NOT_SELECTED",
                "fill_status": "UNAVAILABLE_NO_M1_BID_ASK",
                "outcome_used_for_classification": "NO",
            })
    return features, reconciliation


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    features, rows = build_rows()
    write_csv(OUT_FEATURES, features)
    write_csv(OUT_RECON, rows)
    expected = Counter(row["expected_regime"] for row in rows)
    er_matches = sum(row["er_regime_match"] for row in rows)
    midpoint_matches = sum(row["midpoint_regime_match"] for row in rows)
    setup_counts = Counter(row["expected_setup"] for row in rows)
    OUT_REPORT.write_text(
        "# SESSION V2 October Regime Research\n\n"
        "Date: 2026-08-23\n"
        "Status: **RESEARCH / NO AUTHORITATIVE CLASSIFIER SELECTED**\n\n"
        "The feature table is calculated only from the 30 completed EURUSD M15 reference "
        "boxes. Historical labels are used only for reconciliation. No outcome, post-box "
        "candle, or fill field is used by feature extraction or candidate classification.\n\n"
        f"- Cases: {len(rows)}\n"
        f"- Labelled regime population: {dict(expected)}\n"
        f"- Owner-labelled setup population: {dict(setup_counts)}\n"
        f"- ER 0.40 research candidate agreement: {er_matches}/{len(rows)}\n"
        f"- Midpoint-side research candidate agreement: {midpoint_matches}/{len(rows)}\n\n"
        "The attachment separately declares 16 Trend and 14 Range-regime cases, but its "
        "explicit 30-row case list yields 17 Trend and 13 Range-regime cases. This is an "
        "unresolved owner-data conflict; no label was changed.\n\n"
        "Both candidates remain research evidence only. Agreement with a small labelled "
        "sample does not validate a classifier or authorize execution. Trend Bias V1 and "
        "strict Sweep evidence require separate reports and unseen-data validation.\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} cases: {OUT_FEATURES.name}, {OUT_RECON.name}, {OUT_REPORT.name}")


if __name__ == "__main__":
    main()