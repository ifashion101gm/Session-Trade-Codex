# FINAL SESSION — SSPF v2.2

Finalized after the 11:00 UTC execution cutoff on 2026-08-13. These replace and supersede every earlier same-session analysis snapshot for the listed symbol. Each final analysis includes the locked 00:00–08:00 UTC Asian baseline (32 closed M15 candles) and the complete 08:00–11:00 UTC sweep window (12 closed M15 candles, 08:00 through 10:45 UTC).

All results are analysis-only. No MT5 order, position, or setting was changed.

| Symbol | Final setup / status | Failed gate | Artifacts |
| --- | --- | --- | --- |
| EURUSD | NONE / NO_TRADE | G4_SESSION_DATA — non-positive spread | [analysis.json](1748358606eb/analysis.json) · [ticket.md](1748358606eb/ticket.md) · [chart.png](1748358606eb/chart.png) |
| GBPUSD | TREND_CONTINUATION SHORT / NO_TRADE | G16_EXECUTION_WINDOW — finalization occurred after 11:00 UTC | [analysis.json](2e69f8ecabd1/analysis.json) · [ticket.md](2e69f8ecabd1/ticket.md) · [chart.png](2e69f8ecabd1/chart.png) |
| USDJPY | NONE / NO_TRADE | G10_SETUP_DETECTED — no qualifying setup in 12 sweep candles | [analysis.json](3cce95616705/analysis.json) · [ticket.md](3cce95616705/ticket.md) · [chart.png](3cce95616705/chart.png) |
| XAUUSD.crp | NONE / NO_TRADE | G5_RANGE_BOUNDS — Asian range 80.82 outside [2, 25] | [analysis.json](e1356fe9bb3e/analysis.json) · [ticket.md](e1356fe9bb3e/ticket.md) · [chart.png](e1356fe9bb3e/chart.png) |

## Journal result

`python sspf.py journal sync` completed healthy after finalization: zero matches, closures, active proposals, or proposals expired in this pass. Earlier same-session snapshots are superseded by this final index; there were no unfilled journal proposals remaining to mark `EXPIRED`.
