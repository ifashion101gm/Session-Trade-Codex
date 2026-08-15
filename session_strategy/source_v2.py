"""User-resolved SOURCE_V2 research primitives; historical and read-only."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import Candle


LONDON = ZoneInfo("Europe/London")


def source_v2_bounds(day: date) -> tuple[datetime, datetime, datetime]:
    """London-local [00:00,08:00) Asian range and [08:00,10:00) entry window."""
    local_start = datetime.combine(day, time(0), LONDON)
    local_lock = datetime.combine(day, time(8), LONDON)
    local_end = datetime.combine(day, time(10), LONDON)
    return tuple(x.astimezone(timezone.utc) for x in (local_start, local_lock, local_end))


def source_v2_agent_bounds(day: date) -> tuple[datetime, datetime, datetime]:
    """Agent contract: [00:00,08:00) range, signals through the 09:30 close."""
    local_start = datetime.combine(day, time(0), LONDON)
    local_lock = datetime.combine(day, time(8), LONDON)
    local_expiry = datetime.combine(day, time(9, 30), LONDON)
    return tuple(x.astimezone(timezone.utc) for x in (local_start, local_lock, local_expiry))


def fractal_pivots(candles: list[Candle]) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Return confirmed three-candle swing highs and lows (confirmed by i+1 close)."""
    highs, lows = [], []
    for i in range(1, len(candles) - 1):
        if candles[i - 1].high < candles[i].high > candles[i + 1].high:
            highs.append((i, candles[i].high))
        if candles[i - 1].low > candles[i].low < candles[i + 1].low:
            lows.append((i, candles[i].low))
    return highs, lows


def h1_structure(candles: list[Candle], tolerance: float) -> str:
    """HH+HL bullish, LH+LL bearish; mixed/equal/insufficient is uncertain."""
    highs, lows = fractal_pivots(candles[-48:])
    if len(highs) < 2 or len(lows) < 2:
        return "UNCERTAIN"
    h1, h2 = highs[-2][1], highs[-1][1]
    l1, l2 = lows[-2][1], lows[-1][1]
    if abs(h2 - h1) <= tolerance or abs(l2 - l1) <= tolerance:
        return "UNCERTAIN"
    if h2 > h1 and l2 > l1:
        return "BULLISH"
    if h2 < h1 and l2 < l1:
        return "BEARISH"
    return "UNCERTAIN"


def combined_bias(session: list[Candle], structure: str) -> str:
    direction = "BULLISH" if session[-1].close > session[0].open else (
        "BEARISH" if session[-1].close < session[0].open else "UNCERTAIN")
    return direction if direction == structure else "UNCERTAIN"


def range_or_trend(session: list[Candle]) -> str:
    high, low = max(c.high for c in session), min(c.low for c in session)
    return "RANGE" if abs(session[-1].close - session[0].open) <= .5 * (high - low) else "TREND"


def ratchet_trailing_stop(direction: str, current_stop: float,
                          completed: list[Candle]) -> float:
    highs, lows = fractal_pivots(completed)
    if direction == "LONG" and lows:
        return max(current_stop, lows[-1][1])
    if direction == "SHORT" and highs:
        return min(current_stop, highs[-1][1])
    return current_stop
