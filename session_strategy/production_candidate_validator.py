"""Pure read-only validator for the strict SSPF production-candidate contract."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any


def _empty_trade(max_hold: str) -> dict:
    return {"action": None, "entry_price": None, "stop_loss": None,
            "take_profit": None, "risk_reward_ratio": "1:5", "risk_pips": None,
            "max_hold_timestamp": max_hold + " UTC"}


def _response(payload, timestamp, status, reason, metrics, trade, gates) -> dict:
    return {"strategy_id": "SSPF_V2_3_PRODUCTION_CANDIDATE",
            "mode": "READ_ONLY_PRODUCTION_CANDIDATE",
            "symbol": str(payload.get("symbol", "")), "timestamp": timestamp,
            "status": status, "rejection_reason": reason, "metrics": metrics,
            "trade_parameters": trade, "gates": gates, "execution_authorized": False}


def validate(payload: dict[str, Any], root_config: dict[str, Any]) -> dict[str, Any]:
    cfg = root_config["production_candidate"]
    timestamp, gates = str(payload.get("current_time", "")), []
    max_hold = str(cfg["maximum_hold_utc"])
    metrics = {"asian_range_pips": None, "atr_14d_pips": None,
               "dynamic_min_pips": None, "dynamic_max_pips": None,
               "efficiency_ratio": None, "classification": None,
               "rejection_wick_ratio": None, "selected_canonical_setup": None}
    try:
        symbol = str(payload["symbol"])
        bounds = cfg["dynamic_bounds"][symbol]
        asian_high = float(payload["asian_session"]["high"])
        asian_low = float(payload["asian_session"]["low"])
        market = payload["ohlcv_data"]
        atr_14d, spread = float(market["atr_14d"]), float(market["spread"])
        pip_size, m15 = float(market.get("pip_size", 1.0)), list(market["m15"])
        now = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _response(payload, timestamp, "SIGNAL_REJECTED", "INVALID_INPUT_SCHEMA",
                         metrics, _empty_trade(max_hold), gates)
    if asian_high <= asian_low or atr_14d <= 0 or spread < 0 or pip_size <= 0 or not m15:
        return _response(payload, timestamp, "SIGNAL_REJECTED", "INVALID_INPUT_VALUES",
                         metrics, _empty_trade(max_hold), gates)
    session_range = asian_high - asian_low
    dynamic_min = float(bounds["minimum_atr_multiplier"]) * atr_14d
    dynamic_max = float(bounds["maximum_atr_multiplier"]) * atr_14d
    metrics.update({"asian_range_pips": session_range / pip_size,
                    "atr_14d_pips": atr_14d / pip_size,
                    "dynamic_min_pips": dynamic_min / pip_size,
                    "dynamic_max_pips": dynamic_max / pip_size})
    if session_range < dynamic_min:
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G4_FAIL_COMPRESSION_VOLATILITY", metrics,
                         _empty_trade(max_hold), gates + [{"name": "G4_DYNAMIC_FLOOR", "passed": False}])
    gates.append({"name": "G4_DYNAMIC_FLOOR", "passed": True})
    if session_range > dynamic_max:
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G5_FAIL_OVER_EXPANSION", metrics,
                         _empty_trade(max_hold), gates + [{"name": "G5_DYNAMIC_CEILING", "passed": False}])
    gates.append({"name": "G5_DYNAMIC_CEILING", "passed": True})
    start, end = (time.fromisoformat(x) for x in cfg["execution_window_utc"])
    if not start <= now.time().replace(tzinfo=None) < end:
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G1_FAIL_OUTSIDE_EXECUTION_WINDOW", metrics,
                         _empty_trade(max_hold), gates)
    first_open, last = float(m15[0]["open"]), m15[-1]
    candle_open, candle_close = float(last["open"]), float(last["close"])
    candle_high, candle_low = float(last["high"]), float(last["low"])
    efficiency = abs(candle_close - first_open) / session_range
    threshold = float(cfg["efficiency_trend_threshold"])
    if efficiency > threshold and candle_high > asian_high and candle_close > asian_high:
        classification = "BULLISH_TREND"
    elif efficiency > threshold and candle_low < asian_low and candle_close < asian_low:
        classification = "BEARISH_TREND"
    elif asian_low <= candle_close <= asian_high and efficiency <= threshold:
        classification = "RANGE"
    else:
        classification = "UNCERTAIN"
    metrics.update({"efficiency_ratio": efficiency, "classification": classification})
    if classification == "UNCERTAIN":
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G3_FAIL_CLASSIFICATION_UNCERTAIN", metrics,
                         _empty_trade(max_hold), gates)
    asset_filter = cfg.get("asset_filters", {}).get(symbol)
    if asset_filter and efficiency < float(asset_filter["minimum_efficiency_ratio"]):
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         str(asset_filter["rejection_reason"]), metrics,
                         _empty_trade(max_hold), gates)
    candidates, directions = [], {}
    candle_range = candle_high - candle_low
    long_sweep = candle_low < asian_low and candle_close > asian_low
    short_sweep = candle_high > asian_high and candle_close < asian_high
    if long_sweep or short_sweep:
        if candle_range <= 0:
            wick_ratio = 0.0
        elif long_sweep:
            wick_ratio = (min(candle_open, candle_close) - candle_low) / candle_range
        else:
            wick_ratio = (candle_high - max(candle_open, candle_close)) / candle_range
        metrics["rejection_wick_ratio"] = wick_ratio
        if wick_ratio < float(cfg["minimum_rejection_wick_ratio"]):
            return _response(payload, timestamp, "SIGNAL_REJECTED",
                             "GATE_G6_FAIL_LOW_WICK_QUALITY_RATIO", metrics,
                             _empty_trade(max_hold), gates)
        candidates.append("SWEEP")
        directions["SWEEP"] = "LONG" if long_sweep else "SHORT"
    midpoint = asian_low + 0.5 * session_range
    fib_382, fib_618 = asian_low + 0.382 * session_range, asian_low + 0.618 * session_range
    shallow = efficiency > float(cfg["shallow_retrace_efficiency_threshold"])
    if classification == "BULLISH_TREND" and candle_close > candle_open:
        if candle_low <= midpoint <= candle_high or shallow and (
                candle_low <= fib_618 <= candle_high or candle_low <= asian_high <= candle_high):
            candidates.append("TREND_CONTINUATION"); directions["TREND_CONTINUATION"] = "LONG"
    elif classification == "BEARISH_TREND" and candle_close < candle_open:
        if candle_low <= midpoint <= candle_high or shallow and (
                candle_low <= fib_382 <= candle_high or candle_low <= asian_low <= candle_high):
            candidates.append("TREND_CONTINUATION"); directions["TREND_CONTINUATION"] = "SHORT"
    if classification == "RANGE":
        if candle_low <= asian_low and candle_close > asian_low and candle_close > candle_open:
            candidates.append("RANGE_REJECTION"); directions["RANGE_REJECTION"] = "LONG"
        elif candle_high >= asian_high and candle_close < asian_high and candle_close < candle_open:
            candidates.append("RANGE_REJECTION"); directions["RANGE_REJECTION"] = "SHORT"
    selected = next((name for name in cfg["setup_priority"] if name in candidates), None)
    metrics.update({"selected_canonical_setup": selected, "qualifying_candidates": candidates})
    if selected is None:
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_PATTERN_FAIL_NO_CANONICAL_SETUP", metrics,
                         _empty_trade(max_hold), gates)
    direction = directions[selected]
    buffer = max(float(cfg["stop_buffer"]["spread_multiplier"]) * spread,
                 float(cfg["stop_buffer"]["daily_atr_fraction"]) * atr_14d)
    extreme = candle_low if direction == "LONG" else candle_high
    stop = extreme - buffer if direction == "LONG" else extreme + buffer
    risk = candle_close - stop if direction == "LONG" else stop - candle_close
    if risk <= 0:
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "FIXED_STOP_NOT_BEYOND_SWEEP", metrics,
                         _empty_trade(max_hold), gates)
    target = candle_close + 5 * risk if direction == "LONG" else candle_close - 5 * risk
    trade = {"action": "BUY_MARKET" if direction == "LONG" else "SELL_MARKET",
             "entry_price": candle_close, "stop_loss": stop, "take_profit": target,
             "risk_reward_ratio": "1:5", "risk_pips": risk / pip_size,
             "max_hold_timestamp": max_hold + " UTC"}
    return _response(payload, timestamp, "SIGNAL_ACCEPTED", None, metrics, trade, gates)
