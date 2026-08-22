from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Literal

# Broker‑neutral representation of a trade decision
@dataclass(frozen=True)
class TradeIntent:
    strategy_id: str
    strategy_version: str
    symbol: str
    reference_session: str
    reference_start: datetime
    reference_end: datetime
    reference_high: float
    reference_low: float
    reference_range: float
    regime: Literal["TREND", "RANGE"]
    setup: str
    direction: Literal["LONG", "SHORT"]
    signal_time: datetime
    signal_price: float
    entry_type: Literal["MARKET", "LIMIT"]
    entry_price: Optional[float]
    stop_price: float
    target_price: float
    risk_fraction: float
    reason_code: str
    entry_contract_signed: bool

# MT5‑ready request (only the fields MT5 needs)
@dataclass(frozen=True)
class ExecutableOrder:
    action: int
    symbol: str
    volume: float
    order_type: int
    price: float
    sl: float
    tp: float
    deviation: int
    magic: int
    comment: str
    type_time: int
    type_filling: int

class ValidationResult(Enum):
    SUCCESS = "SUCCESS"
    INVALID_INTENT = "INVALID_INTENT"
    MISSING_DIRECTION = "MISSING_DIRECTION"
    MISSING_ENTRY = "MISSING_ENTRY"
    MISSING_STOP = "MISSING_STOP"
    MISSING_TARGET = "MISSING_TARGET"
    # These were returned by validator.py but absent from the enum (H-1 fix)
    INVALID_STOP = "INVALID_STOP"
    INVALID_TARGET = "INVALID_TARGET"
    INVALID_TRADE_GEOMETRY = "INVALID_TRADE_GEOMETRY"
    INVALID_RISK = "INVALID_RISK"
    ENTRY_CONTRACT_UNSIGNED = "ENTRY_CONTRACT_UNSIGNED"
    TRADING_DISABLED = "TRADING_DISABLED"
    SUBMIT_PERMISSION_DENIED = "SUBMIT_PERMISSION_DENIED"
    NON_DEMO_ACCOUNT = "NON_DEMO_ACCOUNT"
    MARKET_DATA_STALE = "MARKET_DATA_STALE"
    SYMBOL_NOT_TRADEABLE = "SYMBOL_NOT_TRADEABLE"

# Result of an execution attempt (journal entry)
@dataclass(frozen=True)
class ExecutionReport:
    intent: TradeIntent
    validation: ValidationResult
    volume: Optional[float] = None
    order_check_retcode: Optional[int] = None
    order_send_retcode: Optional[int] = None
    mt5_ticket: Optional[int] = None
    # M-8 fix: use default_factory; datetime.utcnow() at class level evaluated
    # once at import time (shared across all instances) and is deprecated in 3.12+.
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class RiskResultReason(Enum):
    SUCCESS = "SUCCESS"
    INVALID_ACCOUNT_EQUITY = "INVALID_ACCOUNT_EQUITY"
    INVALID_RISK_FRACTION = "INVALID_RISK_FRACTION"
    INVALID_ENTRY_PRICE = "INVALID_ENTRY_PRICE"
    INVALID_STOP_PRICE = "INVALID_STOP_PRICE"
    ZERO_STOP_DISTANCE = "ZERO_STOP_DISTANCE"
    INVALID_TICK_SIZE = "INVALID_TICK_SIZE"
    INVALID_TICK_VALUE = "INVALID_TICK_VALUE"
    INVALID_VOLUME_MIN = "INVALID_VOLUME_MIN"
    INVALID_VOLUME_MAX = "INVALID_VOLUME_MAX"
    INVALID_VOLUME_STEP = "INVALID_VOLUME_STEP"
    RAW_VOLUME_INVALID = "RAW_VOLUME_INVALID"
    VOLUME_BELOW_MINIMUM = "VOLUME_BELOW_MINIMUM"
    VOLUME_ABOVE_MAXIMUM = "VOLUME_ABOVE_MAXIMUM"
    VOLUME_NORMALIZATION_FAILED = "VOLUME_NORMALIZATION_FAILED"
    ESTIMATED_LOSS_EXCEEDS_RISK = "ESTIMATED_LOSS_EXCEEDS_RISK"

@dataclass(frozen=True)
class RiskResult:
    passed: bool
    reason_code: RiskResultReason
    message: str
    risk_amount: Optional[float] = None
    stop_distance: Optional[float] = None
    stop_ticks: Optional[float] = None
    loss_per_lot: Optional[float] = None
    raw_volume: Optional[float] = None
    normalized_volume: Optional[float] = None
    estimated_loss_at_stop: Optional[float] = None
    risk_utilization: Optional[float] = None
