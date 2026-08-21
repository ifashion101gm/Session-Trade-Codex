"""Outcome-blind TREND_BIAS_V2 candidate study; no entries, fills, or orders."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.session_flow_v2_classification_study import (  # noqa: E402
    END, SOURCES, START, load_bars, weekdays,
)
from session_strategy.session_contract import (  # noqa: E402
    SESSION_FLOW_V2_LEGS, SessionType, box_direction_v1, classify_completed_box,
)

OUT_DIR = ROOT / "outputs" / "trend_bias_v2_candidate_study_2022-10-03_2022-10-21"


def candidate_a(open_price: float, close_price: float) -> str:
    """Completed-box open-to-close sign, with exact equality unresolved."""
    return box_direction_v1(open_price, close_price) or "DIRECTION_UNRESOLVED"


def run_study() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    total_references = 0
    for symbol, source in SOURCES.items():
        indexed = load_bars(source)
        for trading_date in weekdays(START, END):
            for leg_key, leg in SESSION_FLOW_V2_LEGS.items():
                total_references += 1
                start, _ = leg.bounds(trading_date)
                candles = [indexed[start + i * timedelta(minutes=15)]
                           for i in range(leg.expected_m15_candles)]
                selection = classify_completed_box(leg, trading_date, candles)
                if selection.session_type is not SessionType.TREND:
                    continue
                box_open = float(candles[0].open)
                box_close = float(candles[-1].close)
                rows.append({
                    "symbol": symbol,
                    "trading_date": trading_date.isoformat(),
                    "leg": leg_key,
                    "reference": leg.reference,
                    "er": selection.efficiency_ratio,
                    "box_open": box_open,
                    "box_close": box_close,
                    "candidate_a": candidate_a(box_open, box_close),
                    "candidate_a_known_at": leg.activation_utc(trading_date).isoformat(),
                    "candidate_a_available_by_box_completion": True,
                    "candidate_b": "NOT_EVALUABLE_SPEC_INCOMPLETE",
                    "candidate_b_available_by_box_completion": "UNDEFINED",
                    "candidate_c": "NOT_EVALUABLE_SPEC_INCOMPLETE",
                    "candidate_c_available_by_box_completion": "UNDEFINED",
                    "a_vs_b": "NOT_COMPARABLE",
                    "a_vs_c": "NOT_COMPARABLE",
                    "b_vs_c": "NOT_COMPARABLE",
                })

    a_counts = Counter(row["candidate_a"] for row in rows)
    by_leg = {}
    for leg_key in SESSION_FLOW_V2_LEGS:
        leg_rows = [row for row in rows if row["leg"] == leg_key]
        leg_counts = Counter(row["candidate_a"] for row in leg_rows)
        by_leg[leg_key] = {
            "trend_references": len(leg_rows),
            "long": leg_counts["LONG"],
            "short": leg_counts["SHORT"],
            "unresolved": leg_counts["DIRECTION_UNRESOLVED"],
            "coverage_fraction": (len(leg_rows) - leg_counts["DIRECTION_UNRESOLVED"])
            / len(leg_rows) if leg_rows else None,
        }
    by_symbol = defaultdict(Counter)
    for row in rows:
        by_symbol[row["symbol"]][row["candidate_a"]] += 1

    summary = {
        "contract_id": "TREND_BIAS_V2",
        "study": "CANDIDATE_DIRECTION_ONLY_OUTCOME_BLIND",
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "symbols": list(SOURCES),
        "population": {
            "all_references": total_references,
            "trend_references": len(rows),
        },
        "candidate_a": {
            "rule": "CLOSE_GT_OPEN_LONG_CLOSE_LT_OPEN_SHORT_EQUAL_UNRESOLVED",
            "long": a_counts["LONG"],
            "short": a_counts["SHORT"],
            "unresolved": a_counts["DIRECTION_UNRESOLVED"],
            "coverage_fraction": (len(rows) - a_counts["DIRECTION_UNRESOLVED"])
            / len(rows) if rows else None,
            "available_by_box_completion": True,
            "by_leg": by_leg,
            "by_symbol": {symbol: dict(counts) for symbol, counts in by_symbol.items()},
        },
        "candidate_b": {
            "status": "NOT_EVALUABLE_SPEC_INCOMPLETE",
            "missing": ["timeframe", "feed", "structure_equation", "LONG_rule",
                        "SHORT_rule", "staleness_and_conflict_rules"],
        },
        "candidate_c": {
            "status": "NOT_EVALUABLE_SPEC_INCOMPLETE",
            "missing": ["source_context", "transfer_rule", "LONG_rule", "SHORT_rule",
                        "carry_duration", "missing_and_conflict_rules"],
        },
        "candidate_agreement": "NOT_CALCULABLE_UNTIL_B_AND_C_ARE_DEFINED",
        "trade_outcomes_used": False,
        "router_changed": False,
        "sweep_classifier_changed": False,
        "execution_or_scheduling": False,
    }
    return rows, summary


def main() -> None:
    rows, summary = run_study()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "trend_bias_records.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT_DIR / "trend_bias_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
