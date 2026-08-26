"""ASIAN_SESSION_V2 (config/strategy_v2.yaml) -- the canonical-session successor to the
LEGACY_FROZEN ASIAN_SESSION_V1 (config/strategy.yaml). See CANONICAL_SESSION_MIGRATION_REPORT.md
and CANONICAL_STRATEGY_VERSION_MAP.md."""
from __future__ import annotations

from dataclasses import replace

import pytest

import session_clock as sc
from session_strategy.config import load_config


V2_PATH = "config/strategy_v2.yaml"
V1_PATH = "config/strategy.yaml"


def test_v2_session_window_matches_canonical_asian():
    config = load_config(V2_PATH)
    asian = sc.get_session_definition("asian")
    assert config.session_start_utc == f"{asian.start_hour:02d}:00"
    assert config.session_end_utc == f"{asian.end_hour:02d}:00"
    assert config.session_candles == asian.expected_m15_bars == 24


def test_v2_has_no_execution_authority():
    config = load_config(V2_PATH)
    assert config.mode == "analysis_only"
    assert config.execution_permissions["submit_orders"] is False
    assert config.execution_permissions["modify_orders"] is False
    assert config.execution_permissions["close_positions"] is False
    assert config.governance["demo_execution_authorized"] is False
    assert config.governance["live_execution_authorized"] is False


def test_v2_strategy_identity_is_distinct_from_v1():
    v1 = load_config(V1_PATH)
    v2 = load_config(V2_PATH)
    assert v1.strategy_id == "ASIAN_SESSION_V1"
    assert v2.strategy_id == "ASIAN_SESSION_V2"
    assert v1.session_start_utc == "00:00" and v1.session_end_utc == "07:00"
    assert v2.session_start_utc == "00:00" and v2.session_end_utc == "06:00"


def test_v1_is_frozen_with_no_execution_authority_either():
    """LEGACY_FROZEN means the historical window is preserved, not that it's still live."""
    v1 = load_config(V1_PATH)
    assert v1.mode == "analysis_only"
    assert v1.execution_permissions["submit_orders"] is False
    assert v1.session_start_utc == "00:00" and v1.session_end_utc == "07:00"  # unchanged, frozen
    assert v1.session_candles == 28  # unchanged, frozen


def test_unknown_strategy_id_is_rejected_by_the_ssot_registry():
    v2 = load_config(V2_PATH)
    bogus = replace(v2, strategy_id="ASIAN_SESSION_V3", raw={**v2.raw, "strategy_id": "ASIAN_SESSION_V3"})
    from session_strategy.config import _validate
    with pytest.raises(ValueError, match="not a known session contract"):
        _validate(bogus)
