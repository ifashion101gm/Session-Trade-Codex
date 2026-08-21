# FINAL SESSION — SSPF v2.2

Finalized after the 11:00 UTC execution cutoff on 2026-08-14. This index replaces and supersedes every earlier same-session analysis snapshot for each listed symbol. Every final artifact uses the locked 00:00–08:00 UTC Asian baseline (32 contiguous closed M15 candles) and the complete 08:00–11:00 UTC sweep window (12 closed M15 candles, 08:00 through 10:45 UTC).

All results are analysis-only. No MT5 order, position, or setting was placed, modified, cancelled, partially closed, or closed.

| Symbol | Final setup / status | Failed gate | Artifacts |
| --- | --- | --- | --- |
| EURUSD | NONE / NO_TRADE | G10_SETUP_DETECTED — no qualifying setup in 12 completed sweep candles | [analysis.json](6692a2b306a0/analysis.json) · [ticket.md](6692a2b306a0/ticket.md) · [chart.png](6692a2b306a0/chart.png) |
| GBPUSD | NONE / NO_TRADE | G10_SETUP_DETECTED — no qualifying setup in 12 completed sweep candles | [analysis.json](6c4ab4d3a2f7/analysis.json) · [ticket.md](6c4ab4d3a2f7/ticket.md) · [chart.png](6c4ab4d3a2f7/chart.png) |
| USDJPY | NONE / NO_TRADE | G10_SETUP_DETECTED — no qualifying setup in 12 completed sweep candles | [analysis.json](d4c3b82f58b1/analysis.json) · [ticket.md](d4c3b82f58b1/ticket.md) · [chart.png](d4c3b82f58b1/chart.png) |
| XAUUSD.crp | NONE / NO_TRADE | G5_RANGE_BOUNDS — Asian range 50.99 outside [2, 25] | [analysis.json](d768f299fddc/analysis.json) · [ticket.md](d768f299fddc/ticket.md) · [chart.png](d768f299fddc/chart.png) |

## Journal result

`python sspf.py journal sync` completed healthy after finalization: zero matches, closures, active proposals, or proposals expired in this pass. Any unfilled proposal older than 11:00 UTC would have been recorded locally as `EXPIRED`; none remained. Earlier same-session proposals are superseded by this final index.
