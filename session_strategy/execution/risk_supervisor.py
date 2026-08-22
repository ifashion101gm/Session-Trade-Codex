from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

from .models import TradeIntent, RiskResult, RiskResultReason
from ..config import load_config, StrategyConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskSupervisor:
    """Calculate safe position size based on live account equity and configured risk.

    The supervisor reads the current account equity from the provided MT5 gateway,
    applies the configured ``risk_percent_per_trade`` (default 1 %), and derives a
    maximum monetary loss budget. It then uses the broker's per‑lot loss estimate to
    compute a raw lot size, which is normalized to the broker's volume constraints.

    Failure reasons are returned via ``RiskResultReason`` and a descriptive message.
    """

    config: StrategyConfig

    def _equity(self, gateway) -> float:
        """Retrieve live equity from the gateway's ``account`` method.
        Returns 0.0 on unexpected failures to keep the function total‑failure safe.
        """
        try:
            equity = gateway.account().equity
            logger.debug("Live equity fetched: %s", equity)
            return float(equity)
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Failed to obtain account equity: %s", exc)
            return 0.0

    def evaluate(self, intent: TradeIntent, gateway) -> RiskResult:
        """Perform the risk sizing workflow.

        Returns a ``RiskResult`` indicating success or a concrete failure reason.
        """
        # 1. Live equity
        equity = self._equity(gateway)
        if equity <= 0:
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.INVALID_ACCOUNT_EQUITY,
                message="Unable to obtain positive account equity.",
            )

        # 2. Configured risk fraction (percentage → fraction)
        risk_fraction = self.config.risk_percent_per_trade / 100.0
        if risk_fraction <= 0:
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.INVALID_RISK_FRACTION,
                message="Configured risk fraction must be positive.",
            )
        risk_budget = equity * risk_fraction
        logger.debug("Risk budget (equity * fraction): %s", risk_budget)

        # 3. Determine entry reference price
        entry_price = intent.entry_price if intent.entry_price is not None else intent.signal_price
        if entry_price is None or entry_price <= 0:
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.INVALID_ENTRY_PRICE,
                message="Entry price is missing or non‑positive.",
            )

        # 4. Stop distance and per‑lot loss
        if intent.direction == "LONG":
            stop_distance = entry_price - intent.stop_price
        else:  # SHORT
            stop_distance = intent.stop_price - entry_price
        if stop_distance <= 0:
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.ZERO_STOP_DISTANCE,
                message="Stop price does not lie beyond entry in the trade direction.",
            )
        # Use the gateway helper to compute loss for a single lot.
        loss_per_lot = gateway.loss_for_one_lot(intent.symbol, intent.direction, entry_price, intent.stop_price)
        if loss_per_lot is None or loss_per_lot <= 0:
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.INVALID_TICK_VALUE,
                message="Unable to compute loss per lot from broker.",
            )
        logger.debug("Loss per lot: %s", loss_per_lot)

        # 5. Raw volume based on risk budget
        raw_volume = risk_budget / loss_per_lot
        logger.debug("Raw volume before broker constraints: %s", raw_volume)

        # 6. Retrieve symbol metadata for volume limits
        spec = gateway.symbol_spec(intent.symbol)
        if not (spec.volume_min and spec.volume_step):
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.INVALID_VOLUME_MIN,
                message="Broker volume metadata missing.",
            )

        # 7. Normalize volume to step and enforce bounds
        # Floor to nearest step
        step = spec.volume_step
        normalized = (int(raw_volume / step)) * step
        if normalized <= 0:
            # Even after stepping we have no usable volume
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.VOLUME_BELOW_MINIMUM,
                message="Calculated volume below broker minimum step.",
            )
        # Enforce max bound
        if normalized > spec.volume_max:
            normalized = spec.volume_max

        # 8. Verify that the normalized volume respects the minimum volume.
        if normalized < spec.volume_min:
            # Do **not** force up to the minimum – report a dedicated failure.
            return RiskResult(
                passed=False,
                reason_code=RiskResultReason.VOLUME_BELOW_MINIMUM,
                message="Normalized volume would be below broker minimum.",
            )

        estimated_loss = normalized * loss_per_lot
        utilization = (estimated_loss / risk_budget) * 100 if risk_budget else 0

        return RiskResult(
            passed=True,
            reason_code=RiskResultReason.SUCCESS,
            message="Risk sizing succeeded.",
            risk_amount=risk_budget,
            stop_distance=stop_distance,
            raw_volume=raw_volume,
            normalized_volume=normalized,
            estimated_loss_at_stop=estimated_loss,
            risk_utilization=utilization,
        )
