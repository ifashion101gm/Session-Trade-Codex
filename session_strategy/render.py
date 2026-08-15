from __future__ import annotations

from datetime import timezone
from pathlib import Path
import json

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .models import AnalysisResult, Candle


DISCLAIMER = "Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually."

MYANMAR_OFFSET_HOURS = 6.5


def _mmt(value) -> str:
    if value is None:
        return "N/A"
    from datetime import timedelta
    return (value + timedelta(hours=MYANMAR_OFFSET_HOURS)).strftime("%Y-%m-%d %H:%M MMT")


def markdown(result: AnalysisResult) -> str:
    failures = [f"{g.name}: {g.detail}" for g in result.gates if not g.passed]
    lines = [
        f"# {result.strategy_id} v{result.contract_version} — Trade Analysis Ticket", "",
        f"- Status: **{result.status}**",
        f"- Analysis ID: `{result.analysis_id}`",
        f"- Strategy: {result.strategy_id} v{result.contract_version} (config `{result.config_hash}`)",
        f"- Symbol: {result.symbol}",
        f"- Trading date: {result.trading_date}",
        f"- Timestamp (UTC): {result.timestamp_utc.isoformat()}",
        f"- Timestamp (Myanmar): {_mmt(result.timestamp_utc)}",
        f"- Asian session: {result.asian_start.isoformat() if result.asian_start else 'N/A'}"
        f" → {result.asian_end.isoformat() if result.asian_end else 'N/A'}",
        f"- Last closed execution candle: {result.execution_candle_times[-1] if result.execution_candle_times else 'none'}",
        f"- Account: {result.account.account_type.upper()} `{result.account.login_masked}` | Equity: ${result.account.equity:.2f}",
        f"- Bid / Ask / Spread: {result.bid} / {result.ask} / {result.spread:.10g}", "",
        "## Asian range (locked)", "",
        f"- High / Low: {result.asian_high} / {result.asian_low}",
        f"- Range: {result.asian_range}",
        f"- Midpoint: {result.midpoint}",
        f"- Quartiles: {result.lower_quartile} / {result.upper_quartile}",
        f"- Risk unit R (25% of range): {result.risk_unit}",
        f"- Efficiency ratio: {result.efficiency_ratio} · Close location: {result.close_location}",
        f"- Session type: **{result.session_type}**",
        f"- Setup: **{result.setup}**" + (f" {result.direction}" if result.direction else ""), "",
        "## Gate evaluation", "",
    ]
    lines.extend(f"- {'PASS' if g.passed else 'FAIL'} — {g.name}: {g.detail}" for g in result.gates)

    if result.entry is not None:
        lines.extend([
            "", "## Proposed signal — manual execution only", "",
            f"- Direction: {result.direction}",
            f"- Signal candle close (UTC): {result.signal_time.isoformat() if result.signal_time else 'N/A'}",
            f"- Entry: {result.entry}",
            f"- Stop loss: {result.stop_loss}",
            f"- Initial risk (1R): {result.initial_risk}",
            f"- Partial target ({result.partial_close_percent:.0f}% off): {result.partial_target} ({result.partial_target_label})",
            f"- TP2 (runner): {result.tp2_5r} (5R)",
            f"- Volume: {result.volume} lots"
            + (f"  (partial {result.partial_volume} / runner {result.runner_volume})"
               if result.runner_volume is not None else ""),
            f"- Risk: ${result.intended_risk_cash:.2f} intended"
            + (f" / ${result.actual_risk_cash:.2f} actual" if result.actual_risk_cash is not None else ""),
            f"- Risk basis: ${result.risk_basis_cash:.2f} (lower of balance and equity)",
            f"- Signal expires: {result.expiry_utc.isoformat() if result.expiry_utc else 'N/A'}",
            (f"- Estimated cost: {result.estimated_cost_r:.3f}R  ->  net TP1 {result.net_tp1_r:.2f}R, "
             f"net TP2 {result.net_tp2_r:.2f}R (gross {result.gross_tp2_r:.1f}R)"
             if result.estimated_cost_r is not None else "- Estimated cost: not available"),
            "", "### Management sequence", "",
            "1. Open the position with the original stop.",
            (f"2. At {result.partial_target_label} ({result.partial_target}): close "
             f"{result.partial_close_percent:.0f}%."),
            f"3. Move the remaining stop to entry ({result.entry}) and target 5R ({result.tp2_5r}).",
            "4. Never move the initial stop farther away.",
            "5. Do not re-enter this setup after the trade completes or is stopped.",
        ])
    if result.reason_codes:
        lines.extend(["", "## Reason codes", "", "`" + "` `".join(result.reason_codes) + "`"])
    if failures:
        lines.extend(["", "## Rejection reasons", ""] + [f"- {x}" for x in failures])
    if result.warnings:
        lines.extend(["", "## Warnings", ""] + [f"- {x}" for x in result.warnings])
    lines.extend(["", DISCLAIMER, ""])
    return "\n".join(lines)


def chart(result: AnalysisResult, candles: list[Candle], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 8), dpi=130)
    fig.patch.set_facecolor("#0b1016")
    ax.set_facecolor("#111820")
    width = 15 / (24 * 60) * 0.72
    for c in candles:
        x = mdates.date2num(c.time)
        color = "#16a085" if c.close >= c.open else "#e74c3c"
        ax.vlines(x, c.low, c.high, color=color, linewidth=0.8)
        ax.add_patch(Rectangle((x - width / 2, min(c.open, c.close)), width,
                               max(abs(c.close - c.open), 1e-12), facecolor=color, edgecolor=color))
    if candles and result.asian_high is not None:
        x0, x1 = mdates.date2num(candles[0].time), mdates.date2num(candles[-1].time)
        ax.add_patch(Rectangle((x0, result.asian_low), x1 - x0, result.asian_range,
                               facecolor="#3498db", edgecolor="#5dade2", alpha=0.10))
        for value, label, color in [(result.asian_high, "Asian high", "#5dade2"),
                                    (result.asian_low, "Asian low", "#5dade2"),
                                    (result.midpoint, "Midpoint", "#95a5a6"),
                                    (result.entry, "Entry", "#f1c40f"),
                                    (result.stop_loss, "SL", "#e74c3c"),
                                    (result.tp1_4r, "TP1 4R", "#9b59b6"),
                                    (result.tp2_5r, "TP2 5R", "#2ecc71")]:
            if value is not None:
                ax.axhline(value, color=color, linestyle="--", linewidth=1, label=f"{label}: {value}")
    core = [v for v in (result.asian_low, result.asian_high, result.entry, result.stop_loss,
                        result.tp1_4r, result.tp2_5r) if v is not None]
    if core:
        lo, hi = min(core), max(core)
        pad = max((hi - lo) * 0.12, result.spread * 2, 1e-9)
        ax.set_ylim(lo - pad, hi + pad)
    ax.grid(True, color="#28323d", linewidth=0.5)
    ax.tick_params(colors="#c9d1d9")
    for spine in ax.spines.values():
        spine.set_color("#34404c")
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1, tz=timezone.utc))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    ax.set_title(f"{result.symbol} · {result.trading_date} UTC · {result.session_type} · {result.status}",
                 color="#e8edf2", loc="left")
    ax.legend(facecolor="#111820", labelcolor="#e8edf2", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def write_artifacts(result: AnalysisResult, candles: list[Candle], root: Path) -> dict[str, str]:
    folder = root / result.trading_date / result.analysis_id
    folder.mkdir(parents=True, exist_ok=True)
    json_path, md_path, chart_path = folder / "analysis.json", folder / "ticket.md", folder / "chart.png"
    json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    md_path.write_text(markdown(result), encoding="utf-8")
    chart(result, candles, chart_path)
    return {"json": str(json_path.resolve()), "markdown": str(md_path.resolve()),
            "chart": str(chart_path.resolve())}
