"""Canonical classification-only funnel for SESSION_FLOW_V2_SIMPLE.

The module has no broker, ticket, fill, or performance side effects. Downstream stages
remain explicit unavailable states until separately implemented and authorized.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from datetime import date
from typing import Iterable

from .session_contract import EntryEngine, SessionType, SetupType, StrategySelection


@dataclass(frozen=True)
class FunnelRecord:
    contract_id: str
    contract_version: str
    symbol: str
    trading_date: date
    leg: str
    reference_session: str
    reference_valid: bool
    reason_code: str
    efficiency_ratio: float | None = None
    session_type: SessionType | None = None
    sweep_evaluated: bool = False
    sweep_qualified: bool | None = None
    setup_type: SetupType | None = None
    entry_engine: EntryEngine | None = None
    direction: str | None = None
    entry_status: str = "NOT_APPLICABLE"
    ticket_status: str = "NOT_AUTHORIZED"
    fill_status: str = "NOT_AUTHORIZED"
    result_status: str = "NOT_CALCULATED"

    @property
    def key(self) -> tuple[str, str, date, str, str]:
        return (self.contract_version, self.symbol, self.trading_date, self.leg,
                self.reference_session)

    def serializable(self) -> dict:
        row = asdict(self)
        row["trading_date"] = self.trading_date.isoformat()
        for field in ("session_type", "setup_type", "entry_engine"):
            value = row[field]
            row[field] = value.value if value is not None else None
        return row


def record_from_selection(symbol: str, trading_date: date, leg: str,
                          reference_session: str,
                          selection: StrategySelection) -> FunnelRecord:
    if selection.setup_type is SetupType.TREND:
        entry_status = selection.entry_status
    elif selection.setup_type is SetupType.SWEEP:
        entry_status = selection.entry_status.replace("BLOCKED_BY_ENTRY_2_SPEC",
                                                       "SWEEP_ENTRY_SPEC_BLOCKED")
    else:
        entry_status = "RANGE_ENTRY_IMPLEMENTATION_BLOCKED"
    return FunnelRecord(
        "SESSION_FLOW_V2_SIMPLE", "2.1-simple", symbol, trading_date, leg,
        reference_session, True, "CLASSIFIED", selection.efficiency_ratio,
        selection.session_type, selection.session_type is SessionType.RANGE,
        None if selection.session_type is SessionType.TREND else
        bool(selection.sweep and selection.sweep.qualified),
        selection.setup_type, selection.entry_engine, selection.direction,
        entry_status,
    )


def invalid_record(symbol: str, trading_date: date, leg: str,
                   reference_session: str, reason: str) -> FunnelRecord:
    return FunnelRecord("SESSION_FLOW_V2_SIMPLE", "2.1-simple", symbol, trading_date,
                        leg, reference_session, False, reason,
                        entry_status="NOT_APPLICABLE")


def summarize_funnel(records: Iterable[FunnelRecord], expected: int | None = None) -> dict:
    rows = list(records)
    keys = [row.key for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("DUPLICATE_FUNNEL_OWNER: contract/symbol/date/leg/reference must be unique")
    for row in rows:
        if not row.reference_valid:
            if any((row.session_type, row.setup_type, row.entry_engine)):
                raise ValueError("INVALID_REFERENCE_ENTERED_CLASSIFICATION")
            continue
        owners = sum(row.entry_engine is engine for engine in EntryEngine)
        if owners != 1:
            raise ValueError("ENTRY_ENGINE_OWNERSHIP_MUST_BE_EXACTLY_ONE")
        if row.session_type is SessionType.TREND:
            if row.sweep_evaluated or row.sweep_qualified is not None or \
                    row.setup_type is not SetupType.TREND or \
                    row.entry_engine is not EntryEngine.ENTRY_1:
                raise ValueError("INVALID_TREND_FUNNEL_LINEAGE")
        elif row.session_type is SessionType.RANGE:
            expected_setup = SetupType.SWEEP if row.sweep_qualified else SetupType.RANGE
            expected_engine = EntryEngine.ENTRY_2 if row.sweep_qualified else EntryEngine.ENTRY_3
            if not row.sweep_evaluated or row.sweep_qualified is None or \
                    row.setup_type is not expected_setup or row.entry_engine is not expected_engine:
                raise ValueError("INVALID_RANGE_FUNNEL_LINEAGE")
        else:
            raise ValueError("VALID_REFERENCE_MISSING_SESSION_TYPE")

    valid = [row for row in rows if row.reference_valid]
    counts = Counter()
    counts["reference_expected"] = len(rows) if expected is None else expected
    counts["reference_valid"] = len(valid)
    counts["reference_invalid"] = len(rows) - len(valid)
    counts["trend_sessions"] = sum(r.session_type is SessionType.TREND for r in valid)
    counts["range_sessions"] = sum(r.session_type is SessionType.RANGE for r in valid)
    counts["range_with_sweep"] = sum(r.setup_type is SetupType.SWEEP for r in valid)
    counts["range_without_sweep"] = sum(r.setup_type is SetupType.RANGE for r in valid)
    counts["trend_setups"] = sum(r.setup_type is SetupType.TREND for r in valid)
    counts["sweep_setups"] = counts["range_with_sweep"]
    counts["range_setups"] = counts["range_without_sweep"]
    counts["entry_valid"] = sum(r.entry_status.startswith("VALID_") for r in valid)
    counts["entry_blocked"] = sum("BLOCKED" in r.entry_status for r in valid)
    counts["no_valid_entry"] = sum(r.entry_status.startswith("NO_VALID") for r in valid)
    counts["tickets"] = sum(r.ticket_status == "CREATED" for r in valid)
    counts["fills"] = sum(r.fill_status == "FILLED" for r in valid)
    counts["results"] = sum(r.result_status not in ("NOT_CALCULATED", "UNRESOLVED") for r in valid)

    equations = {
        "session_split": counts["trend_sessions"] + counts["range_sessions"] == counts["reference_valid"],
        "range_split": counts["range_with_sweep"] + counts["range_without_sweep"] == counts["range_sessions"],
        "setup_total": counts["trend_setups"] + counts["sweep_setups"] + counts["range_setups"] == counts["reference_valid"],
        "trend_setup": counts["trend_setups"] == counts["trend_sessions"],
        "sweep_setup": counts["sweep_setups"] == counts["range_with_sweep"],
        "range_setup": counts["range_setups"] == counts["range_without_sweep"],
    }
    def rate(numerator: int, denominator: int):
        return None if denominator == 0 else numerator / denominator

    metrics = {
        "valid_reference_rate": rate(counts["reference_valid"], counts["reference_expected"]),
        "trend_session_rate": rate(counts["trend_sessions"], counts["reference_valid"]),
        "range_session_rate": rate(counts["range_sessions"], counts["reference_valid"]),
        "sweep_rate_among_range_sessions": rate(counts["sweep_setups"], counts["range_sessions"]),
        "range_setup_rate_among_range_sessions": rate(counts["range_setups"], counts["range_sessions"]),
    }
    for setup in SetupType:
        population = [row for row in valid if row.setup_type is setup]
        prefix = setup.value.lower()
        valid_entries = sum(row.entry_status.startswith("VALID_") for row in population)
        tickets = sum(row.ticket_status == "CREATED" for row in population)
        fills = sum(row.fill_status == "FILLED" for row in population)
        metrics[f"{prefix}_entry_valid_rate"] = rate(valid_entries, len(population))
        metrics[f"{prefix}_ticket_rate"] = rate(tickets, len(population))
        metrics[f"{prefix}_fill_rate"] = rate(fills, tickets)
        metrics[f"{prefix}_stop_rate_per_fill"] = None
        metrics[f"{prefix}_4r_rate_per_fill"] = None
        metrics[f"{prefix}_5r_rate_per_fill"] = None
    return {"counts": dict(counts), "metrics": metrics, "equations": equations,
            "funnel_reconciles": all(equations.values())}
