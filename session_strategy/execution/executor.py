from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .models import ExecutionReport, ValidationResult, TradeIntent
from .validator import validate_intent
from .risk_supervisor import RiskSupervisor
from .request_builder import RequestBuilder
from ..mt5_gateway import MT5ExecutionGateway
from ..config import StrategyConfig, allow_order_submission

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoExecutor:
    """Controlled DEMO execution layer.

    This component orchestrates the full pipeline from a validated ``TradeIntent``
    through risk sizing, request building, broker‑side dry‑run checks and finally
    the simulated order submission.  All gates described in the architecture are
    enforced here.

    Attributes
    ----------
    config:
        Loaded strategy configuration.  ``trading_mode`` must be ``"demo"`` and
        ``execution_permissions["submit_orders"]`` must be ``True`` for orders
        to reach the gateway.
    gateway:
        Must be an :class:`MT5ExecutionGateway` — the read-only gateway does not
        expose ``order_send`` or ``order_check`` at all, so passing one here is a
        type error that surfaces immediately.
    """

    config: StrategyConfig
    gateway: MT5ExecutionGateway

    def _can_submit(self) -> bool:
        """Composite gate that decides whether an order may be sent.

        All conditions must be True; the function is fail-closed (any failure
        returns False immediately after logging the specific block reason).

        Gates:
        1. ``config.trading_mode`` must be ``"demo"`` — no live path exists.
        2. ``execution_permissions["submit_orders"]`` must be ``True`` in config.
        3. ``allow_order_submission()`` — env-var ``ALLOW_ORDER_SUBMISSION`` must
           be set to a truthy value (``"true"`` / ``"1"`` / ``"yes"``).
        """
        # Gate 1: mode must be demo
        if self.config.trading_mode != "demo":
            logger.warning(
                "submission_blocked reason=trading_mode_not_demo mode=%s",
                self.config.trading_mode,
            )
            return False

        # Gate 2: execution_permissions.submit_orders must be explicit True
        if not self.config.execution_permissions.get("submit_orders"):
            logger.warning("submission_blocked reason=execution_permissions_submit_orders_false")
            return False

        # Gate 3: env-var ALLOW_ORDER_SUBMISSION must be set
        if not allow_order_submission():
            logger.warning(
                "submission_blocked reason=ALLOW_ORDER_SUBMISSION_env_var_not_set"
            )
            return False

        return True

    def execute(self, intent: TradeIntent) -> ExecutionReport:
        """Run the full DEMO execution pipeline for a single ``TradeIntent``.

        Returns an :class:`ExecutionReport` containing the validation outcome and
        any broker‑side return codes.

        Pipeline
        --------
        1. Broker-neutral validation (``validate_intent``).
        2. Risk sizing (``RiskSupervisor``).
        3. MT5 request construction (``RequestBuilder``).
        4. Composite submission gate (``_can_submit``).
        5. Broker-side dry-run (``order_check``).
        6. Order submission (``order_send``, demo only).
        """
        # 1️⃣ Validate intent (broker-neutral)
        validation = validate_intent(intent)
        if validation != ValidationResult.SUCCESS:
            logger.info("intent_validation_failed code=%s", validation)
            return ExecutionReport(intent=intent, validation=validation)

        # 2️⃣ Risk sizing
        risk_supervisor = RiskSupervisor(config=self.config)
        risk = risk_supervisor.evaluate(intent, self.gateway)
        if not risk.passed:
            logger.info("risk_supervisor_failed reason=%s", risk.reason_code)
            return ExecutionReport(intent=intent, validation=ValidationResult.INVALID_RISK)

        # 3️⃣ Build MT5 request
        builder = RequestBuilder(intent=intent, risk=risk)
        request = builder.build()

        # 4️⃣ Composite submission gate
        if not self._can_submit():
            logger.info("execution_blocked_by_composite_gate")
            return ExecutionReport(
                intent=intent, validation=ValidationResult.SUBMIT_PERMISSION_DENIED
            )

        # 5️⃣ Dry-run order check
        check_result = self.gateway.order_check(request)
        if check_result.get("retcode") != 0:
            logger.warning("order_check_failed retcode=%s", check_result.get("retcode"))
            return ExecutionReport(
                intent=intent,
                validation=ValidationResult.MARKET_DATA_STALE,
                order_check_retcode=check_result.get("retcode"),
            )

        # 6️⃣ Submit (demo only — order_send is only present on MT5ExecutionGateway)
        send_result = self.gateway.order_send(request)
        retcode = send_result.get("retcode") if isinstance(send_result, dict) else None
        logger.info("demo_order_submitted intent=%s retcode=%s", intent, retcode)
        return ExecutionReport(
            intent=intent,
            validation=ValidationResult.SUCCESS,
            volume=risk.normalized_volume,
            order_check_retcode=check_result.get("retcode"),
            order_send_retcode=retcode,
        )
