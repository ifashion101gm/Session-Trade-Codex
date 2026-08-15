from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import Counter
from statistics import median
from typing import Any
import logging
import time

import MetaTrader5 as mt5

from .models import AccountSnapshot, Candle, SymbolSpec


logger = logging.getLogger(__name__)


#: MT5 API surface this project must never call. Asserted at connect time so a dependency
#: upgrade or an accidental import cannot quietly widen the boundary.
FORBIDDEN_MT5_CALLS = (
    "order_send", "order_check", "order_calc_margin_send", "positions_close",
    "position_close", "order_delete", "order_modify", "login",
)


class MT5ReadOnlyGateway:
    """Narrow MT5 adapter. It intentionally exposes no trading methods."""

    @staticmethod
    def _assert_read_only() -> None:
        """Fail closed if this class ever grows a mutating method."""
        exposed = sorted(n for n in FORBIDDEN_MT5_CALLS if hasattr(MT5ReadOnlyGateway, n))
        if exposed:
            raise RuntimeError(f"Read-only boundary violated: gateway exposes {exposed}")

    def __init__(self, execution_permissions: dict | None = None):
        self._permissions = execution_permissions or {}

    def _assert_permissions(self) -> None:
        """`mode: analysis_only` is a label unless the boundary checks it."""
        granted = [k for k in ("submit_orders", "modify_orders", "close_positions")
                   if self._permissions.get(k)]
        if granted:
            raise RuntimeError(f"execution_permissions grant {granted}; this build cannot execute")

    def __enter__(self) -> "MT5ReadOnlyGateway":
        self._assert_read_only()
        self._assert_permissions()
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
        logger.info("mt5_connected mode=read_only trading_calls_exposed=0")
        return self

    def __exit__(self, *_: object) -> None:
        mt5.shutdown()

    def account(self) -> AccountSnapshot:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            raise RuntimeError(f"MT5 account unavailable: {mt5.last_error()}")
        login = str(account.login)
        trade_mode = int(account.trade_mode)
        account_type = {mt5.ACCOUNT_TRADE_MODE_DEMO: "demo", mt5.ACCOUNT_TRADE_MODE_REAL: "real"}.get(trade_mode, "contest")
        ping = getattr(terminal, "ping_last", None)
        return AccountSnapshot(
            login_masked=("*" * max(0, len(login) - 3)) + login[-3:],
            account_type=account_type,
            balance=float(account.balance), equity=float(account.equity), server=str(account.server),
            trade_allowed=bool(account.trade_allowed),
            expert_allowed=bool(account.trade_expert and getattr(terminal, "trade_allowed", False)),
            ping_ms=(float(ping) / 1000.0 if ping is not None else None),
        )

    def account_login_matches(self, allowed_logins: list[int]) -> bool:
        """Compare exact logins inside the gateway without exposing one to artifacts."""
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"MT5 account unavailable: {mt5.last_error()}")
        return int(account.login) in {int(login) for login in allowed_logins}

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        """Resolve live broker metadata. Never trust static configuration for
        digits, tick size, volume limits or stop distance."""
        info = mt5.symbol_info(symbol)
        if info is None or not getattr(info, "visible", True):
            if not mt5.symbol_select(symbol, True):
                raise ValueError(f"MT5 symbol not found or not selectable: {symbol}")
            info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"MT5 symbol not found: {symbol}")
        return SymbolSpec(symbol, int(info.digits), float(info.point), float(info.trade_tick_size or info.point),
                          float(info.volume_min), float(info.volume_max), float(info.volume_step),
                          float(info.trade_stops_level) * float(info.point))

    def tick(self, symbol: str) -> dict[str, float]:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Tick unavailable for {symbol}: {mt5.last_error()}")
        if float(tick.ask) <= float(tick.bid):
            logger.warning("quote_refresh symbol=%s reason=non_positive_spread bid=%s ask=%s", symbol, tick.bid, tick.ask)
            time.sleep(0.5)
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise RuntimeError(f"Tick unavailable after zero-spread refresh for {symbol}: {mt5.last_error()}")
            if float(tick.ask) <= float(tick.bid):
                logger.warning("quote_dropped symbol=%s reason=non_positive_spread bid=%s ask=%s", symbol, tick.bid, tick.ask)
        return {"bid": float(tick.bid), "ask": float(tick.ask), "time": float(tick.time)}

    def broker_utc_offset(self, symbols: list[str], now: datetime, maximum_age: int) -> int:
        """Derive a whole-hour server offset from a cross-symbol timestamp consensus."""
        candidates: list[int] = []
        for symbol in symbols:
            raw = self.tick(symbol)["time"]
            candidate = round((raw - now.timestamp()) / 3600)
            residual_age = now.timestamp() - (raw - candidate * 3600)
            if -14 <= candidate <= 14 and 0 <= residual_age <= maximum_age:
                candidates.append(candidate)
        if len(candidates) < 2:
            raise RuntimeError("Broker UTC offset could not be verified across at least two fresh symbols")
        offset, count = Counter(candidates).most_common(1)[0]
        if count < 2:
            raise RuntimeError("Broker UTC offset lacks cross-symbol consensus")
        return offset

    def candles(self, symbol: str, start: datetime, end: datetime, broker_offset_hours: int = 0) -> list[Candle]:
        return self.timeframe_candles(
            symbol, mt5.TIMEFRAME_M15, start, end, broker_offset_hours)

    def timeframe_candles(self, symbol: str, timeframe: int, start: datetime, end: datetime,
                          broker_offset_hours: int = 0) -> list[Candle]:
        """Read any approved historical timeframe without widening the trading boundary."""
        shift = timedelta(hours=broker_offset_hours)
        rows = mt5.copy_rates_range(symbol, timeframe, start + shift, end + shift)
        if rows is None:
            raise RuntimeError(f"Candles unavailable for {symbol}: {mt5.last_error()}")
        return [Candle(datetime.fromtimestamp(int(r["time"]), timezone.utc) - shift, float(r["open"]),
                       float(r["high"]), float(r["low"]), float(r["close"]), int(r["tick_volume"])) for r in rows]

    def m5_candles(self, symbol: str, start: datetime, end: datetime,
                   broker_offset_hours: int = 0) -> list[Candle]:
        return self.timeframe_candles(symbol, mt5.TIMEFRAME_M5, start, end, broker_offset_hours)

    def h4_candles(self, symbol: str, start: datetime, end: datetime,
                   broker_offset_hours: int = 0) -> list[Candle]:
        return self.timeframe_candles(symbol, mt5.TIMEFRAME_H4, start, end, broker_offset_hours)

    def h1_candles(self, symbol: str, start: datetime, end: datetime,
                   broker_offset_hours: int = 0) -> list[Candle]:
        """Read-only H1 history used by research bias classification."""
        shift = timedelta(hours=broker_offset_hours)
        rows = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start + shift, end + shift)
        if rows is None:
            raise RuntimeError(f"H1 candles unavailable for {symbol}: {mt5.last_error()}")
        return [Candle(datetime.fromtimestamp(int(r["time"]), timezone.utc) - shift, float(r["open"]),
                       float(r["high"]), float(r["low"]), float(r["close"]), int(r["tick_volume"])) for r in rows]

    def daily_candles(self, symbol: str, start: datetime, end: datetime,
                      broker_offset_hours: int = 0) -> list[Candle]:
        """Read-only daily history used for volatility-adjusted research bounds."""
        shift = timedelta(hours=broker_offset_hours)
        rows = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_D1, start + shift, end + shift)
        if rows is None:
            raise RuntimeError(f"Daily candles unavailable for {symbol}: {mt5.last_error()}")
        return [Candle(datetime.fromtimestamp(int(r["time"]), timezone.utc) - shift,
                       float(r["open"]), float(r["high"]), float(r["low"]),
                       float(r["close"]), int(r["tick_volume"])) for r in rows]

    def loss_for_one_lot(self, symbol: str, side: str, entry: float, stop: float) -> float | None:
        action = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        profit = mt5.order_calc_profit(action, symbol, 1.0, entry, stop)
        return None if profit is None else abs(float(profit))

    def positions(self) -> list[dict[str, Any]]:
        return [p._asdict() for p in (mt5.positions_get() or ())]

    def orders(self) -> list[dict[str, Any]]:
        return [o._asdict() for o in (mt5.orders_get() or ())]

    def deals(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        return [d._asdict() for d in (mt5.history_deals_get(start, end) or ())]

    def historical_spread(self, symbol: str, timestamp_utc: datetime,
                          broker_offset_hours: int = 0,
                          window_seconds: int = 60) -> float | None:
        """Median positive bid/ask spread around a historical UTC timestamp."""
        shift = timedelta(hours=broker_offset_hours)
        center = timestamp_utc + shift
        rows = mt5.copy_ticks_range(
            symbol, center - timedelta(seconds=window_seconds),
            center + timedelta(seconds=window_seconds), mt5.COPY_TICKS_INFO)
        if rows is None:
            return None
        spreads = [float(row["ask"] - row["bid"]) for row in rows
                   if float(row["ask"]) > float(row["bid"])]
        return median(spreads) if spreads else None
