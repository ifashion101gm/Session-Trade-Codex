"""Controlled DEMO execution harness -- tests BROKER EXECUTION INFRASTRUCTURE
independently of STRATEGY-TIMED EXECUTION.

Per the phased hardening plan (2026-08-25, see STATUS.md): whether the broker
accepts a well-formed order, at what retcode, with what fill behavior, is a
different question from whether ASIAN_SESSION_V1 currently has an accepted
signal. Waiting for the market to produce a real signal before ever touching
order_check/order_send conflates the two and means broker-infrastructure bugs
(like the RequestBuilder direction/type bug found and fixed 2026-08-25) can
only be found live, in the one place least convenient to find them.

This harness builds a deliberately synthetic TradeIntent -- clearly labeled
TEST_EXECUTION / NOT_STRATEGY_SIGNAL in its reason_code and MT5 comment, tiny
fixed volume, a stop far enough from the live price to be valid but placed as
a LIMIT well away from market so it will NOT fill by accident -- and runs it
through the exact same pipeline (validate_intent, RiskSupervisor,
RequestBuilder, order_check, and with --send, order_send + reconcile_position)
that the real strategy signal path uses. It never calls analyze() and is not
gated by G16_EXECUTION_WINDOW or any other strategy timing gate.

Safety
------
- Same three-switch requirement for an actual order_send as
  execute_session_signal.py: --send flag, ALLOW_ORDER_SUBMISSION=true,
  ALLOW_ONE_DEMO_ORDER=true.
- Refuses on anything but a demo account.
- Entry price is placed a configurable distance from the current market price
  (default 50 pips) specifically so a LIMIT test order will not fill on its
  own during the harness run -- the point is to test order_check/order_send
  mechanics and reconciliation, not to actually take a market position.
- Uses a distinct magic number (999999) so it can never be confused with a
  real ASIAN_SESSION_V1 signal in the ledger or in broker history.

Usage
-----
    python scripts/test_demo_execution_harness.py --symbol EURUSD              # order_check only
    ALLOW_ORDER_SUBMISSION=true ALLOW_ONE_DEMO_ORDER=true \\
        python scripts/test_demo_execution_harness.py --symbol EURUSD --send   # + order_send + reconcile
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.config import load_config, allow_order_submission  # noqa: E402
from session_strategy.mt5_gateway import MT5ExecutionGateway  # noqa: E402
from session_strategy.execution.models import TradeIntent, ValidationResult  # noqa: E402
from session_strategy.execution.validator import validate_intent  # noqa: E402
from session_strategy.execution.risk_supervisor import RiskSupervisor  # noqa: E402
from session_strategy.execution.request_builder import RequestBuilder  # noqa: E402
from session_strategy.execution.ledger import ExecutionLedger  # noqa: E402
from session_strategy.execution.reconciliation import (  # noqa: E402
    execution_already_committed, reconcile_position,
)

TEST_MAGIC = 999999  # distinct from ASIAN_SESSION_V1_MAGIC (123456) -- never confusable
LEDGER_PATH = ROOT / "data" / "execution_ledger.sqlite3"


def build_test_intent(symbol: str, direction: str, mid_price: float, pip: float,
                      distance_pips: float) -> TradeIntent:
    """A synthetic, clearly-labeled TradeIntent for infrastructure testing.

    LIMIT entry placed `distance_pips` away from the current mid price, on
    the side that will NOT be immediately marketable, so order_check can
    validate it without order_send filling it instantly against a real
    strategy assumption -- this harness is about proving the pipe works, not
    about taking a directional bet.
    """
    now = datetime.now(timezone.utc)
    distance = distance_pips * pip
    if direction == "LONG":
        entry = round(mid_price - distance, 5)
        stop = round(entry - 20 * pip, 5)
        target = round(entry + 30 * pip, 5)
    else:
        entry = round(mid_price + distance, 5)
        stop = round(entry + 20 * pip, 5)
        target = round(entry - 30 * pip, 5)

    return TradeIntent(
        strategy_id="TEST_EXECUTION_HARNESS",
        strategy_version="1.0",
        symbol=symbol,
        reference_session="TEST_EXECUTION",
        reference_start=now - timedelta(hours=1),
        reference_end=now,
        reference_high=mid_price + distance,
        reference_low=mid_price - distance,
        reference_range=2 * distance,
        regime="RANGE",
        setup="TEST_EXECUTION",
        direction=direction,
        signal_time=now,
        signal_price=mid_price,
        entry_type="LIMIT",
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        risk_fraction=0.001,  # deliberately tiny -- infrastructure test, not a real risk decision
        reason_code="TEST_EXECUTION,NOT_STRATEGY_SIGNAL",
        entry_contract_signed=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--direction", choices=("LONG", "SHORT"), default="LONG")
    ap.add_argument("--distance-pips", type=float, default=50.0,
                     help="How far from market to place the test LIMIT (default 50 pips).")
    ap.add_argument("--config", default=str(ROOT / "config" / "strategy.yaml"))
    ap.add_argument("--ledger", default=str(LEDGER_PATH))
    ap.add_argument("--send", action="store_true",
                     help="Attempt real order_send (requires ALLOW_ORDER_SUBMISSION + ALLOW_ONE_DEMO_ORDER).")
    args = ap.parse_args()

    config = load_config(args.config)
    if config.trading_mode != "demo":
        print(json.dumps({"error": f"trading_mode={config.trading_mode!r}, not demo; refusing"}, indent=2))
        return 1

    ledger = ExecutionLedger(args.ledger)
    try:
        with MT5ExecutionGateway("demo", config.execution_permissions) as gateway:
            account = gateway.account()
            if account.account_type != "demo":
                print(json.dumps({"error": f"connected account is {account.account_type!r}, not demo; refusing"}, indent=2))
                return 1

            symbol = config.resolve_symbol(args.symbol)
            broker = config.broker_symbol(symbol)
            tick = gateway.tick(broker)
            spec = gateway.symbol_spec(broker)
            pip = spec.point * (10 if spec.digits in (3, 5) else 1)
            mid = (tick["bid"] + tick["ask"]) / 2

            intent = build_test_intent(symbol, args.direction, mid, pip, args.distance_pips)
            sig_id = f"test-{uuid.uuid4().hex[:12]}"
            attempt_id = sig_id

            committed, reason = execution_already_committed(ledger, gateway, sig_id, symbol, TEST_MAGIC)
            if committed:
                # Shouldn't happen (sig_id is fresh every run) but the gate is universal by design.
                print(json.dumps({"execution": "DUPLICATE_BLOCKED", "reason": reason}, indent=2))
                return 1

            validation = validate_intent(intent)
            if validation != ValidationResult.SUCCESS:
                print(json.dumps({"stage": "VALIDATE_INTENT", "result": validation.value}, indent=2))
                return 1

            risk = RiskSupervisor(config=config).evaluate(intent, gateway)
            if not risk.passed:
                print(json.dumps({
                    "stage": "RISK_SUPERVISOR", "result": risk.reason_code.value, "message": risk.message,
                }, indent=2))
                return 1

            request = RequestBuilder(intent=intent, risk=risk).build()
            request["magic"] = TEST_MAGIC
            # MT5 rejects request["comment"] outright above ~31 chars (found live,
            # 2026-08-25: "Invalid comment argument" on a 35-char string) -- kept short.
            request["comment"] = "TEST_EXEC_NO_SIGNAL"
            ledger.prepare(sig_id, attempt_id, symbol, intent.direction, request)

            check_result = gateway.order_check(request)
            ledger.mark_order_check(sig_id, check_result.get("retcode"), check_result.get("comment"))
            print(json.dumps({
                "stage": "ORDER_CHECK",
                "signal_id": sig_id,
                "retcode": check_result.get("retcode"),
                "comment": check_result.get("comment"),
                "request": {k: v for k, v in request.items()},
                "normalized_volume": risk.normalized_volume,
                "mid_price": mid, "pip_size": pip,
            }, indent=2, default=str))

            if not args.send:
                print(json.dumps({"execution": "CHECK_ONLY", "signal_id": sig_id}, indent=2))
                return 0

            if not allow_order_submission():
                print(json.dumps({"execution": "REFUSED", "reason": "ALLOW_ORDER_SUBMISSION not set"}, indent=2))
                return 1
            if os.environ.get("ALLOW_ONE_DEMO_ORDER", "").lower() not in ("true", "1", "yes"):
                print(json.dumps({"execution": "REFUSED", "reason": "ALLOW_ONE_DEMO_ORDER not set"}, indent=2))
                return 1
            if check_result.get("retcode") != 0:
                print(json.dumps({"execution": "REFUSED", "reason": "order_check did not return 0"}, indent=2))
                return 1

            ledger.mark_send_requested(sig_id)
            send_result = gateway.order_send(request)
            outcome = reconcile_position(gateway, ledger, sig_id, send_result)
            print(json.dumps({"execution": "SUBMITTED", "signal_id": sig_id, **outcome}, indent=2, default=str))
            return 0 if outcome.get("outcome") in (
                "CONFIRMED", "CONFIRMED_VIA_DEAL_HISTORY", "PENDING_ORDER_CONFIRMED") else 1
    finally:
        ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
