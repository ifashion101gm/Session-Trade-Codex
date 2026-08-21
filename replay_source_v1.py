"""Read-only, historical SESSION_SOURCE_V1 replay utility."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path

from session_strategy.engine import filter_window, validate_candles
from session_strategy.mt5_gateway import MT5ReadOnlyGateway
from session_strategy.source_v1 import classify, detect, levels, realize


SYMBOLS = {"EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
           "XAUUSD": "XAUUSD.crp"}


def bounds(day: date):
    return (datetime.combine(day - timedelta(days=1), time(22), timezone.utc),
            datetime.combine(day, time(7), timezone.utc),
            datetime.combine(day, time(11), timezone.utc))


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--broker-offset-hours", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    day = date.fromisoformat(args.date)
    session_start, session_end, replay_end = bounds(day)
    report = {"strategy_id": "SESSION_SOURCE_V1", "trading_date": day.isoformat(),
              "read_only": True, "broker_offset_hours": args.broker_offset_hours,
              "symbols": {}}
    with MT5ReadOnlyGateway({"submit_orders": False, "modify_orders": False,
                             "close_positions": False}) as gateway:
        for logical, broker in SYMBOLS.items():
            row = {"broker_symbol": broker}
            try:
                all_candles = gateway.candles(broker, session_start, replay_end,
                                              args.broker_offset_hours)
                session = filter_window(all_candles, session_start, session_end)
                execution = filter_window(all_candles, session_end, replay_end)
                session_ok, session_detail = validate_candles(session, session_start, 36)
                exec_ok, exec_detail = validate_candles(execution, session_end, 16)
                row.update(data_valid=session_ok and exec_ok, session_data=session_detail,
                           execution_data=exec_detail)
                if not row["data_valid"]:
                    row.update(eligible=False, classification=None, setup=None,
                               reason="INVALID_REPLAY_DATA")
                else:
                    lv = levels(session)
                    session_type = classify(lv)
                    trade = detect(session_type, lv, execution)
                    row.update(levels=lv, classification=session_type,
                               eligible=session_type != "UNCERTAIN", setup=None)
                    if trade:
                        signal_index = next(i for i, c in enumerate(execution)
                                            if c.time.isoformat().replace("+00:00", "Z") == trade.signal_time)
                        realize(trade, execution[signal_index:])
                        row.update(setup=trade.to_dict())
                    else:
                        row["reason"] = ("AMBIGUOUS_CLASSIFICATION" if session_type == "UNCERTAIN"
                                         else "NO_SETUP_IN_REPLAY_WINDOW")
            except Exception as exc:
                row.update(data_valid=False, eligible=False, classification=None, setup=None,
                           reason="DATA_RETRIEVAL_FAILURE", error=str(exc))
            report["symbols"][logical] = row
    payload = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
