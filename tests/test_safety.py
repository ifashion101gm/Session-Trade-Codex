import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from session_strategy import mt5_gateway
from session_strategy.mt5_gateway import MT5ReadOnlyGateway


class SafetyTests(unittest.TestCase):
    def test_gateway_exposes_no_mutating_methods(self):
        names = set(dir(MT5ReadOnlyGateway))
        forbidden = {"order_send", "order_check", "position_close", "order_delete", "modify_position", "login"}
        self.assertFalse(names & forbidden)
        source = inspect.getsource(MT5ReadOnlyGateway)
        self.assertNotIn("mt5.order_send", source)
        self.assertNotIn("mt5.login", source)

    def test_no_forbidden_mt5_call_appears_anywhere_in_the_package(self):
        """The read-only boundary covers the whole package, not just the gateway."""
        package = Path(mt5_gateway.__file__).parent
        offenders = []
        for path in package.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for name in mt5_gateway.FORBIDDEN_MT5_CALLS:
                if f"mt5.{name}" in text:
                    offenders.append(f"{path.name}:{name}")
        self.assertEqual(offenders, [], f"order-mutating MT5 calls found: {offenders}")

    def test_research_validator_has_no_broker_gateway_import(self):
        source = (Path(mt5_gateway.__file__).parent / "research_validator.py").read_text(
            encoding="utf-8")
        self.assertNotIn("MetaTrader5", source)
        self.assertNotIn("mt5_gateway", source)
        self.assertNotIn("order_send", source)

    def test_refined_hybrid_validator_has_no_execution_gateway(self):
        source = (Path(mt5_gateway.__file__).parent / "refined_hybrid_validator.py").read_text(
            encoding="utf-8")
        for forbidden in ("MetaTrader5", "mt5_gateway", "order_send", "Binance", "Bybit"):
            self.assertNotIn(forbidden, source)

    def test_production_candidate_validator_has_no_execution_gateway(self):
        source = (Path(mt5_gateway.__file__).parent /
                  "production_candidate_validator.py").read_text(encoding="utf-8")
        for forbidden in ("MetaTrader5", "mt5_gateway", "order_send", "Binance", "Bybit"):
            self.assertNotIn(forbidden, source)
        refined = (Path(mt5_gateway.__file__).parent / "refined_hybrid_validator.py").read_text(
            encoding="utf-8")
        self.assertNotIn("MetaTrader5", refined)
        self.assertNotIn("mt5_gateway", refined)
        self.assertNotIn("order_send", refined)

    def test_read_only_assertion_fails_closed_if_a_mutator_is_added(self):
        with patch.object(MT5ReadOnlyGateway, "order_send", lambda self: None, create=True):
            with self.assertRaises(RuntimeError) as ctx:
                MT5ReadOnlyGateway._assert_read_only()
        self.assertIn("Read-only boundary violated", str(ctx.exception))

    def test_zero_spread_tick_is_refetched_once(self):
        zero = SimpleNamespace(bid=1.1, ask=1.1, time=100)
        refreshed = SimpleNamespace(bid=1.1, ask=1.10002, time=101)
        with patch.object(mt5_gateway.mt5, "symbol_info_tick", side_effect=[zero, refreshed]) as fetch, \
             patch.object(mt5_gateway.time, "sleep") as sleep:
            tick = MT5ReadOnlyGateway().tick("EURUSD")
        self.assertEqual(fetch.call_count, 2)
        sleep.assert_called_once_with(0.5)
        self.assertGreater(tick["ask"], tick["bid"])

    def test_persistent_zero_spread_remains_zero_for_fail_closed_gate(self):
        zero = SimpleNamespace(bid=1.1, ask=1.1, time=100)
        with patch.object(mt5_gateway.mt5, "symbol_info_tick", return_value=zero) as fetch, \
             patch.object(mt5_gateway.time, "sleep"):
            tick = MT5ReadOnlyGateway().tick("EURUSD")
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(tick["ask"] - tick["bid"], 0)

    def test_persistent_zero_spread_is_logged_as_dropped(self):
        zero = SimpleNamespace(bid=1.1, ask=1.1, time=100)
        with patch.object(mt5_gateway.mt5, "symbol_info_tick", return_value=zero), \
             patch.object(mt5_gateway.time, "sleep"), \
             self.assertLogs("session_strategy.mt5_gateway", "WARNING") as logs:
            MT5ReadOnlyGateway().tick("EURUSD")
        self.assertTrue(any("quote_dropped" in message for message in logs.output))


if __name__ == "__main__":
    unittest.main()
