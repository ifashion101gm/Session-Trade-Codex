from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .models import ExecutionReport, ValidationResult, TradeIntent
from .validator import Validator
from .risk_supervisor import RiskSupervisor
from .request_builder import RequestBuilder
from ..mt5_gateway import MT5ReadOnlyGateway
from ..config import StrategyConfig, load_config

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class DemoExecutor:
    """Controlled DEMO execution layer.

    This component orchestrates the full pipeline from a validated ``TradeIntent``
    through risk sizing, request building, broker‑side dry‑run checks and finally
    the simulated order submission. All gates described in the architecture are
    enforced here.
    """

    config: StrategyConfig
    gateway: MT5ReadOnlyGateway
    validator: Validator = Validator()
    risk_supervisor: RiskSupervisor = RiskSupervisor(config=load_config())

    def _can_submit(self) -> bool:
        """Composite gate that decides whether an order may be sent.

        The conditions reflect the design contract:
        - trading is globally enabled
        - mode is ``demo``
        - explicit permission ``submit_orders`` is granted
        - the gateway permissions have been asserted via ``_assert_permissions``
        """
        if not self.config.trading_enabled:
            logger.debug("Trading disabled via config")
            return False
        if getattr(self.config, "TRADING_MODE", "demo") != "demo":
            logger.debug("TRADING_MODE not demo: %s", getattr(self.config, "TRADING_MODE", None))
            return False
        permissions = getattr(self.gateway, "_permissions", {})
        if not permissions.get("submit_orders"):
            logger.debug("Gateway permission submit_orders not granted")
            return False
        return True

    def execute(self, intent: TradeIntent) -> ExecutionReport:
        """Run the full DEMO execution pipeline for a single ``TradeIntent``.

        Returns an :class:`ExecutionReport` containing the validation outcome and
        any broker‑side return codes.
        """
        # 1️⃣ Validate intent (broker‑neutral)
        validation = self.validator.validate(intent)
        if validation != ValidationResult.SUCCESS:
            logger.info("TradeIntent validation failed: %s", validation)
            return ExecutionReport(intent=intent, validation=validation)

        # 2️⃣ Risk sizing
        risk = self.risk_supervisor.evaluate(intent, self.gateway)
        if not risk.passed:
            logger.info("RiskSupervisor failed: %s", risk.reason_code)
            return ExecutionReport(intent=intent, validation=ValidationResult.INVALID_RISK)

        # 3️⃣ Build MT5 request
        builder = RequestBuilder(intent=intent, risk=risk)
        request = builder.build()

        # 4️⃣ Composite submission gate
        if not self._can_submit():
            logger.info("Execution blocked by composite gate")
            return ExecutionReport(intent=intent, validation=ValidationResult.SUBMIT_PERMISSION_DENIED)

        # 5️⃣ Dry‑run order check
        check_result = self.gateway.order_check(request)
        if check_result.get("retcode") != 0:
            logger.warning("order_check failed: %s", check_result)
            return ExecutionReport(
                intent=intent,
                validation=ValidationResult.MARKET_DATA_STALE,
                order_check_retcode=check_result.get("retcode"),
            )

        # 6️⃣ Submit (demo only – actual send is a no‑op in the read‑only gateway)
        self.gateway.order_send(request)
        logger.info("Demo order submitted for intent %s", intent)
        return ExecutionReport(
            intent=intent,
            validation=ValidationResult.SUCCESS,
            volume=risk.normalized_volume,
            order_check_retcode=check_result.get("retcode"),
        )
