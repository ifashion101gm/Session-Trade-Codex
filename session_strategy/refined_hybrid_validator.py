"""Pure, read-only validator for the refined hybrid research contract."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any


def _empty_trade(max_hold: str) -> dict:
    return {"action": None, "entry_price": None, "stop_loss": None,
            "take_profit": None, "risk_reward_ratio": "1:5", "risk_pips": None,
            "max_hold_timestamp": max_hold + " UTC"}


def _response(payload, timestamp, status, reason, metrics, trade, gates) -> dict:
    return {"strategy_id": "SSPF_V2_3_REFINED_RESEARCH", "mode": "READ_ONLY_RESEARCH",
            "symbol": str(payload.get("symbol", "")), "timestamp": timestamp,
            "status": status, "rejection_reason": reason, "metrics": metrics,
            "trade_parameters": trade, "gates": gates, "execution_authorized": False}


def _h4_bias(bars: list[dict]) -> str:
    if len(bars) < 3:
        return "NEUTRAL"
    recent = bars[-3:]
    highs, lows = [float(x["high"]) for x in recent], [float(x["low"]) for x in recent]
    if highs[0] < highs[1] < highs[2] and lows[0] < lows[1] < lows[2]:
        return "BULLISH"
    if highs[0] > highs[1] > highs[2] and lows[0] > lows[1] > lows[2]:
        return "BEARISH"
    return "NEUTRAL"


def validate(payload: dict[str, Any], root_config: dict[str, Any]) -> dict[str, Any]:
    cfg = root_config["refined_hybrid"]
    timestamp = str(payload.get("current_time", ""))
    max_hold = str(cfg["maximum_hold_utc"])
    metrics = {"asian_range_pips": None, "atr_14d_pips": None,
               "dynamic_min_pips": None, "dynamic_max_pips": None,
               "efficiency_ratio": None, "m15_classification": None,
               "h4_bias": None, "h4_bias_override_applied": False,
               "selected_canonical_setup": None}
    gates = []
    try:
        symbol = str(payload["symbol"])
        bounds = cfg["dynamic_bounds"][symbol]
        asian = payload["asian_session"]
        asian_high, asian_low = float(asian["high"]), float(asian["low"])
        market = payload["ohlcv_data"]
        atr_14d, spread = float(market["atr_14d"]), float(market["spread"])
        pip_size = float(market.get("pip_size", 1.0))
        m15, h4 = list(market["m15"]), list(market.get("h4", []))
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
        gates.append({"name": "G4_DYNAMIC_FLOOR", "passed": False})
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G4_FAIL_COMPRESSION_VOLATILITY", metrics,
                         _empty_trade(max_hold), gates)
    gates.append({"name": "G4_DYNAMIC_FLOOR", "passed": True})
    if session_range > dynamic_max:
        gates.append({"name": "G5_DYNAMIC_CEILING", "passed": False})
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G5_FAIL_OVER_EXPANSION", metrics,
                         _empty_trade(max_hold), gates)
    gates.append({"name": "G5_DYNAMIC_CEILING", "passed": True})
    start, end = (time.fromisoformat(x) for x in cfg["execution_window_utc"])
    if not start <= now.time().replace(tzinfo=None) < end:
        gates.append({"name": "EXECUTION_WINDOW", "passed": False})
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_G1_FAIL_OUTSIDE_EXECUTION_WINDOW", metrics,
                         _empty_trade(max_hold), gates)
    gates.append({"name": "EXECUTION_WINDOW", "passed": True})
    first_open, last_close = float(m15[0]["open"]), float(m15[-1]["close"])
    efficiency = abs(last_close - first_open) / session_range
    latest = m15[-1]
    candle_high, candle_low = float(latest["high"]), float(latest["low"])
    candle_open, candle_close = float(latest["open"]), float(latest["close"])
    threshold = float(cfg["efficiency_trend_threshold"])
    if efficiency > threshold and candle_high > asian_high and candle_close > asian_high:
        classification = "BULLISH_TREND"
    elif efficiency > threshold and candle_low < asian_low and candle_close < asian_low:
        classification = "BEARISH_TREND"
    elif asian_low <= candle_close <= asian_high and efficiency <= threshold:
        classification = "RANGE"
    else:
        classification = "UNCERTAIN"
    original = classification
    h4_bias = _h4_bias(h4)
    if classification == "UNCERTAIN" and h4_bias in {"BULLISH", "BEARISH"}:
        classification = h4_bias + "_TREND"
        metrics["h4_bias_override_applied"] = True
    metrics.update({"efficiency_ratio": efficiency, "m15_classification": original,
                    "h4_bias": h4_bias, "effective_classification": classification})
    if classification == "UNCERTAIN":
        gates.append({"name": "CLASSIFICATION", "passed": False})
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_CLASSIFICATION_UNCERTAIN", metrics,
                         _empty_trade(max_hold), gates)
    gates.append({"name": "CLASSIFICATION", "passed": True})
    m5 = list(market.get("m5", []))
    micro_reentry = any(asian_low < float(x["close"]) < asian_high for x in m5[-3:])
    candidates = []
    direction = None
    if candle_low < asian_low and (candle_close > asian_low or micro_reentry):
        candidates.append("SWEEP"); direction = "LONG"
    elif candle_high > asian_high and (candle_close < asian_high or micro_reentry):
        candidates.append("SWEEP"); direction = "SHORT"
    midpoint = asian_low + 0.5 * session_range
    fib_382 = asian_low + 0.382 * session_range
    fib_618 = asian_low + 0.618 * session_range
    touched_mid = candle_low <= midpoint <= candle_high
    shallow = efficiency > float(cfg["shallow_retrace_efficiency_threshold"])
    if classification == "BULLISH_TREND" and candle_close > candle_open:
        touched_shallow_or_boundary = (
            candle_low <= fib_618 <= candle_high
            or candle_low <= asian_high <= candle_high
        )
        if touched_mid or (shallow and touched_shallow_or_boundary):
            candidates.append("TREND_CONTINUATION"); direction = direction or "LONG"
    if classification == "BEARISH_TREND" and candle_close < candle_open:
        touched_shallow_or_boundary = (
            candle_low <= fib_382 <= candle_high
            or candle_low <= asian_low <= candle_high
        )
        if touched_mid or (shallow and touched_shallow_or_boundary):
            candidates.append("TREND_CONTINUATION"); direction = direction or "SHORT"
    if classification == "RANGE":
        if candle_low <= asian_low and candle_close > asian_low and candle_close > candle_open:
            candidates.append("RANGE_REJECTION"); direction = direction or "LONG"
        elif candle_high >= asian_high and candle_close < asian_high and candle_close < candle_open:
            candidates.append("RANGE_REJECTION"); direction = direction or "SHORT"
    selected = next((name for name in cfg["setup_priority"] if name in candidates), None)
    metrics["selected_canonical_setup"] = selected
    metrics["qualifying_candidates"] = candidates
    if selected is None or direction is None:
        gates.append({"name": "PATTERN_TRIGGER", "passed": False})
        return _response(payload, timestamp, "SIGNAL_REJECTED",
                         "GATE_PATTERN_FAIL_NO_CANONICAL_SETUP", metrics,
                         _empty_trade(max_hold), gates)
    gates.append({"name": "PATTERN_TRIGGER", "passed": True})
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
