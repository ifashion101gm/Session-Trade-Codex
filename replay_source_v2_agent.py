"""Strict read-only SOURCE_V2 agent backtest for one historical day."""
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys

from session_strategy.engine import filter_window, validate_candles
from session_strategy.mt5_gateway import MT5ReadOnlyGateway
from session_strategy.source_v1 import detect, levels, realize
from session_strategy.source_v2 import (combined_bias, h1_structure, range_or_trend,
                                        source_v2_agent_bounds)


SYMBOLS = {"EURUSD": ("EURUSD", .0001), "GBPUSD": ("GBPUSD", .0001),
           "XAUUSD": ("XAUUSD.crp", .01)}


def main() -> int:
    day, output = date.fromisoformat(sys.argv[1]), Path(sys.argv[2])
    start, lock, expiry = source_v2_agent_bounds(day)
    observe_end = datetime.combine(day + timedelta(days=1), time(0), timezone.utc)
    report = {"strategy_id": "SESSION_USER_RESOLVED_V2_AGENT",
              "contract_version": "2.2-backtest", "date": day.isoformat(),
              "read_only": True, "orders_submitted": 0, "orders_modified": 0,
              "orders_closed": 0, "window_utc": {"asian_start": start.isoformat(),
              "lock": lock.isoformat(), "hard_expiry": expiry.isoformat()},
              "actionable_closes_local": ["08:15","08:30","08:45","09:00","09:15","09:30"],
              "spread_model": "NOT_AVAILABLE_IN_MT5_OHLC_HISTORY; gate not asserted",
              "symbols": {}}
    with MT5ReadOnlyGateway({}) as gateway:
        for logical, (broker, pip) in SYMBOLS.items():
            row = {"broker_symbol": broker}
            try:
                m15 = gateway.candles(broker, start, observe_end, 3)
                session = filter_window(m15, start, lock)
                entries = filter_window(m15, lock, expiry)
                outcome = filter_window(m15, lock, observe_end)
                ok, detail = validate_candles(session, start, 32)
                h1 = gateway.h1_candles(broker, lock - timedelta(hours=50), lock, 3)
                h1 = [c for c in h1 if c.time + timedelta(hours=1) <= lock][-48:]
                structure = h1_structure(h1, 2 * pip)
                bias = combined_bias(session, structure) if ok else "UNCERTAIN"
                state = range_or_trend(session) if ok else None
                lv = levels(session) if ok else None
                eligible = ok and bias != "UNCERTAIN"
                trade = None
                rejection = None
                if not ok: rejection = "INVALID_SESSION_DATA"
                elif bias == "UNCERTAIN": rejection = "UNCERTAIN_H1_OR_DIRECTION_DISAGREEMENT"
                else:
                    detector_type = "RANGE" if state == "RANGE" else bias + "_TREND"
                    candidate = detect(detector_type, lv, entries)
                    if candidate and ((candidate.direction == "LONG") != (bias == "BULLISH")):
                        rejection = "SETUP_DIRECTION_DISAGREES_WITH_H1_BIAS"
                    else: trade = candidate
                    if not candidate: rejection = "NO_SETUP_BEFORE_HARD_EXPIRY"
                if trade:
                    signal = datetime.fromisoformat(trade.signal_time.replace("Z", "+00:00"))
                    realize(trade, [c for c in outcome if c.time >= signal])
                row.update(data_valid=ok, data_detail=detail, session_levels=lv,
                           h1_candles=len(h1), h1_structure=structure,
                           combined_bias=bias, classification=state, eligible=eligible,
                           spread_gate_measured=False, setup=trade.to_dict() if trade else None,
                           rejection_reason=rejection, realized_r=trade.outcome_r if trade else 0.0)
            except Exception as exc:
                row.update(data_valid=False, eligible=False, setup=None, realized_r=0.0,
                           rejection_reason="DATA_RETRIEVAL_FAILURE", error=str(exc))
            report["symbols"][logical] = row
    report["portfolio_realized_r"] = sum(x["realized_r"] for x in report["symbols"].values())
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
