"""Pure post-reference signal detector for owner-adopted COWORK_SWEEP_V2."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .session_contract import (FrozenSession, M15Bar, SessionType, SweepSide,
                               TrendRangeClassification)


@dataclass(frozen=True)
class CoworkSweepSignal:
    candle_index: int
    candle_time: object
    side: SweepSide
    direction: str
    reference_price: float
    boundary: float
    breach: float
    wick_ratio: float
    confirmation: str
    contract_version: str = "COWORK_SWEEP_V2"
    entry_status: str = "SWEEP_ENTRY_SPEC_BLOCKED"


def detect_cowork_sweeps(
    reference_high: float,
    reference_low: float,
    execution_candles: Sequence[M15Bar],
    pip_size: float,
) -> list[CoworkSweepSignal]:
    """Return every causal confirmed Cowork Sweep in chronological order."""
    high = float(reference_high)
    low = float(reference_low)
    pip = float(pip_size)
    if high <= low or pip <= 0:
        raise ValueError("INVALID_COWORK_SWEEP_INPUT")

    times = [candle.open_time for candle in execution_candles]
    if any(value.tzinfo is None for value in times) or any(
            current <= previous for previous, current in zip(times, times[1:])):
        raise ValueError("INVALID_COWORK_SWEEP_TIMESTAMPS")

    signals: list[CoworkSweepSignal] = []
    for index, candle in enumerate(execution_candles):
        o, h, l, c = map(float, (candle.open, candle.high, candle.low, candle.close))
        if min(o, h, l, c) <= 0 or h < max(o, c) or l > min(o, c) or l > h:
            raise ValueError("INVALID_COWORK_SWEEP_CANDLE")
        candle_range = h - l

        high_breach = h - high
        short_body_confirmation = c < o
        upper_wick_ratio = 0.0 if candle_range == 0 else (h - max(o, c)) / candle_range
        high_clears_one_pip = high_breach > pip or math.isclose(
            high_breach, pip, rel_tol=1e-9, abs_tol=pip * 1e-9)
        if o < high and high_clears_one_pip and c < high and (
                upper_wick_ratio > 0.35 or short_body_confirmation):
            signals.append(CoworkSweepSignal(
                index, candle.open_time, SweepSide.HIGH, "SHORT", max(o, c), high,
                high_breach, upper_wick_ratio,
                "REVERSAL_BODY" if short_body_confirmation else "WICK_RATIO",
            ))

        low_breach = low - l
        long_body_confirmation = c > o
        lower_wick_ratio = 0.0 if candle_range == 0 else (min(o, c) - l) / candle_range
        low_clears_one_pip = low_breach > pip or math.isclose(
            low_breach, pip, rel_tol=1e-9, abs_tol=pip * 1e-9)
        if o > low and low_clears_one_pip and c > low and (
                lower_wick_ratio > 0.35 or long_body_confirmation):
            signals.append(CoworkSweepSignal(
                index, candle.open_time, SweepSide.LOW, "LONG", min(o, c), low,
                low_breach, lower_wick_ratio,
                "REVERSAL_BODY" if long_body_confirmation else "WICK_RATIO",
            ))
    return signals


def detect_range_session_sweeps(
    session: FrozenSession,
    classification: TrendRangeClassification,
    execution_candles: Sequence[M15Bar],
    pip_size: float,
) -> list[CoworkSweepSignal]:
    """Run Cowork Sweep only after the frozen session is classified RANGE."""
    if session.status != "VALID_FROZEN_SESSION":
        raise ValueError("INVALID_SESSION_DATA")
    if classification.classifier_id != "ER_ONLY_V2" or classification.status != "VALIDATED":
        raise ValueError("INVALID_CLASSIFIER_CONTRACT")
    if (classification.session_start, classification.session_end) != \
            (session.start, session.end):
        raise ValueError("CLASSIFIER_SESSION_MISMATCH")
    if classification.session_type is not SessionType.RANGE:
        raise ValueError("SWEEP_DETECTION_REQUIRES_RANGE_SESSION")
    return detect_cowork_sweeps(
        session.box_top, session.box_bottom, execution_candles, pip_size)
