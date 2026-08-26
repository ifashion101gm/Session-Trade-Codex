"""Canonical simplified strategy router -- research candidate-setup generation only.

Status: RESEARCH. Not wired to any MT5 gateway or order-sending path. See
ACTIVE_STRATEGY_ARCHITECTURE.md and CANONICAL_SESSION_MIGRATION_REPORT.md.
"""
from .candles import Candle
from .reference_box import ReferenceBox, build_reference_box
from .classifier import Regime, classify, CLASSIFIER_ID, CLASSIFIER_VERSION, EFFICIENCY_RATIO_THRESHOLD
from .setups import (
    SetupDecision, SetupType, Direction, DecisionStatus,
    entry_1_trend, entry_2_sweep, entry_3_range,
)
from .router import route_completed_session

__all__ = [
    "Candle", "ReferenceBox", "build_reference_box",
    "Regime", "classify", "CLASSIFIER_ID", "CLASSIFIER_VERSION", "EFFICIENCY_RATIO_THRESHOLD",
    "SetupDecision", "SetupType", "Direction", "DecisionStatus",
    "entry_1_trend", "entry_2_sweep", "entry_3_range",
    "route_completed_session",
]
