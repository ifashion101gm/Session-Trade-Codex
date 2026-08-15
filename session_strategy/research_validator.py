"""Deterministic SSPF v2.3 research validator with no execution capability."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any


def _rejected(payload: dict, timestamp: str, reason: str, metrics: dict) -> dict:
    return {
        "strategy_id": "SSPF_V2_3_RESEARCH",
        "mode": "READ_ONLY_RESEARCH",
        "symbol": str(payload.get("symbol", "")),
        "timestamp": timestamp,
        "status": "SIGNAL_REJECTED",
        "rejection_reason": reason,
        "metrics": metrics,
        "trade_parameters": {
            "action": None, "entry_price": None, "stop_loss": None,
            "take_profit": None, "risk_reward_ratio": "1:5", "risk_pips": None,
        },
        "execution_authorized": False,
    }


def validate(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Validate one caller-supplied snapshot and return proposal JSON only."""
    required = ("symbol", "asian_session", "ohlcv_data", "dom_data", "current_time")
    missing = [key for key in required if key not in payload]
    timestamp = str(payload.get("current_time", ""))
    empty_metrics = {
        "asian_range_pips": None, "atr_14d_pips": None,
        "dynamic_min_pips": None, "dynamic_max_pips": None,
        "limit_order_density": None, "delta_absorption": False,
    }
    if missing:
        return _rejected(payload, timestamp, "INVALID_INPUT_MISSING_" + "_".join(missing),
                         empty_metrics)
    try:
        now = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        asian = payload["asian_session"]
        high, low = float(asian["high"]), float(asian["low"])
        atr_14d = float(payload["ohlcv_data"]["atr_14d"])
        pip_size = float(payload["ohlcv_data"].get("pip_size", 1.0))
        entry = float(payload["ohlcv_data"]["signal_candle"]["close"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return _rejected(payload, timestamp, "INVALID_INPUT_SCHEMA", empty_metrics)
    if high <= low or atr_14d <= 0 or pip_size <= 0:
        return _rejected(payload, timestamp, "INVALID_INPUT_NON_POSITIVE_RANGE_ATR_OR_PIP",
                         empty_metrics)
    bounds = config["atr_range_bounds"]
    session_range = high - low
    dynamic_min = float(bounds["minimum_multiplier"]) * atr_14d
    dynamic_max = float(bounds["maximum_multiplier"]) * atr_14d
    dom = payload.get("dom_data") or {}
    resting = dom.get("resting_limit_volume_at_sweep")
    average = dom.get("average_20_level_depth")
    lod = (float(resting) / float(average)
           if resting is not None and average is not None and float(average) > 0 else None)
    cvd = dom.get("cvd_reversal") is True
    metrics = {
        "asian_range_pips": session_range / pip_size,
        "atr_14d_pips": atr_14d / pip_size,
        "dynamic_min_pips": dynamic_min / pip_size,
        "dynamic_max_pips": dynamic_max / pip_size,
        "limit_order_density": lod,
        "delta_absorption": cvd,
    }
    if session_range < dynamic_min:
        return _rejected(payload, timestamp, "GATE_G4_FAIL_COMPRESSION_VOLATILITY", metrics)
    if session_range > dynamic_max:
        return _rejected(payload, timestamp, "GATE_G5_FAIL_OVER_EXPANSION", metrics)
    if not time(8, 0) <= now.time().replace(tzinfo=None) < time(11, 0):
        return _rejected(payload, timestamp, "GATE_G1_FAIL_OUTSIDE_EXECUTION_WINDOW", metrics)
    candle = payload["ohlcv_data"]["signal_candle"]
    candle_high, candle_low = float(candle["high"]), float(candle["low"])
    setup = str(payload["ohlcv_data"].get("setup", "SWEEP")).upper()
    direction = str(payload["ohlcv_data"].get("direction", "")).upper()
    if setup == "SWEEP":
        valid_long = direction == "LONG" and candle_low < low and entry > low
        valid_short = direction == "SHORT" and candle_high > high and entry < high
        if not (valid_long or valid_short):
            return _rejected(payload, timestamp, "GATE_PATTERN_FAIL_SWEEP_CONFIRMATION", metrics)
        dom_cfg = config["dom_gate"]
        if lod is None:
            return _rejected(payload, timestamp, "GATE_G6_FAIL_DOM_DATA_MISSING", metrics)
        if lod < float(dom_cfg["minimum_limit_order_density"]) or not cvd:
            return _rejected(payload, timestamp,
                             "GATE_G6_FAIL_DOM_LIQUIDITY_INSUFFICIENT", metrics)
    elif setup not in {"TREND_CONTINUATION", "RANGE_REJECTION"}:
        return _rejected(payload, timestamp, "GATE_PATTERN_FAIL_UNSUPPORTED_SETUP", metrics)
    spread_buffer = float(payload["ohlcv_data"].get("spread_buffer", 0.0))
    if spread_buffer < 0 or direction not in {"LONG", "SHORT"}:
        return _rejected(payload, timestamp, "INVALID_ORDER_GEOMETRY", metrics)
    extreme = candle_low if direction == "LONG" else candle_high
    stop = extreme - spread_buffer if direction == "LONG" else extreme + spread_buffer
    risk = entry - stop if direction == "LONG" else stop - entry
    if risk <= 0:
        return _rejected(payload, timestamp, "FIXED_STOP_NOT_BEYOND_SWEEP", metrics)
    target = entry + 5 * risk if direction == "LONG" else entry - 5 * risk
    result = _rejected(payload, timestamp, "", metrics)
    result.update({"status": "SIGNAL_ACCEPTED", "rejection_reason": None,
                   "setup": setup, "trade_parameters": {
                       "action": "BUY_MARKET" if direction == "LONG" else "SELL_MARKET",
                       "entry_price": entry, "stop_loss": stop, "take_profit": target,
                       "risk_reward_ratio": "1:5", "risk_pips": risk / pip_size,
                   }})
    return result
