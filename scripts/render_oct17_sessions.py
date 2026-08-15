"""Render the validated October 17 EURUSD M15 sessions and trades."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asian_session_backtester as bt


OUTPUT = ROOT / "outputs" / "eurusd_2022-10-17_validation"


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    bars, source = bt.load_mt5(3, "EURUSD", date(2022, 10, 17), date(2022, 10, 17))
    start = datetime(2022, 10, 17, tzinfo=timezone.utc)
    bars = [bar for bar in bars if start <= bar.time < start + timedelta(hours=19)]

    fig, ax = plt.subplots(figsize=(18, 9))
    fig.patch.set_facecolor("#101722")
    ax.set_facecolor("#101722")

    width = 11 / (24 * 60)
    for bar in bars:
        x = mdates.date2num(bar.time)
        bullish = bar.close >= bar.open
        color = "#dce5eb" if bullish else "#758592"
        ax.vlines(x, bar.low, bar.high, color=color, linewidth=1.0, zorder=4)
        bottom = min(bar.open, bar.close)
        height = max(abs(bar.close - bar.open), 0.000015)
        ax.add_patch(Rectangle((x-width/2, bottom), width, height,
                               facecolor=color, edgecolor=color, linewidth=.7,
                               zorder=5))

    sessions = [
        ("ASIAN 00:00–07:00", 0, 7, "#2d82b7"),
        ("LONDON 07:00–12:00", 7, 12, "#20a486"),
        ("NEW YORK 12:00–18:00", 12, 18, "#8c6bd1"),
    ]
    for label, begin_hour, end_hour, color in sessions:
        begin, end = start + timedelta(hours=begin_hour), start + timedelta(hours=end_hour)
        subset = [bar for bar in bars if begin <= bar.time < end]
        high, low = max(bar.high for bar in subset), min(bar.low for bar in subset)
        x0, x1 = mdates.date2num(begin), mdates.date2num(end)
        ax.add_patch(Rectangle((x0, low), x1-x0, high-low,
                               facecolor=color, edgecolor=color, alpha=.13,
                               linewidth=1.8, zorder=1))
        ax.text(x0 + (x1-x0)/2, high + .00022,
                f"{label}\n{(high-low)/bt.PIP:.1f} pips",
                color=color, ha="center", va="bottom", fontsize=9,
                fontweight="bold")

    trades = [
        {"name": "London Long Sweep", "entry_time": "2022-10-17T08:45:00Z",
         "exit_time": "2022-10-17T10:00:00Z", "entry": .97338,
         "stop": .9727475, "partial": .97561, "target": .9765425,
         "result": "+3.894R gross"},
        {"name": "New York Long Range", "entry_time": "2022-10-17T12:30:00Z",
         "exit_time": "2022-10-17T15:45:00Z", "entry": .97707,
         "stop": .975805, "partial": .98213, "target": .983395,
         "result": "+4.250R gross"},
    ]
    for trade in trades:
        x0, x1 = mdates.date2num(utc(trade["entry_time"])), mdates.date2num(utc(trade["exit_time"]))
        ax.add_patch(Rectangle((x0, trade["entry"]), x1-x0,
                               trade["target"]-trade["entry"],
                               facecolor="#00c9a7", edgecolor="#00e6be",
                               alpha=.20, linewidth=1.3, zorder=2))
        ax.add_patch(Rectangle((x0, trade["stop"]), x1-x0,
                               trade["entry"]-trade["stop"],
                               facecolor="#e69f00", edgecolor="#ffb000",
                               alpha=.30, linewidth=1.2, zorder=2))
        ax.hlines([trade["entry"], trade["partial"], trade["target"], trade["stop"]],
                  x0, x1, colors=["#55d6ff", "#ffe66d", "#00e6be", "#ffb000"],
                  linestyles=["-", "--", "-", "-"], linewidths=[1.2, 1, 1.2, 1.2], zorder=3)
        ax.scatter([x0], [trade["entry"]], marker="^", s=65,
                   color="#55d6ff", edgecolor="white", linewidth=.5, zorder=7)
        ax.text(x0 + .004, trade["entry"],
                f"{trade['name']}\nEntry {trade['entry']:.5f} | SL {trade['stop']:.5f}\n"
                f"TP5 {trade['target']:.5f} | {trade['result']}",
                color="#e8f1f5", fontsize=8.5, va="center",
                bbox=dict(boxstyle="round,pad=.35", facecolor="#182431",
                          edgecolor="#3c5365", alpha=.92), zorder=8)

    ax.set_title("EUR/USD M15 — October 17, 2022 | Session Boxes and Validated Trades",
                 color="#e8f1f5", fontsize=15, fontweight="bold", pad=20)
    ax.text(.01, .985,
            f"Source: {source} • UTC • Bias: Bullish\n"
            "Asian→London: Range + low sweep → Long Sweep | "
            "London→New York: Range + no sweep → Long Range",
            transform=ax.transAxes, ha="left", va="top", color="#a9bac6",
            fontsize=9.5,
            bbox=dict(boxstyle="round,pad=.45", facecolor="#16212c",
                      edgecolor="#2b3d4b", alpha=.92))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_xlabel("October 17, 2022 — UTC", color="#a9bac6")
    ax.set_ylabel("EUR/USD", color="#a9bac6")
    ax.grid(True, color="#314150", alpha=.22, linestyle="--", linewidth=.6)
    ax.tick_params(colors="#a9bac6", labelsize=8.5)
    for spine in ax.spines.values():
        spine.set_color("#314150")
    ax.set_xlim(mdates.date2num(start)-.01, mdates.date2num(start+timedelta(hours=18, minutes=15)))
    ax.margins(y=.08)
    fig.tight_layout()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "oct17_three_sessions_validated.png", dpi=180,
                facecolor=fig.get_facecolor(), bbox_inches="tight")
    fig.savefig(OUTPUT / "oct17_three_sessions_validated.svg",
                facecolor=fig.get_facecolor(), bbox_inches="tight")
    print(OUTPUT / "oct17_three_sessions_validated.png")


if __name__ == "__main__":
    main()
