"""Manual trigger for ASIAN_SESSION_V1: analyze a symbol, and if the signal is
accepted, submit ONE order on the demo account with the correct entry and
stop, and a single take-profit at the 5R ceiling (``tp2_5r``).

Scope, deliberately narrow (trader decision, 2026-08-25): this does NOT
automate the strategy's real 4R-partial-close / move-stop-to-breakeven
management step -- that stays manual, exactly as USER_MANUAL.md's `monitor`
command already assumes. It only closes the gap between "analyze produced an
accepted signal" and "an order reaches the broker" for one explicitly
requested symbol, on one explicit invocation. It is not a bot; run it by hand
whenever you want to act on the current signal for that symbol.

Safety
------
- Uses MT5ExecutionGateway with execution_mode="demo" hardcoded -- no live path.
- Refuses if the connected account is not demo, or config.trading_mode != "demo".
- Requires config.execution_permissions.submit_orders == True (already true for
  ASIAN_SESSION_V1 in config/strategy.yaml).
- Without --confirm, ALWAYS dry-runs: prints what would be submitted and stops
  before any order_check/order_send call reaches the broker.
- THREE independent switches must all be true to reach a real order_send:
  the script's own --confirm flag, ALLOW_ORDER_SUBMISSION=true, AND
  ALLOW_ONE_DEMO_ORDER=true. Any one missing fails closed.
- A module-level counter refuses a second order_send within the same process
  invocation, regardless of anything else -- one run, at most one order.

Hardening sequence, phased plan applied 2026-08-25 (see STATUS.md for full detail):
  Phase A (steps 1-7): build_intent()/signal_id() unit tested against a synthetic
  accepted result; duplicate-send protection (now execution_already_committed(),
  in session_strategy/execution/reconciliation.py); --check mode running a REAL
  order_check against the live broker.
  Phase B (this revision): local durable execution ledger
  (session_strategy/execution/ledger.py) written BEFORE order_send, so a crash
  between broker acceptance and local recording can't produce a silent
  duplicate; reconcile_position() independently re-queries the broker after
  order_send rather than trusting the retcode alone.
  A real correctness bug was also found and fixed in this revision:
  RequestBuilder.build() was submitting every order as a market BUY regardless
  of intent.direction/entry_type -- see request_builder.py's docstring.
  Phase C (accepted real signal -> full pipeline), Phase D (4R-partial/
  breakeven/5R management automation), and Phase E (multi-day forward test)
  are not started.

Usage
-----
    python scripts/execute_session_signal.py --symbol EURUSD                    # dry run, no broker call
    python scripts/execute_session_signal.py --symbol EURUSD --check            # + real order_check
    ALLOW_ORDER_SUBMISSION=true ALLOW_ONE_DEMO_ORDER=true \\
        python scripts/execute_session_signal.py --symbol EURUSD --confirm      # submits, once
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.cli import _sync  # noqa: E402
from session_strategy.config import load_config, allow_order_submission  # noqa: E402
from session_strategy.engine import analyze, session_bounds, execution_bounds, filter_window  # noqa: E402
from session_strategy.journal import Journal  # noqa: E402
from session_strategy.mt5_gateway import MT5ExecutionGateway  # noqa: E402
from session_strategy.render import markdown, write_artifacts  # noqa: E402
from session_strategy.execution.models import TradeIntent, ValidationResult  # noqa: E402
from session_strategy.execution.validator import validate_intent  # noqa: E402
from session_strategy.execution.risk_supervisor import RiskSupervisor  # noqa: E402
from session_strategy.execution.request_builder import RequestBuilder  # noqa: E402
from session_strategy.execution.ledger import ExecutionLedger  # noqa: E402
from session_strategy.execution.reconciliation import (  # noqa: E402
    execution_already_committed, reconcile_position,
)

ASIAN_SESSION_V1_MAGIC = 123456  # matches RequestBuilder.build() -- kept in sync manually
LEDGER_PATH = ROOT / "data" / "execution_ledger.sqlite3"

_orders_sent_this_run = 0  # module-level; one script invocation, at most one order_send


def _load_news_calendar(config) -> tuple[list[dict], bool]:
    if not config.news_filter.get("enabled"):
        return [], True
    source = Path(config.news_filter["source"])
    if not source.is_absolute():
        source = ROOT / source
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        events = payload["events"]
        return (events if isinstance(events, list) else []), True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return [], False


def build_intent(result) -> TradeIntent:
    """Map an accepted AnalysisResult onto a single-order TradeIntent.

    target_price is tp2_5r (the 5R ceiling), not tp1_4r/partial_target -- the
    4R partial-close step has no automation to hand off to, so the order is
    given room to run to the full target rather than closing early at 4R.
    """
    regime = "TREND" if "TREND" in (result.session_type or "") else "RANGE"
    signal_price = (result.signal_candle or {}).get("close") or result.entry
    return TradeIntent(
        strategy_id=result.strategy_id,
        strategy_version=result.contract_version,
        symbol=result.symbol,
        reference_session="ASIAN",
        reference_start=result.asian_start,
        reference_end=result.asian_end,
        reference_high=result.asian_high,
        reference_low=result.asian_low,
        reference_range=result.asian_range,
        regime=regime,
        setup=result.setup,
        direction=result.direction,
        signal_time=result.signal_time,
        signal_price=signal_price,
        entry_type="LIMIT",
        entry_price=result.entry,
        stop_price=result.stop_loss,
        target_price=result.tp2_5r,
        risk_fraction=result.risk_fraction,
        reason_code=",".join(result.reason_codes) if result.reason_codes else "SIGNAL_ACCEPTED",
        entry_contract_signed=True,
    )


def signal_id(result) -> str:
    """Deterministic id for the underlying SIGNAL, not the analysis run.

    Two `analyze()` calls against the same reference session that land on the
    same setup/direction must produce the SAME id, even though `analysis_id`
    (a random uuid), bid/ask, and spread differ between runs -- otherwise
    duplicate-send protection could never recognize "we already acted on
    this." Deliberately excludes anything that isn't part of what makes a
    signal a signal: strategy, symbol, the reference session it was read
    from, and the setup/direction it produced.
    """
    basis = "|".join([
        result.strategy_id,
        result.symbol,
        result.trading_date,
        result.asian_start.isoformat() if result.asian_start else "",
        result.setup or "",
        result.direction or "",
    ])
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def dry_broker_check(config, gateway, intent: TradeIntent) -> dict:
    """Run validation + risk sizing + REAL order_check against the live broker
    (no order_send). Returns a dict with the exact retcode, comment, and
    request MT5 handed back, so the broker's own verdict is visible before
    any real submission is attempted."""
    validation = validate_intent(intent)
    if validation != ValidationResult.SUCCESS:
        return {"stage": "VALIDATE_INTENT", "result": validation.value}

    risk = RiskSupervisor(config=config).evaluate(intent, gateway)
    if not risk.passed:
        return {"stage": "RISK_SUPERVISOR", "result": risk.reason_code.value, "message": risk.message}

    request = RequestBuilder(intent=intent, risk=risk).build()
    check_result = gateway.order_check(request)
    return {
        "stage": "ORDER_CHECK",
        "retcode": check_result.get("retcode"),
        "comment": check_result.get("comment"),
        "request": request,
        "normalized_volume": risk.normalized_volume,
    }


def submit_one_order(config, gateway, ledger: ExecutionLedger, sig_id: str,
                     attempt_id: str, intent: TradeIntent) -> dict:
    """The only path that may call order_send. Enforces the one-shot counter,
    writes to the ledger BEFORE order_send (the crash-safety property), and
    reconciles against the broker afterward rather than trusting the retcode.
    """
    global _orders_sent_this_run
    if _orders_sent_this_run >= 1:
        return {"stage": "REFUSED", "reason": "max_orders_this_run=1 already reached this invocation"}

    validation = validate_intent(intent)
    if validation != ValidationResult.SUCCESS:
        return {"stage": "VALIDATE_INTENT", "result": validation.value}

    risk = RiskSupervisor(config=config).evaluate(intent, gateway)
    if not risk.passed:
        return {"stage": "RISK_SUPERVISOR", "result": risk.reason_code.value, "message": risk.message}

    request = RequestBuilder(intent=intent, risk=risk).build()
    ledger.prepare(sig_id, attempt_id, intent.symbol, intent.direction, request)

    check_result = gateway.order_check(request)
    ledger.mark_order_check(sig_id, check_result.get("retcode"), check_result.get("comment"))
    if check_result.get("retcode") != 0:
        return {
            "stage": "ORDER_CHECK", "outcome": "REJECTED",
            "retcode": check_result.get("retcode"), "comment": check_result.get("comment"),
        }

    # The critical write: persisted BEFORE order_send() is called.
    ledger.mark_send_requested(sig_id)
    _orders_sent_this_run += 1

    send_result = gateway.order_send(request)
    reconciliation = reconcile_position(gateway, ledger, sig_id, send_result)
    return {"stage": "SUBMITTED", **reconciliation}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--config", default=str(ROOT / "config" / "strategy.yaml"))
    ap.add_argument("--journal", default=str(ROOT / "data" / "sspf_journal.sqlite3"))
    ap.add_argument("--ledger", default=str(LEDGER_PATH))
    ap.add_argument("--output", default=str(ROOT / "outputs"))
    ap.add_argument("--check", action="store_true",
                     help="Also run a REAL broker-side order_check (no order_send).")
    ap.add_argument("--confirm", action="store_true",
                     help="Attempt real submission. Without this, always dry-run.")
    args = ap.parse_args()

    config = load_config(args.config)
    if config.trading_mode != "demo":
        print(json.dumps({"error": f"trading_mode={config.trading_mode!r}, not demo; refusing"}, indent=2))
        return 1

    journal = Journal(args.journal)
    ledger = ExecutionLedger(args.ledger)
    try:
        try:
            symbol = config.resolve_symbol(args.symbol)
        except KeyError:
            print(json.dumps({"status": "NO_TRADE", "reason_codes": ["SYMBOL_NOT_SUPPORTED"]}, indent=2))
            return 2

        with MT5ExecutionGateway("demo", config.execution_permissions) as gateway:
            account = gateway.account()
            if account.account_type != "demo":
                print(json.dumps({"error": f"connected account is {account.account_type!r}, not demo; refusing"}, indent=2))
                return 1

            broker = config.broker_symbol(symbol)
            now = datetime.now(timezone.utc)
            trading_date = now.date()
            asian_start, asian_end = session_bounds(trading_date, config)
            exec_start, exec_end = execution_bounds(trading_date, config)
            spec, tick = gateway.symbol_spec(broker), gateway.tick(broker)
            offset = gateway.broker_utc_offset(
                [config.broker_symbol(s) for s in config.symbols], now, config.maximum_tick_age_seconds)
            tick["broker_offset_hours"] = offset

            session_candles = filter_window(
                gateway.candles(broker, asian_start, asian_end, offset), asian_start, asian_end)
            step = config.timeframe_seconds
            last_closed = now - timedelta(seconds=now.timestamp() % step)
            window_end = min(exec_end, last_closed)
            execution_candles = (
                filter_window(gateway.candles(broker, exec_start, window_end, offset),
                              exec_start, window_end)
                if window_end > exec_start else [])

            # Bug found 2026-08-25: this call was missing entirely, so
            # journal.healthy() (fed into analyze() as journal_healthy, which
            # gates G14_DAILY_RISK/G15_DRAWDOWN) always read a never-refreshed,
            # stale sync_state row -- both gates failed unconditionally.
            # cli.py's analyze_command() calls this same _sync() every run;
            # this script must too.
            _sync(journal, gateway, config)

            used, drawdown = journal.risk_stats(account.equity, now)
            # Gate on the EXECUTION LEDGER (an order was actually sent), not
            # journal.trades_this_session() (a ticket was printed) -- see
            # ExecutionLedger.has_committed_execution_today() docstring. Using
            # the journal here would let a plain dry run permanently consume
            # the one-shot quota for a real signal before order_check ever ran.
            taken = 1 if ledger.has_committed_execution_today(
                symbol, trading_date.isoformat(), ASIAN_SESSION_V1_MAGIC) else 0
            news_events, news_calendar_available = _load_news_calendar(config)

            result = analyze(
                config=config, symbol=symbol, trading_date=trading_date, now=now,
                account=account, spec=spec, tick=tick, session_candles=session_candles,
                execution_candles=execution_candles, one_lot_loss=gateway.loss_for_one_lot,
                daily_used_cash=used, drawdown_percent=drawdown,
                journal_healthy=journal.healthy(), trades_taken_this_session=taken,
                account_identity_verified=bool(config.allowed_logins()),
                news_events=news_events, news_calendar_available=news_calendar_available)
            result.broker_symbol = broker
            paths = write_artifacts(result, session_candles + execution_candles, Path(args.output))
            journal.record(result, paths)
            print(markdown(result))

            if not result.accepted:
                print(json.dumps({"execution": "NOT_ATTEMPTED", "reason": "no accepted signal"}, indent=2))
                return 3

            intent = build_intent(result)
            sig_id = signal_id(result)
            attempt_id = result.analysis_id

            committed, reason = execution_already_committed(ledger, gateway, sig_id, intent.symbol, ASIAN_SESSION_V1_MAGIC)
            if committed:
                print(json.dumps({
                    "execution": "DUPLICATE_BLOCKED",
                    "signal_id": sig_id,
                    "reason": reason,
                }, indent=2))
                return 1

            if not args.confirm:
                payload = {
                    "execution": "DRY_RUN",
                    "signal_id": sig_id,
                    "would_submit": {
                        "symbol": intent.symbol, "direction": intent.direction,
                        "entry_type": intent.entry_type, "entry_price": intent.entry_price,
                        "stop_price": intent.stop_price, "target_price_5R": intent.target_price,
                    },
                    "note": "TP is the 5R ceiling. The 4R partial-close/breakeven step is NOT "
                            "automated -- manage manually via `python sspf.py monitor`.",
                    "to_actually_submit": "re-run with --confirm and ALLOW_ORDER_SUBMISSION=true "
                                          "and ALLOW_ONE_DEMO_ORDER=true set",
                }
                if args.check:
                    payload["broker_check"] = dry_broker_check(config, gateway, intent)
                print(json.dumps(payload, indent=2))
                return 0

            if not allow_order_submission():
                print(json.dumps({
                    "execution": "REFUSED", "signal_id": sig_id,
                    "reason": "ALLOW_ORDER_SUBMISSION is not set truthy",
                }, indent=2))
                return 1
            if os.environ.get("ALLOW_ONE_DEMO_ORDER", "").lower() not in ("true", "1", "yes"):
                print(json.dumps({
                    "execution": "REFUSED", "signal_id": sig_id,
                    "reason": "ALLOW_ONE_DEMO_ORDER is not set truthy -- this is the third, "
                              "independent one-shot switch and is required in addition to "
                              "--confirm and ALLOW_ORDER_SUBMISSION",
                }, indent=2))
                return 1

            outcome = submit_one_order(config, gateway, ledger, sig_id, attempt_id, intent)
            print(json.dumps({"execution": "ATTEMPTED", "signal_id": sig_id, **outcome}, indent=2, default=str))
            return 0 if outcome.get("outcome") in (
                "CONFIRMED", "CONFIRMED_VIA_DEAL_HISTORY", "PENDING_ORDER_CONFIRMED") else 1
    finally:
        ledger.close()
        journal.close()


if __name__ == "__main__":
    raise SystemExit(main())
