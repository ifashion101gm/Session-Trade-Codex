"""Historical, read-only SOURCE_V2 qualification replay."""
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys

from session_strategy.engine import filter_window, validate_candles
from session_strategy.mt5_gateway import MT5ReadOnlyGateway
from session_strategy.source_v1 import detect, levels, realize
from session_strategy.source_v2 import (combined_bias, h1_structure, range_or_trend,
                                        source_v2_bounds)


def main() -> int:
    day = date.fromisoformat(sys.argv[1])
    output = Path(sys.argv[2])
    start, lock, end = source_v2_bounds(day)
    outcome_end = datetime.combine(day + timedelta(days=1), time(0), timezone.utc)
    report = {"strategy_id": "SESSION_USER_RESOLVED_V2", "date": day.isoformat(),
              "read_only": True, "window_utc": [start.isoformat(), lock.isoformat(), end.isoformat()],
              "outcome_observation_end_utc": outcome_end.isoformat(),
              "symbols": {}}
    with MT5ReadOnlyGateway({}) as gateway:
        for symbol in ("EURUSD", "GBPUSD"):
            row = {}
            try:
                m15 = gateway.candles(symbol, start, outcome_end, 3)
                session, execution = filter_window(m15, start, lock), filter_window(m15, lock, end)
                outcome_candles = filter_window(m15, lock, outcome_end)
                ok, detail = validate_candles(session, start, 32)
                h1 = gateway.h1_candles(symbol, lock - timedelta(hours=50), lock, 3)
                h1 = [c for c in h1 if c.time + timedelta(hours=1) <= lock][-48:]
                pip = .0001
                structure = h1_structure(h1, 2 * pip)
                bias = combined_bias(session, structure) if ok else "UNCERTAIN"
                state = range_or_trend(session) if ok else None
                # Range setups do not require directional HTF agreement; trend setups do.
                eligible = ok and (state == "RANGE" or bias != "UNCERTAIN")
                trade = detect("RANGE" if state == "RANGE" else bias + "_TREND",
                               levels(session), execution) if eligible else None
                if trade:
                    i = next(i for i,c in enumerate(execution)
                             if c.time.isoformat().replace("+00:00","Z") == trade.signal_time)
                    signal_time = execution[i].time
                    realize(trade, [c for c in outcome_candles if c.time >= signal_time])
                row.update(data_valid=ok, data_detail=detail, h1_candles=len(h1),
                           h1_structure=structure, combined_bias=bias,
                           classification=state, eligible=eligible,
                           setup=trade.to_dict() if trade else None)
            except Exception as exc:
                row.update(data_valid=False, eligible=False, error=str(exc), setup=None)
            report["symbols"][symbol] = row
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
