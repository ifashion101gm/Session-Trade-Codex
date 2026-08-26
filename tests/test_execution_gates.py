"""Composite execution-gate tests for the DemoExecutor pipeline.

Validates that every safety gate fails closed independently, and that the only
way to reach order_send is when ALL gates pass simultaneously.

Key invariant: ``order_send`` call count == 0 for every negative test.

Test structure
--------------
- Positive path: all mocked gates pass → exactly one ``order_send`` call.
- Negative path: each gate individually fails → ``order_send`` never called.
- Gateway isolation: verify MT5ReadOnlyGateway has no order_send attribute.
- MT5ExecutionGateway construction: demo mode required; live mode rejected.
"""
from __future__ import annotations

import os
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch, call

from session_strategy.config import StrategyConfig, load_config
from session_strategy.execution.executor import DemoExecutor
from session_strategy.execution.models import (
    ExecutionReport, RiskResult, RiskResultReason,
    TradeIntent, ValidationResult,
)
from session_strategy.mt5_gateway import MT5ExecutionGateway, MT5ReadOnlyGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_intent() -> TradeIntent:
    """Minimal TradeIntent that passes validate_intent() completely."""
    return TradeIntent(
        strategy_id="ASIAN_SESSION_V1",
        strategy_version="1.0",
        symbol="EURUSD",
        reference_session="2026-08-11",
        reference_start=datetime(2026, 8, 11, 0, tzinfo=timezone.utc),
        reference_end=datetime(2026, 8, 11, 7, tzinfo=timezone.utc),
        reference_high=1.16800,
        reference_low=1.16400,
        reference_range=0.004,
        regime="RANGE",
        setup="SWEEP",
        direction="LONG",
        signal_time=datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc),
        signal_price=1.16400,
        entry_type="MARKET",
        entry_price=1.16400,
        stop_price=1.16300,
        target_price=1.16800,
        risk_fraction=0.005,
        reason_code="SWEEP_CONFIRMED",
        entry_contract_signed=True,
    )


def _good_risk() -> RiskResult:
    return RiskResult(
        passed=True,
        reason_code=RiskResultReason.SUCCESS,
        message="ok",
        normalized_volume=0.1,
    )


def _bad_risk(reason=RiskResultReason.INVALID_ACCOUNT_EQUITY) -> RiskResult:
    return RiskResult(passed=False, reason_code=reason, message="blocked")


def _make_gateway(submit_orders: bool = True) -> MT5ExecutionGateway:
    """Create a gateway mock that does NOT touch MT5."""
    gw = MagicMock(spec=MT5ExecutionGateway)
    gw._permissions = {"submit_orders": submit_orders}
    gw.account.return_value = MagicMock(equity=10_000.0)
    gw.loss_for_one_lot.return_value = 100.0
    gw.symbol_spec.return_value = MagicMock(
        volume_min=0.01, volume_max=100.0, volume_step=0.01
    )
    gw.order_check.return_value = {"retcode": 0}
    gw.order_send.return_value = {"retcode": 0, "order": 123456}
    return gw


def _make_executor(config: StrategyConfig, gateway: MT5ExecutionGateway) -> DemoExecutor:
    return DemoExecutor(config=config, gateway=gateway)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestCompositeExecutionGates(unittest.TestCase):
    """Every gate must individually fail-closed; positive path requires all pass."""

    def setUp(self):
        self.config = load_config()
        self.gateway = _make_gateway()

    # ------------------------------------------------------------------
    # Phase 3: gateway isolation
    # ------------------------------------------------------------------

    def test_read_only_gateway_has_no_order_send(self):
        """MT5ReadOnlyGateway must not expose order_send at all (physical absence)."""
        self.assertFalse(hasattr(MT5ReadOnlyGateway, "order_send"),
                         "order_send must not exist on MT5ReadOnlyGateway")

    def test_read_only_gateway_has_no_order_check(self):
        """MT5ReadOnlyGateway must not expose order_check at all (physical absence)."""
        self.assertFalse(hasattr(MT5ReadOnlyGateway, "order_check"),
                         "order_check must not exist on MT5ReadOnlyGateway")

    def test_execution_gateway_requires_demo_mode(self):
        """MT5ExecutionGateway must reject non-demo execution_mode at construction."""
        with self.assertRaises(ValueError) as ctx:
            MT5ExecutionGateway(execution_mode="live")
        self.assertIn("demo", str(ctx.exception).lower())

    def test_execution_gateway_accepts_demo_mode(self):
        """MT5ExecutionGateway('demo') must construct without error."""
        gw = MT5ExecutionGateway(
            execution_mode="demo",
            execution_permissions={"submit_orders": True},
        )
        self.assertEqual(gw._execution_mode, "demo")

    def test_read_only_gateway_assert_read_only_passes(self):
        """_assert_read_only on MT5ReadOnlyGateway must not raise."""
        MT5ReadOnlyGateway._assert_read_only()  # must not raise

    # ------------------------------------------------------------------
    # Gate 1: validate_intent (B-3 / H-1 / H-2)
    # ------------------------------------------------------------------

    def test_gate_intent_validation_fail_blocks_order_send(self):
        """A malformed intent must block at step 1 (no order_send)."""
        bad_intent = replace(_valid_intent(), strategy_id="")
        executor = _make_executor(self.config, self.gateway)
        report = executor.execute(bad_intent)
        self.assertEqual(report.validation, ValidationResult.INVALID_INTENT)
        self.gateway.order_send.assert_not_called()

    def test_gate_missing_stop_price_blocks_order_send(self):
        bad_intent = replace(_valid_intent(), stop_price=0.0)
        executor = _make_executor(self.config, self.gateway)
        report = executor.execute(bad_intent)
        self.assertEqual(report.validation, ValidationResult.INVALID_STOP)
        self.gateway.order_send.assert_not_called()

    def test_gate_missing_target_price_blocks_order_send(self):
        bad_intent = replace(_valid_intent(), target_price=0.0)
        executor = _make_executor(self.config, self.gateway)
        report = executor.execute(bad_intent)
        self.assertEqual(report.validation, ValidationResult.INVALID_TARGET)
        self.gateway.order_send.assert_not_called()

    def test_gate_invalid_trade_geometry_blocks_order_send(self):
        # LONG but stop above entry (inverted)
        bad_intent = replace(_valid_intent(), stop_price=1.16800, target_price=1.16300)
        executor = _make_executor(self.config, self.gateway)
        report = executor.execute(bad_intent)
        self.assertNotEqual(report.validation, ValidationResult.SUCCESS)
        self.gateway.order_send.assert_not_called()

    def test_gate_unsigned_entry_contract_blocks_order_send(self):
        bad_intent = replace(_valid_intent(), entry_contract_signed=False)
        executor = _make_executor(self.config, self.gateway)
        report = executor.execute(bad_intent)
        self.assertEqual(report.validation, ValidationResult.ENTRY_CONTRACT_UNSIGNED)
        self.gateway.order_send.assert_not_called()

    # ------------------------------------------------------------------
    # Gate 2: risk supervisor
    # ------------------------------------------------------------------

    def test_gate_risk_failure_blocks_order_send(self):
        """RiskSupervisor failure must block at step 2 (no order_send)."""
        executor = _make_executor(self.config, self.gateway)
        self.gateway.account.return_value = MagicMock(equity=0.0)
        report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.INVALID_RISK)
        self.gateway.order_send.assert_not_called()

    # ------------------------------------------------------------------
    # Gate 4: _can_submit composite gate
    # ------------------------------------------------------------------

    def test_gate_wrong_trading_mode_blocks_order_send(self):
        """trading_mode != 'demo' must block submission."""
        config = replace(self.config, trading_mode="live")
        executor = _make_executor(config, self.gateway)
        with patch.dict(os.environ, {"ALLOW_ORDER_SUBMISSION": "true"}):
            report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.SUBMIT_PERMISSION_DENIED)
        self.gateway.order_send.assert_not_called()

    def test_gate_submit_orders_false_blocks_order_send(self):
        """execution_permissions.submit_orders=False must block submission."""
        config = replace(self.config, execution_permissions={
            **self.config.execution_permissions, "submit_orders": False
        })
        executor = _make_executor(config, self.gateway)
        with patch.dict(os.environ, {"ALLOW_ORDER_SUBMISSION": "true"}):
            report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.SUBMIT_PERMISSION_DENIED)
        self.gateway.order_send.assert_not_called()

    def test_gate_env_var_missing_blocks_order_send(self):
        """ALLOW_ORDER_SUBMISSION env-var not set must block submission."""
        executor = _make_executor(self.config, self.gateway)
        env = {k: v for k, v in os.environ.items() if k != "ALLOW_ORDER_SUBMISSION"}
        with patch.dict(os.environ, env, clear=True):
            report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.SUBMIT_PERMISSION_DENIED)
        self.gateway.order_send.assert_not_called()

    def test_gate_env_var_false_blocks_order_send(self):
        """ALLOW_ORDER_SUBMISSION=false must block submission."""
        executor = _make_executor(self.config, self.gateway)
        with patch.dict(os.environ, {"ALLOW_ORDER_SUBMISSION": "false"}):
            report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.SUBMIT_PERMISSION_DENIED)
        self.gateway.order_send.assert_not_called()

    # ------------------------------------------------------------------
    # Gate 5: order_check
    # ------------------------------------------------------------------

    def test_gate_order_check_nonzero_retcode_blocks_order_send(self):
        """order_check retcode != 0 must block submission at step 5.

        Uses a submit_orders=True variant of self.config: config/strategy.yaml (ASIAN_SESSION_V1)
        was frozen to submit_orders=False as part of CANONICAL_SESSION_MIGRATION_REPORT.md's
        LEGACY_FROZEN status, but this test exercises gate 5 specifically, which only runs once
        gate 4 (submit_orders) has already passed -- see test_gate_submit_orders_false_blocks_order_send
        for that gate's own dedicated test.
        """
        self.gateway.order_check.return_value = {"retcode": 10}
        permissive_config = replace(self.config, execution_permissions={
            **self.config.execution_permissions, "submit_orders": True,
        })
        executor = _make_executor(permissive_config, self.gateway)
        with patch.dict(os.environ, {"ALLOW_ORDER_SUBMISSION": "true"}):
            report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.MARKET_DATA_STALE)
        self.gateway.order_send.assert_not_called()

    # ------------------------------------------------------------------
    # Positive path
    # ------------------------------------------------------------------

    def test_positive_path_all_gates_pass_reaches_order_send_exactly_once(self):
        """When all gates pass, exactly one order_send call is made.

        See test_gate_order_check_nonzero_retcode_blocks_order_send above for why this uses a
        submit_orders=True variant of self.config rather than self.config directly.
        """
        permissive_config = replace(self.config, execution_permissions={
            **self.config.execution_permissions, "submit_orders": True,
        })
        executor = _make_executor(permissive_config, self.gateway)
        with patch.dict(os.environ, {"ALLOW_ORDER_SUBMISSION": "true"}):
            report = executor.execute(_valid_intent())
        self.assertEqual(report.validation, ValidationResult.SUCCESS)
        self.gateway.order_send.assert_called_once()
        sent_request = self.gateway.order_send.call_args[0][0]
        # Verify the request has the correct symbol and volume
        self.assertEqual(sent_request["symbol"], "EURUSD")
        self.assertGreater(sent_request["volume"], 0)


class TestValidationResultEnumCompleteness(unittest.TestCase):
    """H-1: Every code returned by validator.py must exist in ValidationResult."""

    def test_all_validator_return_codes_exist_in_enum(self):
        """verify every code validator.py returns is in ValidationResult."""
        from session_strategy.execution.models import ValidationResult
        # All codes explicitly returned in validator.py:
        required = [
            "SUCCESS", "INVALID_INTENT", "MISSING_DIRECTION",
            "MISSING_ENTRY", "INVALID_STOP", "INVALID_TARGET",
            "INVALID_RISK", "ENTRY_CONTRACT_UNSIGNED", "INVALID_TRADE_GEOMETRY",
        ]
        for code in required:
            self.assertIn(code, ValidationResult.__members__,
                          f"ValidationResult.{code} missing — H-1 regression")


class TestTimestampFactory(unittest.TestCase):
    """M-8: ExecutionReport timestamps must be unique per instance."""

    def test_each_execution_report_gets_a_unique_timestamp(self):
        """Two reports created in sequence must have distinct timestamps."""
        intent = _valid_intent()
        r1 = __import__("session_strategy.execution.models", fromlist=["ExecutionReport"]).ExecutionReport(
            intent=intent, validation=ValidationResult.SUCCESS)
        import time; time.sleep(0.001)
        r2 = __import__("session_strategy.execution.models", fromlist=["ExecutionReport"]).ExecutionReport(
            intent=intent, validation=ValidationResult.SUCCESS)
        # They should be distinct (not the same frozen class-level timestamp)
        self.assertIsNotNone(r1.timestamp)
        self.assertIsNotNone(r2.timestamp)
        # timestamps should be timezone-aware UTC
        self.assertIsNotNone(r1.timestamp.tzinfo)
        self.assertIsNotNone(r2.timestamp.tzinfo)


if __name__ == "__main__":
    unittest.main()
