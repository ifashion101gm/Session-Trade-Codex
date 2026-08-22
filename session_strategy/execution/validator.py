from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import TradeIntent, ValidationResult


def validate_intent(intent: TradeIntent) -> ValidationResult:
    """Fail‑closed validation of a :class:`TradeIntent`.

    Returns a member of :class:`ValidationResult`.  The caller should treat any
    result other than ``ValidationResult.SUCCESS`` as a block.
    """
    # Basic required fields
    if not intent.strategy_id:
        return ValidationResult.INVALID_INTENT
    if not intent.strategy_version:
        return ValidationResult.INVALID_INTENT
    if not intent.symbol:
        return ValidationResult.INVALID_INTENT

    if not intent.reference_session:
        return ValidationResult.INVALID_INTENT
    if intent.reference_range is None or intent.reference_range <= 0:
        return ValidationResult.INVALID_INTENT

    if intent.regime not in ("TREND", "RANGE"):
        return ValidationResult.INVALID_INTENT
    if not intent.setup:
        return ValidationResult.INVALID_INTENT
    if not intent.direction:
        return ValidationResult.MISSING_DIRECTION

    if not isinstance(intent.signal_time, datetime):
        return ValidationResult.INVALID_INTENT
    if intent.signal_price is None or intent.signal_price <= 0:
        return ValidationResult.INVALID_INTENT

    if not intent.entry_type:
        return ValidationResult.MISSING_ENTRY
    # entry_reference is derived from entry_price if present, otherwise use signal_price
    entry_reference = intent.entry_price if intent.entry_price is not None else intent.signal_price

    if entry_reference is None or entry_reference <= 0:
        return ValidationResult.MISSING_ENTRY

    if intent.stop_price is None or intent.stop_price <= 0:
        return ValidationResult.INVALID_STOP
    if intent.target_price is None or intent.target_price <= 0:
        return ValidationResult.INVALID_TARGET

    # Risk limits – a simple upper bound (could be configurable in future)
    if intent.risk_fraction is None or intent.risk_fraction <= 0:
        return ValidationResult.INVALID_RISK
    if intent.risk_fraction > 0.05:  # 5% hard‑coded maximum for now
        return ValidationResult.INVALID_RISK

    if not intent.entry_contract_signed:
        return ValidationResult.ENTRY_CONTRACT_UNSIGNED

    # Geometry checks
    if intent.direction == "LONG":
        if not (intent.stop_price < entry_reference < intent.target_price):
            return ValidationResult.INVALID_TRADE_GEOMETRY
    elif intent.direction == "SHORT":
        if not (intent.target_price < entry_reference < intent.stop_price):
            return ValidationResult.INVALID_TRADE_GEOMETRY
    else:
        return ValidationResult.INVALID_INTENT

    return ValidationResult.SUCCESS
