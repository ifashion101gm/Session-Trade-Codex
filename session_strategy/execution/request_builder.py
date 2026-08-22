from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

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
        """
        if not self.risk.passed:
            raise RuntimeError(f"Cannot build request: risk check failed – {self.risk.reason_code}")

        price = self._price_for_order()
        # MT5 constants – using the stub's attributes where available.
        try:
            action = 0  # placeholder for BUY/SELL constant – real code uses mt5.ORDER_TYPE_BUY/SELL
            if self.intent.direction == "LONG":
                action = 0  # mt5.ORDER_TYPE_BUY
            else:
                action = 1  # mt5.ORDER_TYPE_SELL
        except Exception:
            action = 0

        request: dict = {
            "action": action,
            "symbol": self.intent.symbol,
            "volume": self.risk.normalized_volume,
            "order_type": 0,  # market order by default – could be derived from entry_type
            "price": price,
            "sl": self.intent.stop_price,
            "tp": self.intent.target_price,
            "deviation": 10,
            "magic": 123456,
            "comment": f"{self.intent.strategy_id}:{self.intent.strategy_version}",
            "type_time": 0,
            "type_filling": 0,
        }
        logger.debug("Built MT5 request: %s", request)
        return request
