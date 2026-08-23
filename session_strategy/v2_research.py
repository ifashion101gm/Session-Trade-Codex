"""Pure research components for the attached SESSION STRATEGY V2 contract.

This module deliberately does not promote a regime classifier, bias model, or fill
model to authority. It produces reproducible evidence and explicit unresolved states.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Sequence

from .session_contract import FrozenSession, M15Bar


V2_REFERENCE_LEGS = {
    "ASIAN_REFERENCE": ("ASIAN", time(0), time(7), 28),
    "LONDON_REFERENCE": ("LONDON", time(7), time(12), 20),
}


def freeze_v2_reference_box(reference_session: str, trading_date: date,
                            candles: Sequence[M15Bar], decision_time: datetime) -> FrozenSession:
    """Freeze the attachment's 00:00-07:00 Asian or 07:00-12:00 London box."""
    try:
        name, start_time, end_time, expected = V2_REFERENCE_LEGS[reference_session]
    except KeyError as exc:
        raise ValueError("INVALID_SESSION_DATA: unknown V2 reference session") from exc
    start = datetime.combine(trading_date, start_time, tzinfo=timezone.utc)
    end = datetime.combine(trading_date, end_time, tzinfo=timezone.utc)
    if decision_time.tzinfo is None or decision_time.astimezone(timezone.utc) < end:
        raise ValueError("INVALID_SESSION_DATA: reference box is incomplete")
    expected_opens = [start + timedelta(minutes=15 * index) for index in range(expected)]
    actual_opens = [bar.open_time.astimezone(timezone.utc) for bar in candles]
    if actual_opens != expected_opens:
        raise ValueError(f"INVALID_SESSION_DATA: {reference_session} requires {expected} M15 candles")
    if any(bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close)
           or bar.low > bar.high for bar in candles):
        raise ValueError("INVALID_SESSION_DATA: invalid M15 OHLC")
    if not candles:
        raise ValueError("INVALID_SESSION_DATA: empty reference box")
    high = max(bar.high for bar in candles)
    low = min(bar.low for bar in candles)
    return FrozenSession(
        reference_session, trading_date, start, end, tuple(candles), high, low,
        (high + low) / 2.0, candles[0].open, candles[-1].close,
    )


@dataclass(frozen=True)
class ReferenceBoxFeatures:
    first_open: float
    final_close: float
    high: float
    low: float
    range: float
    midpoint: float
    candle_count: int
    start_timestamp: object
    end_timestamp: object
    efficiency_ratio: float
    open_close_displacement: float
    absolute_displacement: float
    normalized_displacement: float
    close_location: float
    open_location: float
    open_side_midpoint: str
    close_side_midpoint: str
    midpoint_crossing_count: int
    candles_above_midpoint: int
    candles_below_midpoint: int
    bullish_candle_count: int
    bearish_candle_count: int
    higher_close_count: int
    lower_close_count: int
    directional_close_ratio: float
    path_length: float
    mean_body_to_range: float
    first_half_displacement: float
    second_half_displacement: float
    final_quarter_displacement: float
    final_quarter_slope: float
    final_quarter_higher_close_count: int
    final_quarter_lower_close_count: int
    high_index: int
    low_index: int
    high_timing_normalized: float
    low_timing_normalized: float
    maximum_favorable_excursion: float
    maximum_adverse_excursion: float

    def serializable(self) -> dict:
        return asdict(self)


def _side(value: float, midpoint: float) -> str:
    if value > midpoint:
        return "ABOVE"
    if value < midpoint:
        return "BELOW"
    return "AT"


def extract_reference_features(session: FrozenSession) -> ReferenceBoxFeatures:
    """Extract deterministic features from the frozen reference candles only."""
    candles = session.candles
    if not candles or session.status != "VALID_FROZEN_SESSION":
        raise ValueError("INVALID_SESSION_DATA: valid frozen session required")
    closes = [bar.close for bar in candles]
    midpoint = session.midpoint
    span = session.box_top - session.box_bottom
    path = abs(closes[0] - session.first_open)
    path += sum(abs(current - previous) for previous, current in zip(closes, closes[1:]))
    displacement = session.final_close - session.first_open
    half = max(1, len(candles) // 2)
    quarter = max(1, len(candles) // 4)
    first_half = candles[:half]
    second_half = candles[half:]
    final_quarter = candles[-quarter:]
    directional = sum(current != previous for previous, current in zip(closes, closes[:-1]))
    crossings = sum(
        (a < midpoint < b) or (a > midpoint > b)
        for a, b in zip(closes, closes[1:])
    )
    body_ratios = [
        abs(bar.close - bar.open) / (bar.high - bar.low)
        if bar.high > bar.low else 0.0
        for bar in candles
    ]
    final_closes = [bar.close for bar in final_quarter]
    final_slope = (final_closes[-1] - final_closes[0]) / max(1, len(final_closes) - 1)
    excursions = [bar.close - session.first_open for bar in candles]
    high_index = max(range(len(candles)), key=lambda index: candles[index].high)
    low_index = min(range(len(candles)), key=lambda index: candles[index].low)
    return ReferenceBoxFeatures(
        session.first_open, session.final_close, session.box_top, session.box_bottom,
        span, midpoint, len(candles), session.start, session.end,
        0.0 if path == 0 else abs(displacement) / path,
        displacement, abs(displacement), 0.0 if span == 0 else abs(displacement) / span,
        0.0 if span == 0 else (session.final_close - session.box_bottom) / span,
        0.0 if span == 0 else (session.first_open - session.box_bottom) / span,
        _side(session.first_open, midpoint), _side(session.final_close, midpoint),
        crossings, sum(bar.close > midpoint for bar in candles),
        sum(bar.close < midpoint for bar in candles),
        sum(bar.close > bar.open for bar in candles),
        sum(bar.close < bar.open for bar in candles),
        sum(current > previous for previous, current in zip(closes, closes[1:])),
        sum(current < previous for previous, current in zip(closes, closes[1:])),
        directional / max(1, len(closes) - 1), path, sum(body_ratios) / len(body_ratios),
        first_half[-1].close - first_half[0].open,
        second_half[-1].close - second_half[0].open if second_half else 0.0,
        final_quarter[-1].close - final_quarter[0].open,
        final_slope,
        sum(current > previous for previous, current in zip(final_closes, final_closes[1:])),
        sum(current < previous for previous, current in zip(final_closes, final_closes[1:])),
        high_index, low_index,
        high_index / max(1, len(candles) - 1), low_index / max(1, len(candles) - 1),
        max(excursions), min(excursions),
    )


def er_040_research_candidate(features: ReferenceBoxFeatures) -> str:
    """Retired comparator; never use as authoritative routing."""
    return "TREND" if features.efficiency_ratio >= 0.40 else "RANGE"


def midpoint_side_research_candidate(features: ReferenceBoxFeatures) -> str:
    """Retired comparator; never use as authoritative routing."""
    return "TREND" if features.open_side_midpoint != features.close_side_midpoint else "RANGE"


@dataclass(frozen=True)
class BiasEvidence:
    direction: str | None
    reason_code: str
    previous_high: float | None
    previous_low: float | None
    boundary: str | None
    penetration: float
    accepted: bool | None
    current_box_direction: str | None
    late_direction: str | None


def trend_bias_v1(
    previous_candles: Sequence[M15Bar],
    current: FrozenSession,
) -> BiasEvidence:
    """Research-only structural bias model with explicit unresolved conflicts."""
    if not previous_candles:
        return BiasEvidence(None, "BIAS_INSUFFICIENT_EVIDENCE", None, None, None,
                            0.0, None, None, None)
    previous_high = max(bar.high for bar in previous_candles)
    previous_low = min(bar.low for bar in previous_candles)
    current_direction = (
        "LONG" if current.final_close > current.first_open
        else "SHORT" if current.final_close < current.first_open else None
    )
    late = current.candles[-max(1, len(current.candles) // 4):]
    late_direction = (
        "LONG" if late[-1].close > late[0].open
        else "SHORT" if late[-1].close < late[0].open else None
    )
    high_touch = max(bar.high for bar in current.candles) > previous_high
    low_touch = min(bar.low for bar in current.candles) < previous_low
    if high_touch and low_touch:
        return BiasEvidence(None, "BIAS_STRUCTURAL_CONFLICT", previous_high, previous_low,
                            "BOTH", max(previous_high - previous_low, 0.0), None,
                            current_direction, late_direction)
    if high_touch:
        candle = max(current.candles, key=lambda bar: bar.high)
        if candle.close > previous_high:
            return BiasEvidence("LONG", "BIAS_HIGH_BREAK_ACCEPT_LONG", previous_high,
                                previous_low, "HIGH", candle.high - previous_high, True,
                                current_direction, late_direction)
        return BiasEvidence("SHORT", "BIAS_HIGH_SWEEP_REJECT_SHORT", previous_high,
                            previous_low, "HIGH", candle.high - previous_high, False,
                            current_direction, late_direction)
    if low_touch:
        candle = min(current.candles, key=lambda bar: bar.low)
        if candle.close < previous_low:
            return BiasEvidence("SHORT", "BIAS_LOW_BREAK_ACCEPT_SHORT", previous_high,
                                previous_low, "LOW", previous_low - candle.low, True,
                                current_direction, late_direction)
        return BiasEvidence("LONG", "BIAS_LOW_SWEEP_RECLAIM_LONG", previous_high,
                            previous_low, "LOW", previous_low - candle.low, False,
                            current_direction, late_direction)
    if current_direction and current_direction == late_direction:
        return BiasEvidence(current_direction, f"BIAS_LATE_CONFIRM_{current_direction}",
                            previous_high, previous_low, None, 0.0, None,
                            current_direction, late_direction)
    if current_direction:
        return BiasEvidence(current_direction, f"BIAS_BOX_MOMENTUM_{current_direction}",
                            previous_high, previous_low, None, 0.0, None,
                            current_direction, late_direction)
    return BiasEvidence(None, "BIAS_INSUFFICIENT_EVIDENCE", previous_high, previous_low,
                        None, 0.0, None, current_direction, late_direction)


@dataclass(frozen=True)
class StrictSweepEvidence:
    qualified: bool
    direction: str | None
    candidate_index: int | None
    candidate_timestamp: object | None
    reference_level: float | None
    candidate_open: float | None
    candidate_high: float | None
    candidate_low: float | None
    candidate_close: float | None
    penetration: float | None
    reclaim: float | None
    reason_code: str


def detect_strict_sweep(
    candles: Sequence[M15Bar],
    established_high: float | None = None,
    established_low: float | None = None,
) -> StrictSweepEvidence:
    """Detect a Sweep against an established level, not a running local extreme."""
    if not candles or established_high is None or established_low is None:
        return StrictSweepEvidence(False, None, None, None, None, None, None, None,
                                   None, None, None, "SWEEP_INSUFFICIENT_LEVEL")
    for index, candle in enumerate(candles):
        high = candle.high > established_high and candle.close < established_high
        low = candle.low < established_low and candle.close > established_low
        if high and low:
            return StrictSweepEvidence(False, None, index, candle.open_time, None,
                                       candle.open, candle.high, candle.low, candle.close,
                                       None, None, "SWEEP_DUAL_BOUNDARY_AMBIGUOUS")
        if high:
            return StrictSweepEvidence(True, "SHORT", index, candle.open_time,
                                       established_high, candle.open, candle.high,
                                       candle.low, candle.close, candle.high - established_high,
                                       established_high - candle.close, "SWEEP_HIGH_RECLAIM")
        if low:
            return StrictSweepEvidence(True, "LONG", index, candle.open_time,
                                       established_low, candle.open, candle.high,
                                       candle.low, candle.close, established_low - candle.low,
                                       candle.close - established_low, "SWEEP_LOW_RECLAIM")
    return StrictSweepEvidence(False, None, None, None, None, None, None, None,
                               None, None, None, "SWEEP_NONE")


@dataclass(frozen=True)
class TradeIntent:
    strategy_version: str
    reference_session: str
    reference_start: object
    reference_end: object
    reference_high: float
    reference_low: float
    reference_mid: float
    reference_range: float
    regime: str
    regime_reason: str
    regime_status: str
    setup: str | None
    bias: str | None
    bias_reason: str
    entry_type: str | None
    entry_reference: float | None
    risk_distance: float | None
    stop_loss: float | None
    tp1: float | None
    tp1_r: float
    tp1_close_pct: float
    tp2: float | None
    tp2_r: float
    remaining_pct: float
    signal_timestamp: object | None
    fill_status: str
    execution_status: str
    research_flags: tuple[str, ...]
    reason_codes: tuple[str, ...]


def build_risk_geometry(entry: float, direction: str, reference_range: float) -> tuple[float, float, float]:
    """Return fixed 25% risk, 4R, and 5R prices without fill assumptions."""
    risk = reference_range * 0.25
    sign = 1 if direction == "LONG" else -1
    return entry - sign * risk, entry + sign * 4 * risk, entry + sign * 5 * risk


def route_v2_research(
    session: FrozenSession,
    regime_classifier: Callable[[ReferenceBoxFeatures], str] | None = None,
    previous_candles: Sequence[M15Bar] = (),
    established_high: float | None = None,
    established_low: float | None = None,
) -> TradeIntent:
    """Build one explicit intent or fail closed while the regime contract is open."""
    features = extract_reference_features(session)
    if regime_classifier is None:
        return _unresolved_intent(session, "REGIME_CLASSIFIER_UNRESOLVED")
    regime = regime_classifier(features)
    if regime not in {"TREND", "RANGE"}:
        return _unresolved_intent(session, "REGIME_CLASSIFIER_INVALID")
    if regime == "TREND":
        bias = trend_bias_v1(previous_candles, session)
        if bias.direction is None:
            return _unresolved_intent(session, bias.reason_code, regime, bias.reason_code)
        entry = session.midpoint
        stop, tp1, tp2 = build_risk_geometry(entry, bias.direction, session.box_top - session.box_bottom)
        return _intent(session, regime, "TREND", bias.direction, bias.reason_code,
                       "MIDPOINT", entry, stop, tp1, tp2, "RESEARCH_TREND_BIAS")
    sweep = detect_strict_sweep(session.candles, established_high, established_low)
    if sweep.qualified:
        candle = session.candles[sweep.candidate_index]
        entry = max(candle.open, candle.close) if sweep.direction == "SHORT" else min(candle.open, candle.close)
        stop, tp1, tp2 = build_risk_geometry(entry, sweep.direction, session.box_top - session.box_bottom)
        return _intent(session, regime, "SWEEP", sweep.direction, sweep.reason_code,
                       "SWEEP_BODY", entry, stop, tp1, tp2, "RESEARCH_STRICT_SWEEP")
    return _unresolved_intent(session, sweep.reason_code, regime, "RANGE_DIRECTION_UNRESOLVED")


def _unresolved_intent(session: FrozenSession, reason: str, regime: str = "UNRESOLVED",
                       bias_reason: str = "BIAS_UNRESOLVED") -> TradeIntent:
    return _intent(session, regime, None, None, bias_reason, None, None, None, None, None,
                   "RESEARCH_UNRESOLVED", reason)


def _intent(session: FrozenSession, regime: str, setup: str | None, bias: str | None,
            bias_reason: str, entry_type: str | None, entry: float | None,
            stop: float | None, tp1: float | None, tp2: float | None,
            *flags: str) -> TradeIntent:
    return TradeIntent(
        "SESSION_STRATEGY_V2_RESEARCH", session.leg_key, session.start, session.end,
        session.box_top, session.box_bottom, session.midpoint,
        session.box_top - session.box_bottom, regime,
        "RESEARCH_ONLY", "RESEARCH_UNRESOLVED" if setup is None else "RESEARCH",
        setup, bias, bias_reason, entry_type, entry,
        None if entry is None else abs(entry - stop), stop, tp1, 4.0, 0.75, tp2, 5.0,
        0.25, None, "UNAVAILABLE_M1_DATA", "ANALYSIS_ONLY", tuple(flags),
        tuple((bias_reason, *flags)),
    )