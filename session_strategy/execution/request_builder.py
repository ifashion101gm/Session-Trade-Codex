from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

import MetaTrader5 as mt5

from .models import TradeIntent, ExecutableOrder, RiskResult

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class RequestBuilder:
    """Build a full MT5 order request dictionary.

    The builder combines a validated :class:`TradeIntent` with the result of
    :class:`RiskResult` to produce an :class:`ExecutableOrder` compatible with
    ``MetaTrader5``. It also separates the *signal* price from the *entry* price
    according to the intent's ``entry_type``.
    """

    intent: TradeIntent
    risk: RiskResult

    def _price_for_order(self) -> float:
        """Return the price to use for the MT5 request.

        For market orders the entry price is the signal price; for limit orders
        it is the explicitly supplied ``entry_price``.
        """
        if self.intent.entry_type == "MARKET":
            return self.intent.signal_price
        if self.intent.entry_price is not None:
            return self.intent.entry_price
        raise ValueError("Entry price required for LIMIT order but not provided")

    def build(self) -> dict:
        """Construct the MT5 order dictionary.

        The dictionary follows the structure expected by ``MetaTrader5.order_send``
        and ``order_check``. Volume is taken from the normalized volume calculated
        by the risk supervisor. ``sl`` and ``tp`` use the stop and target prices
        from the intent.

        FIXED 2026-08-25 (found during execution-hardening review, before any
        live order_check/order_send was attempted): the previous version set
        ``request["action"]`` to the BUY/SELL indicator (0/1) instead of an
        MT5 ``TRADE_ACTION_*`` constant, and hard-coded ``order_type`` to 0
        (``ORDER_TYPE_BUY``) UNCONDITIONALLY -- every order, regardless of
        ``intent.direction`` or ``intent.entry_type``, would have been
        submitted as a market BUY. ``action=0`` is not a valid
        ``TRADE_ACTION_*`` value at all, so the most likely outcome was an
        immediate broker rejection at ``order_check`` -- but a bug this
        central to correctness must not be assumed benign, and is fixed
        here rather than discovered live.
        """
        if not self.risk.passed:
            raise RuntimeError(f"Cannot build request: risk check failed – {self.risk.reason_code}")

        price = self._price_for_order()
        is_market = self.intent.entry_type == "MARKET"
        is_long = self.intent.direction == "LONG"

        action = mt5.TRADE_ACTION_DEAL if is_market else mt5.TRADE_ACTION_PENDING
        if is_market:
            order_type = mt5.ORDER_TYPE_BUY if is_long else mt5.ORDER_TYPE_SELL
        else:
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if is_long else mt5.ORDER_TYPE_SELL_LIMIT

        request: dict = {
            "action": action,
            "symbol": self.intent.symbol,
            "volume": self.risk.normalized_volume,
            "type": order_type,
            "price": price,
            "sl": self.intent.stop_price,
            "tp": self.intent.target_price,
            "deviation": 10,
            "magic": 123456,
            "comment": f"{self.intent.strategy_id}:{self.intent.strategy_version}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        logger.debug("Built MT5 request: %s", request)
        return request
