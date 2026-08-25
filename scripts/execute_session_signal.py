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
- Even with --confirm, DemoExecutor's own composite gate independently requires
  the ALLOW_ORDER_SUBMISSION environment variable to be truthy, or it fails
  closed with SUBMIT_PERMISSION_DENIED. Two independent switches, not one.

Usage
-----
    python scripts/execute_session_signal.py --symbol EURUSD                    # dry run
    ALLOW_ORDER_SUBMISSION=true python scripts/execute_session_signal.py \\
        --symbol EURUSD --confirm                                              # submits
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.config import load_config, allow_order_submission  # noqa: E402
from session_strategy.engine import analyze, session_bounds, execution_bounds, filter_window  # noqa: E402
from session_strategy.journal import Journal  # noqa: E402
from session_strategy.mt5_gateway import MT5ExecutionGateway  # noqa: E402
from session_strategy.render import markdown, write_artifacts  # noqa: E402
from session_strategy.execution.models import TradeIntent  # noqa: E402
from session_strategy.execution.executor import DemoExecutor  # noqa: E402


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--config", default=str(ROOT / "config" / "strategy.yaml"))
    ap.add_argument("--journal", default=str(ROOT / "data" / "sspf_journal.sqlite3"))
    ap.add_argument("--output", default=str(ROOT / "outputs"))
    ap.add_argument("--confirm", action="store_true",
                     help="Attempt real submission. Without this, always dry-run.")
    args = ap.parse_args()

    config = load_config(args.config)
    if config.trading_mode != "demo":
        print(json.dumps({"error": f"trading_mode={config.trading_mode!r}, not demo; refusing"}, indent=2))
        return 1

    journal = Journal(args.journal)
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

            used, drawdown = journal.risk_stats(account.equity, now)
            taken = journal.trades_this_session(symbol, trading_date.isoformat())
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

            if not args.confirm:
                print(json.dumps({
                    "execution": "DRY_RUN",
                    "would_submit": {
                        "symbol": intent.symbol, "direction": intent.direction,
                        "entry_type": intent.entry_type, "entry_price": intent.entry_price,
                        "stop_price": intent.stop_price, "target_price_5R": intent.target_price,
                    },
                    "note": "TP is the 5R ceiling. The 4R partial-close/breakeven step is NOT "
                            "automated -- manage manually via `python sspf.py monitor`.",
                    "to_actually_submit": "re-run with --confirm and ALLOW_ORDER_SUBMISSION=true set",
                }, indent=2))
                return 0

            executor = DemoExecutor(config=config, gateway=gateway)
            report = executor.execute(intent)
            print(json.dumps({
                "execution": "ATTEMPTED",
                "validation": report.validation.value,
                "volume": report.volume,
                "order_check_retcode": report.order_check_retcode,
                "order_send_retcode": report.order_send_retcode,
            }, indent=2))
            return 0 if report.validation.value == "SUCCESS" else 1
    finally:
        journal.close()


if __name__ == "__main__":
    raise SystemExit(main())
