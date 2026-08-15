"""Historical-only Episode 18 comparison model.

This module deliberately does not integrate with the live analysis CLI.  Source
rules, deterministic interpretations, and unresolved terms are recorded in
config/source_v1.yaml.  It never submits or modifies an MT5 order.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Iterable

from .models import Candle


@dataclass
class SourceTrade:
    setup: str
    direction: str
    signal_time: str
    entry: float
    stop_loss: float
    target_4r: float
    target_5r: float
    outcome_r: float | None = None
    outcome_label: str = "UNRESOLVED"
    runner_note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def levels(candles: list[Candle]) -> dict:
    high, low = max(c.high for c in candles), min(c.low for c in candles)
    rng = high - low
    opened, closed = candles[0].open, candles[-1].close
    return {"high": high, "low": low, "range": rng, "midpoint": (high + low) / 2,
            "open": opened, "close": closed,
            "efficiency_ratio": abs(closed - opened) / rng if rng else 0.0,
            "close_location": (closed - low) / rng if rng else 0.0}


def classify(lv: dict, er_threshold: float = .35, close_location: float = .65) -> str:
    """Inherited deterministic proxy; this is interpretation, not a source rule."""
    if lv["efficiency_ratio"] <= er_threshold:
        return "RANGE"
    if lv["close_location"] >= close_location and lv["close"] > lv["open"]:
        return "BULLISH_TREND"
    if lv["close_location"] <= 1 - close_location and lv["close"] < lv["open"]:
        return "BEARISH_TREND"
    return "UNCERTAIN"


def _trade(setup: str, direction: str, candle: Candle, entry: float, risk: float) -> SourceTrade:
    sign = 1 if direction == "LONG" else -1
    return SourceTrade(setup, direction, candle.time.isoformat().replace("+00:00", "Z"),
                       entry, entry - sign * risk, entry + sign * 4 * risk,
                       entry + sign * 5 * risk)


def detect(session_type: str, lv: dict, candles: list[Candle]) -> SourceTrade | None:
    """First qualifying source setup; exact execution choices are documented proxies."""
    risk = .25 * lv["range"]
    if not risk:
        return None
    for candle in candles:
        if session_type == "RANGE":
            # A take and close back inside is the reproducible sweep proxy. Entry
            # at close represents the otherwise-unspecified "sweep candle body".
            if candle.low < lv["low"] and candle.close > lv["low"]:
                return _trade("SWEEP", "LONG", candle, candle.close, risk)
            if candle.high > lv["high"] and candle.close < lv["high"]:
                return _trade("SWEEP", "SHORT", candle, candle.close, risk)
            # Literal boundary price, with no rejection-strength requirement.
            if candle.low <= lv["low"] <= candle.high:
                return _trade("RANGE", "LONG", candle, lv["low"], risk)
            if candle.low <= lv["high"] <= candle.high:
                return _trade("RANGE", "SHORT", candle, lv["high"], risk)
        elif session_type == "BULLISH_TREND":
            lower_quartile = lv["low"] + .25 * lv["range"]
            touched_zone = (candle.low <= lv["low"] + .55 * lv["range"] and
                            candle.high >= lv["low"] + .45 * lv["range"])
            if candle.low < lower_quartile:
                return None
            if touched_zone and candle.close > candle.open:
                return _trade("TREND", "LONG", candle, lv["midpoint"], risk)
        elif session_type == "BEARISH_TREND":
            upper_quartile = lv["high"] - .25 * lv["range"]
            touched_zone = (candle.low <= lv["low"] + .55 * lv["range"] and
                            candle.high >= lv["low"] + .45 * lv["range"])
            if candle.high > upper_quartile:
                return None
            if touched_zone and candle.close < candle.open:
                return _trade("TREND", "SHORT", candle, lv["midpoint"], risk)
    return None


def realize(trade: SourceTrade, candles: Iterable[Candle]) -> SourceTrade:
    """Replay with STOP_FIRST ordering; trend runner remains source-ambiguous."""
    sign = 1 if trade.direction == "LONG" else -1
    partial = False
    for candle in candles:
        stop_hit = candle.low <= trade.stop_loss if sign == 1 else candle.high >= trade.stop_loss
        four_hit = candle.high >= trade.target_4r if sign == 1 else candle.low <= trade.target_4r
        five_hit = candle.high >= trade.target_5r if sign == 1 else candle.low <= trade.target_5r
        if not partial and stop_hit:
            trade.outcome_r, trade.outcome_label = -1.0, "STOP"
            return trade
        if not partial and four_hit:
            partial = True
            trade.stop_loss = trade.entry
        if partial:
            be_hit = candle.low <= trade.entry if sign == 1 else candle.high >= trade.entry
            if be_hit:
                trade.outcome_r, trade.outcome_label = 3.0, "4R_PARTIAL_THEN_BE"
                return trade
            if five_hit:
                trade.outcome_r, trade.outcome_label = 4.25, "5R_TARGET"
                return trade
    if not partial:
        trade.outcome_label = "OPEN_AT_REPLAY_END"
    return trade
