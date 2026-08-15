"""Research-only no-trade diagnostics; never imported by the production engine."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import floor

from .models import Candle


@dataclass(frozen=True)
class VolumeProfile:
    val: float
    vpoc: float
    vah: float
    value_area_fraction: float
    bins: int
    volume_source: str = "M15_TICK_VOLUME_PROXY"

    def to_dict(self) -> dict:
        return asdict(self)


def session_volume_profile(candles: list[Candle], bins: int = 40,
                           value_area_fraction: float = 0.70) -> VolumeProfile:
    """Approximate a profile by distributing each bar's tick volume across crossed bins.

    M15 OHLC has no price-by-price traded volume, so this is a documented proxy, not an
    institutional order-flow measurement or an ML prediction.
    """
    if not candles or bins < 2 or not 0 < value_area_fraction <= 1:
        raise ValueError("valid candles, at least two bins, and a value area in (0, 1] are required")
    low, high = min(c.low for c in candles), max(c.high for c in candles)
    if high <= low:
        raise ValueError("session range must be positive")
    width = (high - low) / bins
    volumes = [0.0] * bins
    for candle in candles:
        first = max(0, min(bins - 1, floor((candle.low - low) / width)))
        last = max(0, min(bins - 1, floor((candle.high - low) / width)))
        crossed = last - first + 1
        allocation = max(float(candle.tick_volume), 0.0) / crossed
        for index in range(first, last + 1):
            volumes[index] += allocation
    total = sum(volumes)
    if total <= 0:
        raise ValueError("session tick volume must be positive")
    vpoc_index = max(range(bins), key=lambda i: volumes[i])
    ranked = sorted(range(bins), key=lambda i: (-volumes[i], abs(i - vpoc_index), i))
    selected, accumulated = set(), 0.0
    for index in ranked:
        selected.add(index)
        accumulated += volumes[index]
        if accumulated >= total * value_area_fraction:
            break
    center = lambda index: low + (index + 0.5) * width
    return VolumeProfile(center(min(selected)), center(vpoc_index), center(max(selected)),
                         value_area_fraction, bins)


def atr(candles: list[Candle], period: int = 14) -> float:
    if period <= 0 or len(candles) < period + 1:
        raise ValueError("ATR requires period + 1 candles")
    true_ranges = []
    for previous, current in zip(candles, candles[1:]):
        true_ranges.append(max(current.high - current.low,
                               abs(current.high - previous.close),
                               abs(current.low - previous.close)))
    return sum(true_ranges[-period:]) / period


def dynamic_stop(entry: float, sweep_extreme: float, direction: str, atr_value: float,
                 multiplier: float, spread_ceiling: float) -> tuple[float, float]:
    if atr_value < 0 or multiplier < 0 or spread_ceiling < 0:
        raise ValueError("ATR, multiplier, and spread must be non-negative")
    buffer = multiplier * atr_value + spread_ceiling
    stop = sweep_extreme - buffer if direction == "LONG" else sweep_extreme + buffer
    return stop, abs(entry - stop)
