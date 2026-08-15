from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import sys

from .config import load_config
from .engine import analyze, execution_bounds, filter_window, session_bounds
from .journal import Journal
from .lifecycle import assess_analysis, assess_profitability
from .mt5_gateway import MT5ReadOnlyGateway
from .render import markdown, write_artifacts


ROOT = Path(__file__).resolve().parents[1]
JOURNAL_PATH = ROOT / "data" / "sspf_journal.sqlite3"
OUTPUT_ROOT = ROOT / "outputs"


def _load_news_calendar(config) -> tuple[list[dict], bool]:
    """Load operator-maintained events without network or clock-dependent behavior."""
    if not config.news_filter.get("enabled"):
        return [], True
    source = Path(config.news_filter["source"])
    if not source.is_absolute():
        source = ROOT / source
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        events = payload["events"]
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        return events, True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return [], False


def _gateway(config) -> MT5ReadOnlyGateway:
    return MT5ReadOnlyGateway(config.execution_permissions)


def _sync(journal: Journal, gateway: MT5ReadOnlyGateway, config) -> dict:
    specs = {symbol: gateway.symbol_spec(config.broker_symbol(symbol)) for symbol in config.symbols}
    positions, orders = gateway.positions(), gateway.orders()
    broker_symbols = {symbol: config.broker_symbol(symbol) for symbol in config.symbols}
    active = journal.match_active(positions, orders, specs, broker_symbols)
    expired = journal.expire_unfilled_proposals(datetime.now(timezone.utc))
    now = datetime.now(timezone.utc)
    deals = gateway.deals(now - timedelta(days=730), now)
    position_ids = {int(p.get("identifier", p["ticket"])) for p in positions}
    closed = journal.update_closed(deals, position_ids)
    healthy = not active["ambiguous"]
    detail = f"matched={active['matched']}, closed={closed}, ambiguous={len(active['ambiguous'])}"
    journal.mark_sync(healthy, detail, "HEALTHY" if healthy else "AMBIGUOUS")
    return {**active, "expired_proposals": expired, "closed": closed,
            "healthy": healthy, "detail": detail}


def _guard_account(config, account, gateway) -> None:
    """Suffix matching is weak — different accounts can share three digits.
    Prefer an exact login allowlist, supplied via config or SSPF_ALLOWED_LOGINS."""
    guard = config.account_guard
    allowed = config.allowed_logins()
    if allowed:
        if not gateway.account_login_matches(allowed):
            raise RuntimeError("Account is not in the login allowlist")
    elif guard.get("reject_suffix_only_matching"):
        raise RuntimeError(
            "No login allowlist configured and reject_suffix_only_matching is true. "
            "Set SSPF_ALLOWED_LOGINS or account_guard.allowed_logins.")


def health(args) -> int:
    config = load_config(args.config)
    with _gateway(config) as gateway:
        account = gateway.account()
        symbols = {}
        for name, limits in config.symbols.items():
            broker = limits.broker_symbol
            try:
                spec, tick = gateway.symbol_spec(broker), gateway.tick(broker)
                spread = tick["ask"] - tick["bid"]
                symbols[name] = {
                    "broker_symbol": broker, "available": True, "digits": spec.digits, "point": spec.point,
                    "tick_size": spec.tick_size, "volume_min": spec.volume_min,
                    "volume_max": spec.volume_max, "volume_step": spec.volume_step,
                    "minimum_stop_distance": spec.stops_level_price, "spread": spread,
                    "maximum_spread": limits.maximum_spread,
                    "spread_ok": spread <= limits.maximum_spread,
                }
            except Exception as exc:
                symbols[name] = {"broker_symbol": broker, "available": False, "error": str(exc)}
        print(json.dumps({
            "connected": True, "read_only": True,
            "strategy_id": config.strategy_id, "contract_version": config.contract_version,
            "config_hash": config.hash, "account": account.__dict__, "symbols": symbols,
        }, indent=2))
    return 0


def analyze_command(args) -> int:
    config = load_config(args.config)
    try:
        symbol = config.resolve_symbol(args.symbol)
    except KeyError:
        print(json.dumps({"status": "NO_TRADE", "reason_codes": ["SYMBOL_NOT_SUPPORTED"],
                          "error": f"Unsupported exact symbol: {args.symbol}"}, indent=2))
        return 2
    now = datetime.now(timezone.utc)
    trading_date = date.fromisoformat(args.trading_date) if args.trading_date else now.date()
    asian_start, asian_end = session_bounds(trading_date, config)
    exec_start, exec_end = execution_bounds(trading_date, config)
    journal = Journal(args.journal)
    try:
        with _gateway(config) as gateway:
            account = gateway.account()
            broker = config.broker_symbol(symbol)
            spec, tick = gateway.symbol_spec(broker), gateway.tick(broker)
            offset = gateway.broker_utc_offset(
                [config.broker_symbol(s) for s in config.symbols], now, config.maximum_tick_age_seconds)
            tick["broker_offset_hours"] = offset
            sync = _sync(journal, gateway, config)

            # MT5 range retrieval may include the closing timestamp, so the half-open
            # window is re-applied after retrieval rather than trusted from the API call.
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
            _guard_account(config, account, gateway)
            result = analyze(
                config=config, symbol=symbol, trading_date=trading_date, now=now,
                account=account, spec=spec, tick=tick, session_candles=session_candles,
                execution_candles=execution_candles, one_lot_loss=gateway.loss_for_one_lot,
                daily_used_cash=used, drawdown_percent=drawdown,
                journal_healthy=journal.healthy(), trades_taken_this_session=taken,
                account_identity_verified=bool(config.allowed_logins()),
                news_events=news_events, news_calendar_available=news_calendar_available)
            result.broker_symbol = broker
            if sync["unmatched_active"]:
                result.warnings.append(f"{sync['unmatched_active']} unmatched open MT5 item(s)")
            paths = write_artifacts(result, session_candles + execution_candles, Path(args.output))
            journal.record(result, paths)
            print(markdown(result))
            print("Artifacts:")
            print(json.dumps(paths, indent=2))
            return 0 if result.accepted else 3
    finally:
        journal.close()


def sync_command(args) -> int:
    config = load_config(args.config)
    journal = Journal(args.journal)
    try:
        with _gateway(config) as gateway:
            result = _sync(journal, gateway, config)
        print(json.dumps(result, indent=2))
        return 0 if result["healthy"] else 4
    finally:
        journal.close()


def verify_command(args) -> int:
    journal = Journal(args.journal)
    try:
        journal.verify(args.analysis_id, args.outcome, args.note)
        print(json.dumps({"analysis_id": args.analysis_id, "outcome": args.outcome.upper(),
                          "recorded": True}, indent=2))
        return 0
    finally:
        journal.close()


def readiness_command(args) -> int:
    config = load_config(args.config)
    journal = Journal(args.journal)
    checks = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    try:
        permissions = config.execution_permissions
        read_only = not any(permissions.get(x, False) for x in
                            ("submit_orders", "modify_orders", "close_positions"))
        check("CODE_READ_ONLY", read_only, "all order mutation permissions disabled")
        governance = config.governance
        signoff = governance.get("parameter_signoff", {})
        signed = signoff.get("status") == "APPROVED" and signoff.get("config_hash") == config.signoff_hash
        check("PARAMETERS_SIGNED_OFF", signed,
              "approved for active config" if signed else "trader approval for active config is missing")
        cost_signed = bool(config.cost_model.get("cost_model_signed_off"))
        check("COST_MODEL_SIGNED_OFF", cost_signed,
              "cost assumptions approved" if cost_signed else "commission/slippage assumptions are provisional")

        with _gateway(config) as gateway:
            account = gateway.account()
            sync = _sync(journal, gateway, config)
            check("DEMO_ACCOUNT", account.account_type == "demo" and
                  account.server == config.account_guard["required_server"],
                  f"account={account.account_type}, server={account.server}")
            allowed = config.allowed_logins()
            exact_account = bool(allowed) and gateway.account_login_matches(allowed)
            check("EXACT_ACCOUNT_ALLOWLIST", exact_account,
                  "current demo login exactly matches allowlist" if exact_account
                  else "set SSPF_ALLOWED_LOGINS to the exact current demo login")
            check("EXPERT_TRADING_DISABLED", not account.expert_allowed,
                  f"MT5 expert_allowed={account.expert_allowed}; manual trading remains available")
            check("JOURNAL_RECONCILED", sync["healthy"] and not sync["unmatched_active"],
                  f"{sync['detail']}, unmatched_active={sync['unmatched_active']}")

        verified = journal.verification_stats(config.hash)
        evidence_ok = verified["matches"] >= 20 and verified["mismatches"] == 0
        check("MANUAL_RECONCILIATIONS", evidence_ok,
              f"matches={verified['matches']}/20 minimum, mismatches={verified['mismatches']}")
        ready = all(item["passed"] for item in checks)
        print(json.dumps({"status": "READY_FOR_MANUAL_DAY_TRADING" if ready else "NOT_READY",
                          "strategy_id": config.strategy_id, "config_hash": config.hash,
                          "parameter_signoff_hash": config.signoff_hash,
                          "checks": checks}, indent=2))
        return 0 if ready else 6
    finally:
        journal.close()


def monitor(args) -> int:
    config = load_config(args.config)
    journal = Journal(args.journal)
    try:
        analysis = journal.get(args.analysis_id)
        payload = json.loads(analysis["result_json"])
        with _gateway(config) as gateway:
            sync = _sync(journal, gateway, config)
            positions, orders = gateway.positions(), gateway.orders()
            match = journal.db.execute(
                "SELECT * FROM matches WHERE analysis_id=?", (args.analysis_id,)).fetchone()
            current = None
            if match:
                current = next((x for x in positions + orders
                                if int(x["ticket"]) == int(match["mt5_ticket"])), None)
            response = {"analysis_id": args.analysis_id, "ticket_status": analysis["status"],
                        "setup": payload.get("setup"), "direction": payload.get("direction"),
                        "match": dict(match) if match else None, "current_mt5_item": current,
                        "sync": sync, "read_only": True}
            risk = payload.get("initial_risk")
            if current and risk and "price_current" in current:
                sign = 1 if payload["direction"] == "LONG" else -1
                r_now = sign * (float(current["price_current"]) - payload["entry"]) / risk
                response["current_r"] = r_now
                response["next_action"] = (
                    f"close {payload.get('partial_close_percent', 75):.0f}% at {payload.get('partial_target', payload.get('tp1_4r'))} ({payload.get('partial_target_label', 'partial target')})"
                    if r_now < 4 else
                    f"runner target {payload.get('tp2_5r')} (5R); stop should be at entry")
            print(json.dumps(response, indent=2, default=str))
            return 0
    finally:
        journal.close()


def stage_command(args) -> int:
    result = (assess_analysis(args.analysis, args.ticket, args.config)
              if args.stage_name == "analysis" else assess_profitability(args.trades))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.passed else 5


def parser() -> ArgumentParser:
    p = ArgumentParser(prog="sspf", description="SSPF v2.2 read-only MT5 assistant")
    p.add_argument("--config", default=str(ROOT / "config" / "strategy.yaml"))
    p.add_argument("--journal", default=str(JOURNAL_PATH))
    sub = p.add_subparsers(dest="command", required=True)

    h = sub.add_parser("health"); h.set_defaults(func=health)
    a = sub.add_parser("analyze")
    a.add_argument("--symbol", required=True)
    a.add_argument("--trading-date")
    a.add_argument("--output", default=str(OUTPUT_ROOT))
    a.set_defaults(func=analyze_command)
    m = sub.add_parser("monitor"); m.add_argument("--analysis-id", required=True); m.set_defaults(func=monitor)
    j = sub.add_parser("journal"); js = j.add_subparsers(dest="journal_command", required=True)
    js.add_parser("sync").set_defaults(func=sync_command)
    jv = js.add_parser("verify")
    jv.add_argument("--analysis-id", required=True)
    jv.add_argument("--outcome", required=True, choices=("match", "mismatch"))
    jv.add_argument("--note", default="")
    jv.set_defaults(func=verify_command)
    sub.add_parser("readiness").set_defaults(func=readiness_command)
    g = sub.add_parser("stage"); gs = g.add_subparsers(dest="stage_name", required=True)
    ga = gs.add_parser("analysis"); ga.add_argument("--analysis", required=True)
    ga.add_argument("--ticket", required=True); ga.set_defaults(func=stage_command)
    gp = gs.add_parser("profitability"); gp.add_argument("--trades", required=True)
    gp.set_defaults(func=stage_command)
    return p


def main() -> int:
    try:
        args = parser().parse_args()
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "read_only": True}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
