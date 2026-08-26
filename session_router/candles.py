from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    time: datetime  # bar-open time, UTC
    open: float
    high: float
    low: float
    close: float
