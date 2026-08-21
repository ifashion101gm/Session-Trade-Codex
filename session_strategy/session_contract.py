"""Versioned, side-effect-free session definitions for SESSION_FLOW_V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
import math
from typing import Sequence


MMT = timezone(timedelta(hours=6, minutes=30), name="MMT")


@dataclass(frozen=True)
class SessionLeg:
    key: str
    reference: str
    start_utc: time
    end_utc: time
    expected_m15_candles: int

    def bounds(self, trading_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(trading_date, self.start_utc, tzinfo=timezone.utc)
        end = datetime.combine(trading_date, self.end_utc, tzinfo=timezone.utc)
        if end <= start:
            end += timedelta(days=1)
        return start, end

    def validate_bar_opens(self, trading_date: date, opens: list[datetime]) -> None:
        start, end = self.bounds(trading_date)
        expected = [start + timedelta(minutes=15 * i)
                    for i in range(self.expected_m15_candles)]
        normalized = [value.astimezone(timezone.utc) for value in opens]
        if normalized != expected:
            raise ValueError(
                f"INVALID_REFERENCE_SESSION: {self.key} expected "
                f"{self.expected_m15_candles} contiguous M15 bars in "
                f"[{start.isoformat()}, {end.isoformat()})"
            )

    def activation_utc(self, trading_date: date) -> datetime:
        return self.bounds(trading_date)[1]

    def activation_mmt(self, trading_date: date) -> datetime:
        return self.activation_utc(trading_date).astimezone(MMT)


SESSION_FLOW_V2_LEGS = {
    "POST_ASIAN": SessionLeg("POST_ASIAN", "ASIAN", time(0), time(8), 32),
    "POST_LONDON": SessionLeg("POST_LONDON", "LONDON", time(7), time(12), 20),
}


ER_ONLY_V2_THRESHOLD = 0.40
ER_ONLY_V2_CLASSIFIER_ID = "ER_ONLY_V2"
ER_ONLY_V2_STATUS = "VALIDATED"
SESSION_FLOW_V2_SIMPLE_ID = "SESSION_FLOW_V2_SIMPLE"


class SweepResolution(str, Enum):
    """Normalized result from the signed completed-box Sweep classifier."""

    QUALIFIED = "QUALIFIED"
    NO_SWEEP = "NO_SWEEP"


class StrategyType(str, Enum):
    """Legacy compatibility alias values; authoritative field is setup_type."""
    TREND = "TREND"
    SWEEP = "SWEEP"
    RANGE = "RANGE"


SetupType = StrategyType


class SessionType(str, Enum):
    TREND = "TREND"
    RANGE = "RANGE"


class EntryEngine(str, Enum):
    ENTRY_1 = "ENTRY_1"
    ENTRY_2 = "ENTRY_2"
    ENTRY_3 = "ENTRY_3"


class SweepSide(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"
    DUAL = "DUAL"


@dataclass(frozen=True)
class M15Bar:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class FrozenSession:
    """Validated, immutable Session Box Skill output."""

    leg_key: str
    trading_date: date
    start: datetime
    end: datetime
    candles: tuple[M15Bar, ...]
    box_top: float
    box_bottom: float
    midpoint: float
    first_open: float
    final_close: float
    status: str = "VALID_FROZEN_SESSION"


@dataclass(frozen=True)
class TrendRangeClassification:
    """ER_ONLY_V2 result; intentionally contains no setup or trade fields."""

    classifier_id: str
    status: str
    threshold: float
    equality: str
    zero_path: str
    session_type: SessionType
    direction: str | None
    displacement: float
    path_length: float
    efficiency_ratio: float
    session_start: datetime
    session_end: datetime
    candle_count: int


@dataclass(frozen=True)
class SimpleStrategyRoute:
    """Stateless completed-box route for SESSION_FLOW_V2_SIMPLE."""

    strategy_flow: str
    box_status: str
    regime: TrendRangeClassification
    sweep_scope: str
    sweep_evaluated: bool
    sweep_qualified: bool | None
    sweep: SweepClassification | None
    setup_type: SetupType
    entry_engine: EntryEngine
    direction: str | None
    status: str = "ROUTE_RESOLVED"


@dataclass(frozen=True)
class SweepClassification:
    qualified: bool
    candidates_checked: int
    candidate_index: int | None = None
    candidate_time: datetime | None = None
    side: SweepSide | None = None
    direction: str | None = None
    prior_high: float | None = None
    prior_low: float | None = None
    prior_level: float | None = None
    extreme: float | None = None
    close: float | None = None
    penetration: float | None = None
    reclaim_clearance: float | None = None
    classifier_version: str = "1.0"
    entry_status: str = "NOT_EVALUATED"


@dataclass(frozen=True)
class StrategySelection:
    efficiency_ratio: float
    trend_test: bool
    sweep_test: str
    setup_type: SetupType
    state: str
    session_type: SessionType
    entry_engine: EntryEngine
    direction: str | None = None
    entry_status: str = "NOT_EVALUATED"
    sweep: SweepClassification | None = None

    @property
    def strategy_type(self) -> SetupType:
        """Deprecated compatibility alias for setup_type."""
        return self.setup_type


def path_efficiency_ratio(first_open: float, closes: Sequence[float]) -> float:
    """Signed ER_ONLY_V2 1.0 formula over completed reference closes."""
    if not closes:
        raise ValueError("INVALID_REFERENCE_SESSION: at least one completed close is required")
    displacement = abs(float(closes[-1]) - float(first_open))
    path_length = abs(float(closes[0]) - float(first_open))
    path_length += sum(abs(float(current) - float(previous))
                       for previous, current in zip(closes, closes[1:]))
    return 0.0 if path_length == 0 else displacement / path_length


def validate_and_freeze_session(
    leg: SessionLeg,
    trading_date: date,
    candles: Sequence[M15Bar],
    decision_time: datetime,
) -> FrozenSession:
    """Run the Session Box Skill gate and freeze valid completed M15 evidence."""
    if decision_time.tzinfo is None:
        raise ValueError("INVALID_SESSION_DATA: decision_time must be timezone-aware")
    start, end = leg.bounds(trading_date)
    if decision_time.astimezone(timezone.utc) < end:
        raise ValueError("INVALID_SESSION_DATA: session contains incomplete M15 candles")
    try:
        leg.validate_bar_opens(trading_date, [bar.open_time for bar in candles])
    except ValueError as exc:
        raise ValueError(f"INVALID_SESSION_DATA: {exc}") from exc
    for bar in candles:
        if bar.open_time.tzinfo is None:
            raise ValueError("INVALID_SESSION_DATA: candle timestamp must be timezone-aware")
        values = tuple(float(value) for value in (bar.open, bar.high, bar.low, bar.close))
        if any(not math.isfinite(value) or value <= 0 for value in values) or \
                bar.high < max(bar.open, bar.close) or \
                bar.low > min(bar.open, bar.close) or bar.low > bar.high:
            raise ValueError("INVALID_SESSION_DATA: invalid M15 OHLC")
    frozen = tuple(candles)
    top = max(float(bar.high) for bar in frozen)
    bottom = min(float(bar.low) for bar in frozen)
    return FrozenSession(
        leg.key, trading_date, start, end, frozen, top, bottom,
        (top + bottom) / 2.0, float(frozen[0].open), float(frozen[-1].close),
    )


def classify_trend_range(session: FrozenSession) -> TrendRangeClassification:
    """Classify only a validated frozen session with canonical ER_ONLY_V2."""
    if session.status != "VALID_FROZEN_SESSION":
        raise ValueError("INVALID_SESSION_DATA: classifier requires frozen session")
    closes = [float(bar.close) for bar in session.candles]
    displacement = abs(session.final_close - session.first_open)
    path_length = abs(closes[0] - session.first_open)
    path_length += sum(abs(current - previous)
                       for previous, current in zip(closes, closes[1:]))
    er = 0.0 if path_length == 0 else displacement / path_length
    session_type = SessionType.TREND if er >= ER_ONLY_V2_THRESHOLD else SessionType.RANGE
    direction = None
    if session_type is SessionType.TREND:
        direction = box_direction_v1(session.first_open, session.final_close)
    return TrendRangeClassification(
        ER_ONLY_V2_CLASSIFIER_ID, ER_ONLY_V2_STATUS, ER_ONLY_V2_THRESHOLD,
        "TREND", "RANGE", session_type, direction, displacement, path_length, er,
        session.start, session.end, len(session.candles),
    )


def box_direction_v1(first_open: float, final_close: float) -> str | None:
    """Signed BOX_DIRECTION_V1; known at immutable reference-box completion."""
    if float(final_close) > float(first_open):
        return "LONG"
    if float(final_close) < float(first_open):
        return "SHORT"
    return None


def select_strategy(first_open: float, closes: Sequence[float],
                    sweep_resolution: SweepResolution | None = None) -> StrategySelection:
    """Select only the V2 strategy type; entry qualification remains downstream.

    This compatibility helper accepts an already-normalized Sweep result. New code
    should use ``classify_completed_box`` so the signed causal scan is performed.
    """
    er = path_efficiency_ratio(first_open, closes)
    if er >= ER_ONLY_V2_THRESHOLD:
        return StrategySelection(er, True, "NOT_EVALUATED", SetupType.TREND,
                                 "STRATEGY_RESOLVED", SessionType.TREND,
                                 EntryEngine.ENTRY_1,
                                 direction=box_direction_v1(first_open, closes[-1]),
                                 entry_status="ENTRY_1_CONTRACT_INCOMPLETE")
    if sweep_resolution is None:
        raise ValueError("SWEEP_RESULT_REQUIRED: use classify_completed_box")
    resolution = SweepResolution(sweep_resolution)
    if resolution is SweepResolution.QUALIFIED:
        return StrategySelection(er, False, "QUALIFIED", SetupType.SWEEP,
                                 "STRATEGY_RESOLVED", SessionType.RANGE,
                                 EntryEngine.ENTRY_2)
    if resolution is SweepResolution.NO_SWEEP:
        return StrategySelection(er, False, "NO_SWEEP", SetupType.RANGE,
                                 "STRATEGY_RESOLVED", SessionType.RANGE,
                                 EntryEngine.ENTRY_3)
    raise AssertionError(f"unsupported completed-box Sweep result: {resolution}")


def classify_sweep(candles: Sequence[M15Bar]) -> SweepClassification:
    """Apply signed SWEEP_SETUP_V2_CLASSIFIER 1.0 to one completed box.

    Each candidate is tested against highs/lows formed strictly from earlier candles.
    The first qualified candidate owns classification. No post-box data is accepted by
    this pure function's caller-facing completed-box validator.
    """
    if len(candles) < 2:
        raise ValueError("INVALID_REFERENCE_SESSION: Sweep requires a prior candle")
    prior_high = float(candles[0].high)
    prior_low = float(candles[0].low)
    checked = 0
    for index, candle in enumerate(candles[1:], start=1):
        checked += 1
        high_sweep = float(candle.high) > prior_high and float(candle.close) < prior_high
        low_sweep = float(candle.low) < prior_low and float(candle.close) > prior_low
        if high_sweep or low_sweep:
            if high_sweep and low_sweep:
                return SweepClassification(
                    True, checked, index, candle.open_time, SweepSide.DUAL, None,
                    prior_high, prior_low, None, None, float(candle.close), None, None,
                    entry_status="BLOCKED_DUAL_SIDE_AMBIGUITY",
                )
            if high_sweep:
                return SweepClassification(
                    True, checked, index, candle.open_time, SweepSide.HIGH, "SHORT",
                    prior_high, prior_low, prior_high, float(candle.high),
                    float(candle.close), float(candle.high) - prior_high,
                    prior_high - float(candle.close),
                    entry_status="BLOCKED_BY_ENTRY_2_SPEC",
                )
            return SweepClassification(
                True, checked, index, candle.open_time, SweepSide.LOW, "LONG",
                prior_high, prior_low, prior_low, float(candle.low),
                float(candle.close), prior_low - float(candle.low),
                float(candle.close) - prior_low,
                entry_status="BLOCKED_BY_ENTRY_2_SPEC",
            )
        prior_high = max(prior_high, float(candle.high))
        prior_low = min(prior_low, float(candle.low))
    return SweepClassification(False, checked)


def route_v2_simple(session: FrozenSession) -> SimpleStrategyRoute:
    """Return exactly one setup family using completed reference candles only."""
    regime = classify_trend_range(session)
    if regime.session_type is SessionType.TREND:
        return SimpleStrategyRoute(
            SESSION_FLOW_V2_SIMPLE_ID, session.status, regime,
            "REFERENCE_SESSION_ONLY", False, None, None,
            SetupType.TREND, EntryEngine.ENTRY_1, regime.direction,
        )
    sweep = classify_sweep(session.candles)
    if sweep.qualified:
        return SimpleStrategyRoute(
            SESSION_FLOW_V2_SIMPLE_ID, session.status, regime,
            "REFERENCE_SESSION_ONLY", True, True, sweep,
            SetupType.SWEEP, EntryEngine.ENTRY_2, sweep.direction,
        )
    return SimpleStrategyRoute(
        SESSION_FLOW_V2_SIMPLE_ID, session.status, regime,
        "REFERENCE_SESSION_ONLY", True, False, sweep,
        SetupType.RANGE, EntryEngine.ENTRY_3, None,
    )


def classify_completed_box(
    leg: SessionLeg,
    trading_date: date,
    candles: Sequence[M15Bar],
) -> StrategySelection:
    """Validate, freeze, and classify one completed V2 reference box only."""
    frozen = validate_and_freeze_session(
        leg, trading_date, candles, leg.activation_utc(trading_date))
    route = route_v2_simple(frozen)
    classification = route.regime
    er = classification.efficiency_ratio
    if route.setup_type is SetupType.TREND:
        return StrategySelection(er, True, "NOT_EVALUATED", SetupType.TREND,
                                 "STRATEGY_RESOLVED", SessionType.TREND,
                                 EntryEngine.ENTRY_1,
                                 direction=classification.direction,
                                 entry_status="ENTRY_1_CONTRACT_INCOMPLETE")
    sweep = route.sweep
    if route.setup_type is SetupType.SWEEP:
        assert sweep is not None
        return StrategySelection(er, False, "QUALIFIED", SetupType.SWEEP,
                                 "STRATEGY_RESOLVED", SessionType.RANGE,
                                 EntryEngine.ENTRY_2, sweep.direction,
                                 sweep.entry_status, sweep)
    return StrategySelection(er, False, "NO_SWEEP", SetupType.RANGE,
                             "STRATEGY_RESOLVED", SessionType.RANGE,
                             EntryEngine.ENTRY_3, sweep=sweep)


def classify_completed_reference(
    leg: SessionLeg,
    trading_date: date,
    opens: Sequence[datetime],
    first_open: float,
    closes: Sequence[float],
    sweep_resolution: SweepResolution | None = None,
) -> StrategySelection:
    """Validate and classify exactly one immutable completed reference box.

    Extra, missing, duplicate, or post-reference bars are rejected rather than
    silently entering the classifier.
    """
    leg.validate_bar_opens(trading_date, list(opens))
    if len(closes) != leg.expected_m15_candles:
        raise ValueError(
            f"INVALID_REFERENCE_SESSION: {leg.key} expected "
            f"{leg.expected_m15_candles} completed closes"
        )
    return select_strategy(first_open, closes, sweep_resolution)
