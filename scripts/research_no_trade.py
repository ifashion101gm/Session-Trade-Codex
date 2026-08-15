"""Compare canonical no-trade decisions with experimental profile/stop diagnostics."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, datetime, timezone
from pathlib import Path
import json
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.config import load_config
from session_strategy.engine import (classify_session, detect_sweep, execution_bounds,
                                     filter_window, lock_asian_levels, session_bounds,
                                     validate_candles)
from session_strategy.mt5_gateway import MT5ReadOnlyGateway
from session_strategy.research_optimization import atr, dynamic_stop, session_volume_profile


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", default=str(ROOT / "outputs" / "research_no_trade"))
    args = parser.parse_args()
    trading_date = date.fromisoformat(args.date)
    strategy = load_config()
    research = yaml.safe_load((ROOT / "config" / "no_trade_research.yaml").read_text())
    now = datetime.now(timezone.utc)
    asian_start, asian_end = session_bounds(trading_date, strategy)
    exec_start, exec_end = execution_bounds(trading_date, strategy)
    if now < exec_end:
        raise SystemExit(f"Session is incomplete until {exec_end.isoformat()}")
    report = {
        "mode": "HISTORICAL_RESEARCH_ONLY", "production_engine_changed": False,
        "trading_date": args.date, "canonical_config_hash": strategy.hash,
        "warning": "M15 tick volume is a proxy; this is not a trained ML model or trading signal.",
        "symbols": {},
    }
    with MT5ReadOnlyGateway(strategy.execution_permissions) as gateway:
        offset = gateway.broker_utc_offset(
            [strategy.broker_symbol(s) for s in strategy.symbols], now,
            strategy.maximum_tick_age_seconds)
        report["broker_utc_offset_hours"] = offset
        for symbol, limits in strategy.symbols.items():
            broker = limits.broker_symbol
            session = filter_window(gateway.candles(broker, asian_start, asian_end, offset),
                                    asian_start, asian_end)
            execution = filter_window(gateway.candles(broker, exec_start, exec_end, offset),
                                      exec_start, exec_end)
            session_ok, session_detail = validate_candles(
                session, asian_start, strategy.session_candles, strategy, now=now)
            execution_ok, execution_detail = validate_candles(
                execution, exec_start, strategy.post_session_candles, strategy, now=now)
            if not session_ok or not execution_ok:
                report["symbols"][symbol] = {"status": "REJECTED_DATA_QUALITY",
                                             "session": session_detail,
                                             "execution": execution_detail}
                continue
            levels = lock_asian_levels(session, strategy)
            profile_cfg = research["volume_profile"]
            profile = session_volume_profile(session, int(profile_cfg["bins"]),
                                             float(profile_cfg["value_area_fraction"]))
            range_ok = limits.minimum_range <= levels.range <= limits.maximum_range
            item = {
                "canonical": {
                    "status": "ELIGIBLE" if range_ok else "NO_TRADE_RANGE_BOUNDS",
                    "session_type": classify_session(levels, strategy),
                    "range": levels.range, "minimum_range": limits.minimum_range,
                    "maximum_range": limits.maximum_range,
                    "quartile_25": levels.lower_quartile, "midpoint_50": levels.midpoint,
                    "quartile_75": levels.upper_quartile,
                },
                "experimental_volume_profile": profile.to_dict(),
                "experimental_sweep_stops": [],
                "canonical_decision_overridden": False,
            }
            period = int(research["dynamic_stop"]["atr_period"])
            history = session + execution
            atr_value = atr(history, period)
            multiplier = float(research["dynamic_stop"]["multipliers"][symbol])
            for candle in execution:
                signal = detect_sweep(candle, levels, strategy)
                if not signal:
                    continue
                stop, distance = dynamic_stop(
                    candle.close, signal["extreme"], signal["direction"], atr_value,
                    multiplier, limits.maximum_spread)
                item["experimental_sweep_stops"].append({
                    "signal_time_utc": candle.time.isoformat().replace("+00:00", "Z"),
                    "direction": signal["direction"], "entry_close": candle.close,
                    "sweep_extreme": signal["extreme"], "atr_14": atr_value,
                    "atr_multiplier": multiplier, "spread_ceiling_proxy": limits.maximum_spread,
                    "candidate_stop": stop, "candidate_stop_distance": distance,
                    "candidate_tp5r": candle.close + (5 * distance if signal["direction"] == "LONG"
                                                       else -5 * distance),
                })
            report["symbols"][symbol] = item
    folder = Path(args.output) / args.date
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "no_trade_research.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path.resolve()), **report}, indent=2))


if __name__ == "__main__":
    main()
