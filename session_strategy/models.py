from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def bullish(self) -> bool:
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open


@dataclass(frozen=True)
class SymbolSpec:
    name: str
    digits: int
    point: float
    tick_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level_price: float


@dataclass(frozen=True)
class AccountSnapshot:
    login_masked: str
    account_type: str
    balance: float
    equity: float
    server: str
    trade_allowed: bool
    expert_allowed: bool
    ping_ms: float | None


@dataclass(frozen=True)
class AsianLevels:
    """Immutable once the session closes. Candles after the lock never change these."""
    high: float
    low: float
    range: float
    midpoint: float
    open: float
    close: float
    risk_unit: float
    lower_quartile: float
    upper_quartile: float
    midpoint_zone_low: float
    midpoint_zone_high: float
    efficiency_ratio: float
    close_location: float


@dataclass
class Gate:
    name: str
    passed: bool
    detail: str


# Stable reason codes. Every rejection must map to one of these.
class Reason:
    INVALID_ASIAN_DATA = "INVALID_ASIAN_DATA"
    INVALID_ASIAN_RANGE = "INVALID_ASIAN_RANGE"
    EXCESSIVE_SPREAD = "EXCESSIVE_SPREAD"
    UNCERTAIN_SESSION_TYPE = "UNCERTAIN_SESSION_TYPE"
    EXECUTION_WINDOW_EXPIRED = "EXECUTION_WINDOW_EXPIRED"
    OUTSIDE_EXECUTION_WINDOW = "OUTSIDE_EXECUTION_WINDOW"
    NO_QUALIFYING_SETUP = "NO_QUALIFYING_SETUP"
    FIXED_STOP_NOT_BEYOND_SWEEP = "FIXED_STOP_NOT_BEYOND_SWEEP"
    BROKER_STOP_DISTANCE = "BROKER_STOP_DISTANCE"
    VOLUME_OUT_OF_BOUNDS = "VOLUME_OUT_OF_BOUNDS"
    DAILY_RISK_EXCEEDED = "DAILY_RISK_EXCEEDED"
    DRAWDOWN_EXCEEDED = "DRAWDOWN_EXCEEDED"
    ENVIRONMENT_NOT_AUTHORIZED = "ENVIRONMENT_NOT_AUTHORIZED"
    SYMBOL_NOT_SUPPORTED = "SYMBOL_NOT_SUPPORTED"
    BROKER_CLOCK_UNVERIFIED = "BROKER_CLOCK_UNVERIFIED"
    HIGH_IMPACT_NEWS_WINDOW = "HIGH_IMPACT_NEWS_WINDOW"
    NEWS_CALENDAR_UNAVAILABLE = "NEWS_CALENDAR_UNAVAILABLE"
    TRADE_ALREADY_TAKEN = "TRADE_ALREADY_TAKEN"
    MAX_SESSION_TRADES_EXCEEDED = "MAX_SESSION_TRADES_EXCEEDED"
    RUNNER_BELOW_MINIMUM_VOLUME = "RUNNER_BELOW_MINIMUM_VOLUME"
    ACCOUNT_NOT_ALLOWLISTED = "ACCOUNT_NOT_ALLOWLISTED"
    # positive evidence
    RANGE_SESSION = "RANGE_SESSION"
    TREND_SESSION = "TREND_SESSION"
    SELL_SIDE_SWEEP = "SELL_SIDE_SWEEP"
    BUY_SIDE_SWEEP = "BUY_SIDE_SWEEP"
    CLOSE_BACK_INSIDE = "CLOSE_BACK_INSIDE"
    STRUCTURAL_STOP_VALID = "STRUCTURAL_STOP_VALID"
    BOUNDARY_REJECTION = "BOUNDARY_REJECTION"
    MIDPOINT_RETRACEMENT = "MIDPOINT_RETRACEMENT"


@dataclass
class AnalysisResult:
    analysis_id: str
    timestamp_utc: datetime
    trading_date: str
    symbol: str
    account: AccountSnapshot
    bid: float
    ask: float
    spread: float
    strategy_id: str = "ASIAN_SESSION_V1"
    contract_version: str = "1.0"
    schema_version: int = 2
    timezone: str = "UTC"
    broker_utc_offset_hours: int | None = None
    asian_start: datetime | None = None
    asian_end: datetime | None = None
    asian_high: float | None = None
    asian_low: float | None = None
    asian_range: float | None = None
    midpoint: float | None = None
    asian_open: float | None = None
    asian_close: float | None = None
    directional_bias: str | None = None
    risk_unit: float | None = None
    lower_quartile: float | None = None
    upper_quartile: float | None = None
    efficiency_ratio: float | None = None
    close_location: float | None = None
    session_type: str = "UNCERTAIN"
    setup: str = "NONE"
    direction: str | None = None
    signal_time: datetime | None = None
    signal_candle: dict[str, Any] | None = None
    entry: float | None = None
    stop_loss: float | None = None
    initial_risk: float | None = None
    tp1_4r: float | None = None
    tp2_5r: float | None = None
    partial_target: float | None = None
    partial_target_label: str | None = None
    runner_management: str | None = None
    partial_close_percent: float | None = None
    risk_fraction: float | None = None
    volume: float | None = None
    partial_volume: float | None = None
    runner_volume: float | None = None
    runner_below_minimum: bool = False
    estimated_cost_r: float | None = None
    gross_tp2_r: float | None = None
    net_tp1_r: float | None = None
    net_tp2_r: float | None = None
    broker_symbol: str | None = None
    intended_risk_cash: float | None = None
    actual_risk_cash: float | None = None
    actual_risk_percent: float | None = None
    risk_basis_cash: float | None = None
    expiry_utc: datetime | None = None
    gates: list[Gate] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    session_candle_times: list[str] = field(default_factory=list)
    execution_candle_times: list[str] = field(default_factory=list)
    config_hash: str = ""
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return bool(self.gates) and all(g.passed for g in self.gates) and self.entry is not None

    @property
    def status(self) -> str:
        return "SIGNAL_ACCEPTED" if self.accepted else "NO_TRADE"

    def add_reason(self, code: str) -> None:
        if code not in self.reason_codes:
            self.reason_codes.append(code)

    def to_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat().replace("+00:00", "Z")
            if isinstance(value, list):
                return [convert(v) for v in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value
        data = asdict(self)
        data["accepted"] = self.accepted
        data["status"] = self.status
        return convert(data)
