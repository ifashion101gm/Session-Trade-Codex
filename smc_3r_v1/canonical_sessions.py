"""Back-compat shim over the shared canonical session service (`session_clock.py`).

smc_3r_v1 was the first strategy migrated onto CANONICAL_SESSION_WINDOWS_V1 and originally had
its own private loader here. That loader has been consolidated into session_clock.py (the one
reusable session service for the whole repo) -- this module now just re-exports the pieces
smc_3r_v1's own code and tests already call, in the shape they already expect.
"""
from typing import NamedTuple
import session_clock as _clock

load_canonical_sessions = _clock.load_canonical_sessions


class SessionWindow(NamedTuple):
    start_hour: int
    end_hour: int
    expected_m15_bars: int


def _as_window(name: str) -> SessionWindow:
    d = _clock.get_session_definition(name)
    return SessionWindow(d.start_hour, d.end_hour, d.expected_m15_bars)


def asian_window() -> SessionWindow:
    return _as_window("asian")


def london_am_window() -> SessionWindow:
    return _as_window("london_am")


def new_york_am_window() -> SessionWindow:
    return _as_window("new_york_am")
