from typing import NamedTuple, Optional
import pandas as pd
from .canonical_sessions import asian_window


class SessionLevels(NamedTuple):
    asian_high: Optional[float]
    asian_low: Optional[float]
    pdh: Optional[float]
    pdl: Optional[float]


def compute_reference_levels(
    df_m5: pd.DataFrame,
    current_ts: pd.Timestamp,
    expected_daily_bars: int = 288,
    min_daily_coverage_pct: float = 0.95
) -> SessionLevels:
    """
    Computes Asian Session (CANONICAL_SESSION_WINDOWS_V1, config/canonical_sessions.yaml)
    and Prior Trading Day levels.
    Walks backward through prior calendar dates until finding a session meeting >=95% coverage.
    """
    current_date = current_ts.floor('D')

    # Asian Session window from the canonical session contract, expressed in M5 bars
    # (canonical bar counts are M15; multiply by 3 for the M5 timeframe used here).
    window = asian_window()
    expected_m5_bars = window.expected_m15_bars * 3
    asian_start = current_date + pd.Timedelta(hours=window.start_hour)
    asian_end = current_date + pd.Timedelta(hours=window.end_hour)
    asian_bars = df_m5[(df_m5.index >= asian_start) & (df_m5.index < asian_end)]

    asian_high = asian_bars['high'].max() if len(asian_bars) == expected_m5_bars else None
    asian_low = asian_bars['low'].min() if len(asian_bars) == expected_m5_bars else None

    # 2. Prior Trading Day (Iterative backward walk)
    prior_dates = df_m5[df_m5.index < current_date].index.floor('D').unique().sort_values(ascending=False)
    min_required_bars = int(expected_daily_bars * min_daily_coverage_pct)
    pdh, pdl = None, None

    for candidate_date in prior_dates:
        candidate_bars = df_m5[(df_m5.index >= candidate_date) & (df_m5.index < candidate_date + pd.Timedelta(days=1))]
        if len(candidate_bars) >= min_required_bars:
            pdh = candidate_bars['high'].max()
            pdl = candidate_bars['low'].min()
            break

    return SessionLevels(asian_high=asian_high, asian_low=asian_low, pdh=pdh, pdl=pdl)
