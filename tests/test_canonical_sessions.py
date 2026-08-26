"""CANONICAL_SESSION_WINDOWS_V1 boundary/bar-count tests (config/canonical_sessions.yaml).

Guards against the timing drift found across the repo's session configs (see
STRATEGY_LEDGER.md and the LEGACY_SESSION_WINDOW annotations in config/*.yaml): the canonical
Asian/London-AM/New-York-AM hours and bar counts, and smc_3r_v1's consumption of them, must not
silently change.
"""
from __future__ import annotations

import pandas as pd
import pytest

from smc_3r_v1.canonical_sessions import (
    load_canonical_sessions,
    asian_window,
    london_am_window,
    new_york_am_window,
)
from smc_3r_v1.smc_state_machine import SMCStateMachine

DAY = pd.Timestamp("2026-01-05", tz="UTC")


def test_canonical_window_hours_and_bar_counts():
    assert asian_window() == (0, 6, 24)
    assert london_am_window() == (6, 11, 20)
    assert new_york_am_window() == (12, 15, 12)


def test_canonical_sessions_yaml_is_utc_half_open_no_dst():
    # load_canonical_sessions() itself raises SESSION_CONTRACT_CONFLICT on a timezone/boundary
    # mismatch; simply loading successfully here is the assertion.
    load_canonical_sessions()


@pytest.mark.parametrize(
    "hour,minute,expected",
    [
        (5, 45, True),   # last Asian M15 bar
        (6, 0, False),   # Asian box is frozen; belongs to London instead
    ],
)
def test_asian_boundary(hour, minute, expected):
    ts = DAY + pd.Timedelta(hours=hour, minutes=minute)
    window = asian_window()
    in_asian = window.start_hour <= ts.hour < window.end_hour
    assert in_asian is expected


def test_london_am_boundary_via_state_machine():
    sm = SMCStateMachine()
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=6)) is True
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=10, minutes=45)) is True
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=11)) is False


def test_new_york_am_boundary_via_state_machine():
    sm = SMCStateMachine()
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=12)) is True
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=14, minutes=45)) is True
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=15)) is False


def test_gap_between_london_and_new_york_is_excluded():
    sm = SMCStateMachine()
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=11)) is False
    assert sm.is_in_session_window(DAY + pd.Timedelta(hours=11, minutes=30)) is False
