"""Aggregate existing SSPF single-session JSON backtests without inventing outcomes."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from pathlib import Path
import json


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--dates", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    trades, sessions = [], []
    symbol_stats = defaultdict(Counter)
    setup_stats = defaultdict(Counter)
    data_failures = 0
    strategy_id = None
    h4_overrides = 0
    for trading_date in args.dates:
        report = json.loads((root / trading_date / "session_backtest.json").read_text())
        strategy_id = strategy_id or report.get("strategy_id")
        for symbol, item in report["symbols"].items():
            metrics = item.get("metrics", {})
            session = {"date": trading_date, "symbol": symbol, "status": item["status"],
                       "session_type": item.get("session_type", metrics.get("effective_classification")),
                       "asian_range": item.get("asian_range"),
                       "rejection_reason": item.get("rejection_reason")}
            sessions.append(session)
            symbol_stats[symbol]["sessions"] += 1
            if not item["data_quality"]["passed"]:
                data_failures += 1
                symbol_stats[symbol]["data_failures"] += 1
            if item["status"] == "REJECTED_RANGE_BOUNDS":
                symbol_stats[symbol]["range_rejections"] += 1
            triggered = [setup for setup in item.get("setups", [])
                         if setup["status"] == "TRIGGERED"]
            if not triggered:
                symbol_stats[symbol]["no_trigger"] += 1
            for trade in triggered:
                record = {"date": trading_date, "symbol": symbol, **trade}
                trades.append(record)
                if trade.get("h4_bias_override_applied"):
                    h4_overrides += 1
                symbol_stats[symbol]["triggered"] += 1
                setup_stats[trade["setup"]]["triggered"] += 1
                if trade["gross_r"] is None:
                    symbol_stats[symbol]["unresolved"] += 1
                    setup_stats[trade["setup"]]["unresolved"] += 1
                else:
                    symbol_stats[symbol]["resolved"] += 1
                    setup_stats[trade["setup"]]["resolved"] += 1
                    setup_stats[trade["setup"]]["gross_r"] += trade["gross_r"]
                    symbol_stats[symbol]["gross_r"] += trade["gross_r"]
                    if trade["gross_r"] > 0:
                        setup_stats[trade["setup"]]["wins"] += 1
                        symbol_stats[symbol]["wins"] += 1
                    else:
                        setup_stats[trade["setup"]]["losses"] += 1
                        symbol_stats[symbol]["losses"] += 1
    resolved = [trade for trade in trades if trade["gross_r"] is not None]
    spread_net = [trade["net_r_historical_spread_only"] for trade in resolved
                  if trade.get("net_r_historical_spread_only") is not None]
    gross_total = sum(trade["gross_r"] for trade in resolved)
    summary = {
        "strategy_id": strategy_id, "period": {"start": args.dates[0], "end": args.dates[-1]},
        "trading_days": len(args.dates), "symbol_sessions": len(sessions),
        "data_quality_failures": data_failures, "triggered_setups": len(trades),
        "resolved_trades": len(resolved), "unresolved_at_window_end": len(trades) - len(resolved),
        "resolved_gross_r": gross_total,
        "historical_spread_coverage": len(spread_net),
        "net_r_historical_spread_only": sum(spread_net) if spread_net else None,
        "friction_stress": {
            "0.2R_per_trade": gross_total - 0.2 * len(resolved),
            "0.3R_per_trade": gross_total - 0.3 * len(resolved),
            "0.4R_per_trade": gross_total - 0.4 * len(resolved),
        },
        "h4_override_trades": h4_overrides,
        "outcome_warning": "Trades still active at 20:00 UTC are exited at the final completed M15 close.",
        "setup_evaluation": "One canonical setup per symbol/session is selected by configured priority.",
        "by_symbol": {key: dict(value) for key, value in symbol_stats.items()},
        "by_setup": {key: dict(value) for key, value in setup_stats.items()},
        "trades": trades, "sessions": sessions,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
