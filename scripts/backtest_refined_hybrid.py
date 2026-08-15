"""Historical SSPF v2.3 refined-hybrid research backtest; strictly read-only."""

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
from session_strategy.engine import execution_bounds, filter_window, session_bounds, validate_candles
from session_strategy.mt5_gateway import MT5ReadOnlyGateway
from session_strategy.refined_hybrid_validator import validate as validate_refined
from session_strategy.production_candidate_validator import validate as validate_production
from session_strategy.research_optimization import atr


def row(candle) -> dict:
    return {"time": candle.time.isoformat().replace("+00:00", "Z"),
            "open": candle.open, "high": candle.high, "low": candle.low,
            "close": candle.close, "tick_volume": candle.tick_volume}


def simulate(direction: str, entry: float, stop: float, target: float, candles: list) -> dict:
    long_side = direction == "LONG"
    for candle in candles:
        stopped = candle.low <= stop if long_side else candle.high >= stop
        targeted = candle.high >= target if long_side else candle.low <= target
        if stopped:  # conservative M15 collision rule
            return {"outcome": "STOP_LOSS", "gross_r": -1.0,
                    "exit_time_utc": candle.time.isoformat().replace("+00:00", "Z")}
        if targeted:
            return {"outcome": "TAKE_PROFIT_5R", "gross_r": 5.0,
                    "exit_time_utc": candle.time.isoformat().replace("+00:00", "Z")}
    if not candles:
        return {"outcome": "NO_HOLD_DATA", "gross_r": None, "exit_time_utc": None}
    final = candles[-1]
    risk = abs(entry - stop)
    sign = 1 if long_side else -1
    return {"outcome": "END_OF_DAY_EXIT",
            "gross_r": sign * (final.close - entry) / risk,
            "exit_price": final.close,
            "exit_time_utc": final.time.isoformat().replace("+00:00", "Z")}


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", default=str(ROOT / "outputs" / "backtests_refined"))
    parser.add_argument("--contract", choices=("refined", "production"), default="refined")
    args = parser.parse_args()
    trading_date = date.fromisoformat(args.date)
    canonical = load_config()
    research = yaml.safe_load((ROOT / "config" / "no_trade_research.yaml").read_text())
    config_key = "production_candidate" if args.contract == "production" else "refined_hybrid"
    cfg = research[config_key]
    validator = validate_production if args.contract == "production" else validate_refined
    now = datetime.now(timezone.utc)
    asian_start, asian_end = session_bounds(trading_date, canonical)
    exec_start, exec_end = execution_bounds(trading_date, canonical)
    hold_end = datetime.combine(trading_date,
                                datetime.strptime(cfg["maximum_hold_utc"], "%H:%M").time(),
                                timezone.utc)
    if now < hold_end:
        raise SystemExit(f"Hold window is incomplete until {hold_end.isoformat()}")
    report = {
        "strategy_id": cfg["strategy_id"], "mode": "READ_ONLY_RESEARCH",
        "trading_date": args.date, "generated_utc": now.isoformat(),
        "entry_window_utc": cfg["execution_window_utc"],
        "position_hold_end_utc": hold_end.isoformat(),
        "intrabar_collision_policy": "STOP_FIRST",
        "spread_basis": "CONFIGURED_MAXIMUM_PROXY; historical spread unavailable",
        "execution_authorized": False, "symbols": {},
    }
    with MT5ReadOnlyGateway(canonical.execution_permissions) as gateway:
        offset = gateway.broker_utc_offset(
            [canonical.broker_symbol(s) for s in canonical.symbols], now,
            canonical.maximum_tick_age_seconds)
        report["broker_utc_offset_hours"] = offset
        for symbol, limits in canonical.symbols.items():
            broker = limits.broker_symbol
            asian = filter_window(gateway.candles(broker, asian_start, asian_end, offset),
                                  asian_start, asian_end)
            execution = filter_window(gateway.candles(broker, exec_start, exec_end, offset),
                                      exec_start, exec_end)
            hold = filter_window(gateway.candles(broker, exec_start, hold_end, offset),
                                 exec_start, hold_end)
            m5 = gateway.m5_candles(broker, exec_start, exec_end, offset)
            h4 = gateway.h4_candles(broker, asian_start - timedelta(days=5), exec_end, offset)
            daily = gateway.daily_candles(
                broker, asian_start - timedelta(days=40), asian_start, offset)
            daily = [bar for bar in daily if bar.time < asian_start]
            session_ok, session_detail = validate_candles(
                asian, asian_start, canonical.session_candles, canonical, now=now)
            exec_ok, exec_detail = validate_candles(
                execution, exec_start, canonical.post_session_candles, canonical, now=now)
            item = {"broker_symbol": broker, "session_candles": len(asian),
                    "execution_candles": len(execution), "m5_candles": len(m5),
                    "h4_candles": len(h4), "data_quality": {
                        "passed": session_ok and exec_ok, "session": session_detail,
                        "execution": exec_detail}, "setups": []}
            if not session_ok or not exec_ok or len(daily) < 15:
                item["status"] = "REJECTED_DATA_QUALITY"
                report["symbols"][symbol] = item
                continue
            asian_high, asian_low = max(x.high for x in asian), min(x.low for x in asian)
            atr_14d = atr(daily[-15:], 14)
            accepted = None
            last_rejection = None
            for index, candle in enumerate(execution):
                closed_at = candle.time + timedelta(minutes=15)
                prior_m5 = [bar for bar in m5 if bar.time + timedelta(minutes=5) <= closed_at]
                prior_h4 = [bar for bar in h4 if bar.time + timedelta(hours=4) <= closed_at]
                payload = {
                    "symbol": symbol,
                    "current_time": candle.time.isoformat().replace("+00:00", "Z"),
                    "asian_session": {"high": asian_high, "low": asian_low,
                                      "start": asian_start.isoformat(), "end": asian_end.isoformat()},
                    "ohlcv_data": {
                        "atr_14d": atr_14d, "spread": limits.maximum_spread,
                        "pip_size": limits.display_pip_size,
                        "m15": [row(x) for x in asian + execution[:index + 1]],
                        "m5": [row(x) for x in prior_m5],
                        "h4": [row(x) for x in prior_h4],
                    },
                }
                decision = validator(payload, research)
                last_rejection = decision
                if decision["status"] == "SIGNAL_ACCEPTED":
                    accepted = (candle, decision)
                    break
            if accepted is None:
                item.update({"status": "NO_TRADE",
                             "rejection_reason": (last_rejection or {}).get("rejection_reason"),
                             "metrics": (last_rejection or {}).get("metrics", {})})
            else:
                signal_candle, decision = accepted
                params = decision["trade_parameters"]
                direction = "LONG" if params["action"].startswith("BUY") else "SHORT"
                later = [bar for bar in hold if bar.time > signal_candle.time]
                outcome = simulate(direction, params["entry_price"], params["stop_loss"],
                                   params["take_profit"], later)
                historical_spread = gateway.historical_spread(
                    broker, signal_candle.time + timedelta(minutes=15), offset)
                risk_distance = abs(params["entry_price"] - params["stop_loss"])
                spread_r = (historical_spread / risk_distance
                            if historical_spread is not None and risk_distance > 0 else None)
                if outcome["gross_r"] is not None and spread_r is not None:
                    outcome["net_r_historical_spread_only"] = outcome["gross_r"] - spread_r
                trade = {"setup": decision["metrics"]["selected_canonical_setup"],
                         "status": "TRIGGERED", "direction": direction,
                         "signal_time_utc": signal_candle.time.isoformat().replace("+00:00", "Z"),
                         "entry": params["entry_price"], "stop_loss": params["stop_loss"],
                         "tp2_5r": params["take_profit"],
                         "h4_bias_override_applied": decision["metrics"].get(
                             "h4_bias_override_applied", False),
                         "m15_classification": decision["metrics"].get(
                             "m15_classification", decision["metrics"].get("classification")),
                         "effective_classification": decision["metrics"].get(
                             "effective_classification", decision["metrics"].get("classification")),
                         "historical_entry_spread": historical_spread,
                         "historical_entry_spread_r": spread_r,
                         **outcome}
                item.update({"status": "EVALUATED", "metrics": decision["metrics"],
                             "setups": [trade]})
            report["symbols"][symbol] = item
    destination = Path(args.output) / args.date
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "session_backtest.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path.resolve()), **report}, indent=2))


if __name__ == "__main__":
    main()
