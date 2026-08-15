"""Render all stored entries with Parameter / Result / Source basis tables."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "benchmarks" / "entry_database.csv"
OUTPUT = ROOT / "benchmarks" / "entry_database_report.md"


def main() -> int:
    with DATABASE.open(newline="", encoding="utf-8") as handle:
        trades = list(csv.DictReader(handle))
    lines = ["# Session Strategy Entry Database", "",
             "Every result is mapped to its recorded strategy contract. Rows marked "
             "`REPLAY_REQUIRED` are legacy evidence and do not validate the active engine.", ""]
    for number, trade in enumerate(trades, 1):
        lines += [f"## {number}. {trade['entry_id']}", "",
                  "| Parameter | Result | Source-flowchart basis |",
                  "| :--- | :--- | :--- |",
                  f"| Date | {trade['date']} | Stored benchmark date |",
                  f"| Contract | v{trade.get('contract_version', 'UNKNOWN')} / {trade.get('active_contract_status', 'UNKNOWN')} | Evidence compatibility |",
                  f"| Reference | {trade['reference_session'].title()} {trade['reference_window']} UTC | Completed reference session |",
                  f"| Entry session | {trade['execution_session'].title()} | Following execution session |",
                  f"| Bias | {trade['bias'].title()} | Step 1: Determine Bias Trend |",
                  f"| Range Session? | {'Yes' if trade['session_state']=='RANGE' else 'No'} | Step 2: Is Range Session? |",
                  f"| Sweep During Session? | {trade['sweep_during_session'].title()} | Step 3 when Range = Yes |",
                  f"| Setup | {trade['setup'].title()} Setup | {trade['flowchart_path']} |",
                  f"| Direction | {trade['direction'].title()} | {'Swept boundary reversal direction' if trade['setup']=='SWEEP' else 'Frozen bias direction'} |",
                  f"| Signal | {trade['signal_time_utc']} | Closed M15 trigger |",
                  f"| Entry | {trade['entry']} | {trade['entry_rule']} |",
                  f"| Stop loss | {trade['stop']} ({trade['risk_pips']} pips) | {trade['stop_rule']} |",
                  f"| Leg A target | {trade['leg_a_target']} | {trade['management_rule']} |",
                  f"| TP5 | {trade['target_5r']} | {trade['target_rule']} |",
                  f"| Source outcome | {trade['source_outcome']} | Source/chart evidence |",
                  f"| Connected-feed outcome | {trade['feed_outcome']} | Bar-by-bar simulation |",
                  f"| Evidence | {trade['evidence_status']} | Validation status |", ""]
    OUTPUT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Wrote {len(trades)} entries to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
