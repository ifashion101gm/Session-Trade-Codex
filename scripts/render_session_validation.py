"""Render MT5 M15 reference/execution candles with deterministic trade levels."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import asian_session_backtester as bt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--reference-session", choices=("asian", "london"), required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    day = date.fromisoformat(args.date)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    bars, source = bt.load_mt5(3, "EURUSD", day, day)
    result = bt.run(bars, source, evaluation_days=[day], execution_end_hour=22,
                    entry_end_hour=16 if args.reference_session == "asian" else 18,
                    reference_session=args.reference_session)
    start = datetime.combine(day, datetime.min.time(), timezone.utc)
    shown = [bar for bar in bars if start <= bar.time < start + timedelta(hours=22)]

    fig, ax = plt.subplots(figsize=(18, 9))
    fig.patch.set_facecolor("#101722")
    ax.set_facecolor("#101722")
    candle_width = 11 / (24 * 60)
    for bar in shown:
        x = mdates.date2num(bar.time)
        color = "#dce5eb" if bar.close >= bar.open else "#758592"
        ax.vlines(x, bar.low, bar.high, color=color, linewidth=1, zorder=4)
        body_low = min(bar.open, bar.close)
        body_height = max(abs(bar.close-bar.open), .000015)
        ax.add_patch(Rectangle((x-candle_width/2, body_low), candle_width, body_height,
                               facecolor=color, edgecolor=color, linewidth=.7, zorder=5))

    windows = [("ASIAN", 0, 7, "#2d82b7"), ("LONDON", 7, 12, "#20a486"),
               ("NEW YORK", 12, 18, "#8c6bd1")]
    for label, begin_hour, end_hour, color in windows:
        begin, end = start+timedelta(hours=begin_hour), start+timedelta(hours=end_hour)
        subset = [bar for bar in shown if begin <= bar.time < end]
        if not subset:
            continue
        high, low = max(bar.high for bar in subset), min(bar.low for bar in subset)
        x0, x1 = mdates.date2num(begin), mdates.date2num(end)
        ax.add_patch(Rectangle((x0, low), x1-x0, high-low, facecolor=color,
                               edgecolor=color, alpha=.13, linewidth=1.8, zorder=1))
        ax.text((x0+x1)/2, high+.00018, f"{label} {(high-low)/bt.PIP:.1f}p",
                color=color, ha="center", fontsize=9, fontweight="bold")

    for number, trade in enumerate(result.get("trades", []), 1):
        signal = datetime.fromisoformat(trade["signal_time"].replace("Z", "+00:00"))
        exit_text = trade.get("exit_time") or trade["signal_time"]
        exit_time = datetime.fromisoformat(exit_text.replace("Z", "+00:00"))
        x0, x1 = mdates.date2num(signal), mdates.date2num(max(exit_time, signal+timedelta(minutes=15)))
        entry, stop, target = trade["entry"], trade["stop"], trade["target"]
        profit_color, loss_color = "#00c9a7", "#e69f00"
        ax.add_patch(Rectangle((x0, min(entry, target)), x1-x0, abs(target-entry),
                               facecolor=profit_color, alpha=.18, zorder=2))
        ax.add_patch(Rectangle((x0, min(entry, stop)), x1-x0, abs(stop-entry),
                               facecolor=loss_color, alpha=.28, zorder=2))
        ax.hlines([entry, stop, target], x0, x1,
                  colors=["#55d6ff", "#ffb000", "#00e6be"], linewidths=1.3, zorder=3)
        ax.text(x0+.003, entry, f"T{number} {trade['setup']} {trade['direction']}\n"
                f"E {entry:.5f} | SL {stop:.5f} | TP5 {target:.5f}\n"
                f"{trade.get('outcome', 'PENDING')}", color="#e8f1f5", fontsize=8,
                bbox=dict(boxstyle="round,pad=.3", facecolor="#182431", alpha=.92))

    session = result["sessions"][0]
    ax.set_title(f"EUR/USD M15 — {day} MT5 Session Validation",
                 color="#e8f1f5", fontsize=15, fontweight="bold")
    ax.text(.01, .98, f"Source: {source} • UTC • Reference: {args.reference_session.upper()} • "
            f"Classifier: {session.get('session_type')} • Bias: {session.get('directional_bias')}",
            transform=ax.transAxes, va="top", color="#a9bac6", fontsize=9,
            bbox=dict(boxstyle="round,pad=.4", facecolor="#16212c", alpha=.92))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    ax.yaxis.tick_right()
    ax.grid(True, color="#314150", alpha=.22, linestyle="--")
    ax.tick_params(colors="#a9bac6")
    for spine in ax.spines.values():
        spine.set_color("#314150")
    ax.set_xlim(mdates.date2num(start), mdates.date2num(start+timedelta(hours=22)))
    ax.margins(y=.08)
    fig.tight_layout()
    target = output / f"{day}_{args.reference_session}_session_validation.png"
    fig.savefig(target, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
    print(target)


if __name__ == "__main__":
    main()
