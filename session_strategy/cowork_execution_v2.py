"""Pure M1 Bid/Ask fill primitives for COWORK_SWEEP_EXECUTION_V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class M1BidAskBar:
    open_time: datetime
    bid_open: float
    bid_high: float
    bid_low: float
    ask_open: float
    ask_high: float
    ask_low: float


def order_active_for_bar(signal_end: datetime, expiry: datetime,
                         bar: M1BidAskBar) -> bool:
    """An order exists only after signal completion and strictly before expiry."""
    return signal_end <= bar.open_time < expiry


def limit_entry_fill(direction: str, limit: float, bar: M1BidAskBar) -> float | None:
    """Return a causal limit fill, including opening price improvement."""
    if direction == "LONG":
        if bar.ask_open <= limit:
            return bar.ask_open
        return limit if bar.ask_low <= limit else None
    if direction == "SHORT":
        if bar.bid_open >= limit:
            return bar.bid_open
        return limit if bar.bid_high >= limit else None
    raise ValueError("INVALID_DIRECTION")


def stop_exit_fill(direction: str, stop: float, bar: M1BidAskBar) -> float | None:
    """Return stop-market fill; opening gaps may be adverse."""
    if direction == "LONG":
        if bar.bid_open <= stop:
            return bar.bid_open
        return stop if bar.bid_low <= stop else None
    if direction == "SHORT":
        if bar.ask_open >= stop:
            return bar.ask_open
        return stop if bar.ask_high >= stop else None
    raise ValueError("INVALID_DIRECTION")


def target_exit_fill(direction: str, target: float, bar: M1BidAskBar) -> float | None:
    """Return target-limit fill; opening gaps may improve price."""
    if direction == "LONG":
        if bar.bid_open >= target:
            return bar.bid_open
        return target if bar.bid_high >= target else None
    if direction == "SHORT":
        if bar.ask_open <= target:
            return bar.ask_open
        return target if bar.ask_low <= target else None
    raise ValueError("INVALID_DIRECTION")


def protective_exit_stop_first(
    direction: str, stop: float, target: float, bar: M1BidAskBar,
) -> tuple[str, float] | None:
    """Resolve ambiguous one-bar protective exits conservatively."""
    stop_fill = stop_exit_fill(direction, stop, bar)
    if stop_fill is not None:
        return "STOP", stop_fill
    target_fill = target_exit_fill(direction, target, bar)
    return None if target_fill is None else ("TARGET", target_fill)
