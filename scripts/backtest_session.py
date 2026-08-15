"""Read-only, one-session SSPF v2.2 backtest using MT5 M15 history."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.config import load_config
from session_strategy.engine import (classify_session, detect_range_rejection, detect_sweep,
                                     detect_trend_continuation, execution_bounds, filter_window,
                                     lock_asian_levels, session_bounds, trend_invalidated,
                                     validate_candles)
from session_strategy.mt5_gateway import MT5ReadOnlyGateway
from session_strategy.research_optimization import atr


def aligned(value: float, tick: float) -> float:
    return round(value / tick) * tick


def simulate(direction, entry, stop, tp1, tp2, candles, partial_r):
    long_side = direction == "LONG"
    partial_hit = False
    for candle in candles:
        stop_level = entry if partial_hit else stop
        stopped = candle.low <= stop_level if long_side else candle.high >= stop_level
        target1 = candle.high >= tp1 if long_side else candle.low <= tp1
        target2 = candle.high >= tp2 if long_side else candle.low <= tp2
        if stopped:  # canonical intrabar collision policy: STOP_FIRST
            return {"outcome": "PARTIAL_THEN_BREAKEVEN" if partial_hit else "STOP_LOSS",
                    "gross_r": 0.75 * partial_r if partial_hit else -1.0,
                    "exit_time_utc": candle.time.isoformat().replace("+00:00", "Z")}
        if not partial_hit and target1:
            partial_hit = True
            if target2:
                return {"outcome": "PARTIAL_AND_5R", "gross_r": 0.75 * partial_r + 1.25,
                        "exit_time_utc": candle.time.isoformat().replace("+00:00", "Z")}
        elif partial_hit and target2:
            return {"outcome": "PARTIAL_AND_5R", "gross_r": 0.75 * partial_r + 1.25,
                    "exit_time_utc": candle.time.isoformat().replace("+00:00", "Z")}
    if not candles:
        return {"outcome": "NO_HOLD_DATA", "gross_r": None, "exit_time_utc": None}
    final = candles[-1]
    risk = abs(entry - stop)
    sign = 1 if long_side else -1
    runner_r = sign * (final.close - entry) / risk
    gross_r = 0.75 * partial_r + 0.25 * runner_r if partial_hit else runner_r
    return {"outcome": "END_OF_DAY_EXIT", "gross_r": gross_r,
            "exit_price": final.close,
            "exit_time_utc": final.time.isoformat().replace("+00:00", "Z")}


def evaluate_setup(name, session_type, levels, execution, hold_candles, config, spec):
    eligible = session_type in config.setup_rules[name].session_types
    if not eligible:
        return {"setup": name, "status": "NOT_ELIGIBLE", "session_type": session_type}
    signal = signal_candle = None
    for candle in execution:
        if name == "TREND_CONTINUATION" and trend_invalidated(candle, session_type, levels):
            return {"setup": name, "status": "INVALIDATED", "session_type": session_type,
                    "invalidation_time_utc": candle.time.isoformat().replace("+00:00", "Z")}
        candidate = (detect_sweep(candle, levels, config) if name == "SWEEP" else
                     detect_range_rejection(candle, levels, config) if name == "RANGE_REJECTION" else
                     detect_trend_continuation(candle, session_type, levels, config))
        if candidate:
            signal, signal_candle = candidate, candle
            break
    if signal is None:
        return {"setup": name, "status": "NO_SETUP", "session_type": session_type}
    long_side = signal["direction"] == "LONG"
    if name == "SWEEP":
        raw_entry = (min(signal_candle.open, signal_candle.close) if long_side
                     else max(signal_candle.open, signal_candle.close))
    elif name == "RANGE_REJECTION":
        raw_entry = levels.low if long_side else levels.high
    else:
        raw_entry = levels.midpoint
    entry = aligned(raw_entry, spec.tick_size)
    risk = levels.risk_unit
    stop = aligned(entry - risk if long_side else entry + risk, spec.tick_size)
    if name == "SWEEP":
        buffer = config.stop_buffer_fraction * levels.range
        required = signal["extreme"] - buffer if long_side else signal["extreme"] + buffer
        clears = stop < required if long_side else stop > required
        if not clears:
            return {"setup": name, "status": "REJECTED_STRUCTURAL_STOP",
                    "session_type": session_type, "direction": signal["direction"],
                    "signal_time_utc": signal_candle.time.isoformat().replace("+00:00", "Z"),
                    "entry": entry, "stop_loss": stop, "sweep_extreme": signal["extreme"]}
    sign = 1 if long_side else -1
    tp1 = (aligned(levels.high if long_side else levels.low, spec.tick_size)
           if name in {"SWEEP", "RANGE_REJECTION"}
           else aligned(entry + sign * config.partial_target_r * risk, spec.tick_size))
    tp2 = aligned(entry + sign * config.final_target_r * risk, spec.tick_size)
    partial_r = abs(tp1 - entry) / risk
    later = [bar for bar in hold_candles if bar.time > signal_candle.time]
    outcome = simulate(signal["direction"], entry, stop, tp1, tp2, later, partial_r)
    return {"setup": name, "status": "TRIGGERED", "session_type": session_type,
            "direction": signal["direction"],
            "signal_time_utc": signal_candle.time.isoformat().replace("+00:00", "Z"),
            "entry": entry, "stop_loss": stop, "partial_target": tp1,
            "partial_target_r": partial_r,
            "partial_target_label": ("opposite session boundary"
                                     if name in {"SWEEP", "RANGE_REJECTION"} else "4R"),
            "runner_management": ("TRAIL_TO_5R_OR_FURTHER"
                                  if name == "TREND_CONTINUATION" else "BREAKEVEN_TO_5R"),
            "tp1_4r": tp1, "tp2_5r": tp2,
            **outcome}


def main():
    parser = ArgumentParser()
    parser.add_argument("--date", required=True, help="Trading date in UTC (YYYY-MM-DD)")
    parser.add_argument("--output", default=str(ROOT / "outputs" / "backtests"))
    args = parser.parse_args()
    trading_date = date.fromisoformat(args.date)
    config = load_config()
    research = yaml.safe_load((ROOT / "config" / "no_trade_research.yaml").read_text())
    now = datetime.now(timezone.utc)
    session_start, session_end = session_bounds(trading_date, config)
    exec_start, exec_end = execution_bounds(trading_date, config)
    if now < exec_end:
        raise SystemExit(f"Session is incomplete until {exec_end.isoformat()}")
    hold_end = datetime.combine(trading_date, datetime.strptime(
        research["backtest_lifecycle"]["position_hold_end_utc"], "%H:%M").time(), timezone.utc)
    report = {"strategy_id": config.strategy_id, "contract_version": config.contract_version,
              "config_hash": config.hash, "trading_date": args.date,
              "generated_utc": now.isoformat(), "read_only": True,
              "cost_basis": "GROSS_R; historical bid/ask spread unavailable in M15 OHLC",
              "intrabar_collision_policy": "STOP_FIRST", "symbols": {}}
    report["trend_runner_simulation"] = (
        "After the 4R partial, the runner stop moves to breakeven and its fixed target is 5R.")
    report["entry_window_end_utc"] = exec_end.isoformat()
    report["position_hold_end_utc"] = hold_end.isoformat()
    report["end_of_day_exit_policy"] = research["backtest_lifecycle"]["end_of_day_exit"]
    report["canonical_setup_priority"] = research["backtest_lifecycle"]["setup_priority"]
    with MT5ReadOnlyGateway(config.execution_permissions) as gateway:
        offset = gateway.broker_utc_offset(
            [config.broker_symbol(s) for s in config.symbols], now,
            config.maximum_tick_age_seconds)
        report["broker_utc_offset_hours"] = offset
        for symbol, limits in config.symbols.items():
            broker = limits.broker_symbol
            spec = gateway.symbol_spec(broker)
            session = filter_window(gateway.candles(broker, session_start, session_end, offset),
                                    session_start, session_end)
            execution = filter_window(gateway.candles(broker, exec_start, exec_end, offset),
                                      exec_start, exec_end)
            hold = filter_window(gateway.candles(broker, exec_start, hold_end, offset),
                                 exec_start, hold_end)
            session_ok, session_detail = validate_candles(
                session, session_start, config.session_candles, config, now=now)
            exec_ok, exec_detail = validate_candles(
                execution, exec_start, config.post_session_candles, config, now=now)
            item = {"broker_symbol": broker, "session_candles": len(session),
                    "execution_candles": len(execution), "data_quality": {
                        "passed": session_ok and exec_ok,
                        "session": session_detail, "execution": exec_detail}}
            if not session_ok or not exec_ok:
                item["status"] = "REJECTED_DATA_QUALITY"
                report["symbols"][symbol] = item
                continue
            levels = lock_asian_levels(session, config)
            session_type = classify_session(levels, config)
            range_min, range_max = limits.minimum_range, limits.maximum_range
            range_model = "STATIC_SYMBOL_BOUNDS"
            daily_atr = None
            if symbol in research["atr_range_bounds"].get("enabled_symbols", []):
                daily = gateway.daily_candles(
                    broker, session_start - timedelta(days=30), session_start, offset)
                daily = [bar for bar in daily if bar.time < session_start]
                period = int(research["atr_range_bounds"]["period"])
                daily_atr = atr(daily[-(period + 1):], period)
                range_min = float(research["atr_range_bounds"]["minimum_multiplier"]) * daily_atr
                range_max = float(research["atr_range_bounds"]["maximum_multiplier"]) * daily_atr
                range_model = "DAILY_ATR_14_DYNAMIC"
            range_ok = range_min <= levels.range <= range_max
            item.update({"status": "EVALUATED" if range_ok else "REJECTED_RANGE_BOUNDS",
                         "session_type": session_type, "asian_high": levels.high,
                         "asian_low": levels.low, "asian_range": levels.range,
                         "range_model": range_model, "range_minimum": range_min,
                         "range_maximum": range_max, "daily_atr_14": daily_atr,
                         "efficiency_ratio": levels.efficiency_ratio,
                         "close_location": levels.close_location})
            separate = ([evaluate_setup(name, session_type, levels, execution, hold, config, spec)
                         for name in research["backtest_lifecycle"]["setup_priority"]]
                        if range_ok else [])
            item["setups_separate_research"] = separate
            item["setups"] = []
            if range_ok:
                item["setups"] = [next((candidate for candidate in separate
                                        if candidate["status"] in
                                        {"TRIGGERED", "REJECTED_STRUCTURAL_STOP"}),
                                       {"setup": "NONE", "status": "NO_SETUP",
                                        "session_type": session_type})]
            report["symbols"][symbol] = item
    destination = Path(args.output) / args.date
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "session_backtest.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path.resolve()), **report}, indent=2))


if __name__ == "__main__":
    main()
