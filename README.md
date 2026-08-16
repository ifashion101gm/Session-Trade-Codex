# Session Trade Codex

> **Start with [`STATUS.md`](STATUS.md)** — current contract, current evidence, open decisions.
> Most other documents in this folder predate the 2026-08-15 corrections.

| | |
|---|---|
| Active contract | **`SESSION_FLOW_V1`** — [`SESSION_FLOW_V1_SPEC.md`](SESSION_FLOW_V1_SPEC.md) |
| Engine | `scripts/session_flow.py` |
| Desk report | `scripts/engine_report.py` — runs at 07:00 and 12:00 UTC |
| Backtest | `scripts/backtest_session_flow.py` |
| Data contract | [`data/README.md`](data/README.md) |
| Adding symbols | [`EXPORT_INSTRUCTIONS.md`](EXPORT_INSTRUCTIONS.md) |
| What to do next | [`ROADMAP.md`](ROADMAP.md) |

Analysis only. No order-mutating call exists in this codebase.

---

A local, read-only MetaTrader 5 assistant that applies **the trader's own** Asian Session strategy.
It builds the 22:00–07:00 UTC Asian range, classifies the session, watches the 07:00–16:00 UTC
execution window for one of three setups, and writes a recommendation for a human to verify and
execute manually.

**This project does not create or optimise a trading strategy.** The rulebook is an input,
transcribed in `STRATEGY_SPEC.md` §0. Any divergence between the code and that specification is a
defect, even when it looks like an improvement.

**It never places, modifies, cancels, or closes an order.** The boundary is asserted at connect
time and enforced by tests. MT5 algorithmic trading is not required and should stay off.

Strategy: `ASIAN_SESSION_V1` v1.0 · **M15 only** · 124 tests pass. Run `python sspf.py readiness`
for the active config hash and release state.

> Supersedes SSPF v2.2. Different session window, classification metric, entry model, partial
> target and risk fraction — evidence from the old contract does not transfer.

---

## Start here

| If you want to… | Read |
|---|---|
| Understand what this project is for | [PROJECT_CHARTER.md](PROJECT_CHARTER.md) |
| Run it day to day | [USER_MANUAL.md](USER_MANUAL.md) |
| Know the rules it applies | [STRATEGY_SPEC.md](STRATEGY_SPEC.md) — §0 is the source of truth |
| Know what it needs to run | [RESOURCES.md](RESOURCES.md) |
| Know what is still open | [STAGE1_QUALIFICATION.md](STAGE1_QUALIFICATION.md) |

## The strategy in one screen

```
Build Asian range (22:00–07:00 UTC, 36 M15 candles)  →  lock high, low, range
        │
   Validate range and spread ──fail──→ NO TRADE
        │
   Classify: ER = |close-open| / range
        ├─ ER <= 0.35 ──────────────→ RANGE   → swept? → SWEEP : RANGE_REJECTION
        └─ ER > 0.35 + close location → TREND  → midpoint retracement → TREND_CONTINUATION
        │
   Stop = 25% of range (never widened) · TP1 = 4R, close 75% · TP2 = 5R
```

Instruments (logical → broker): `EURUSD`, `GBPUSD`, `USDJPY`, `XAUUSD` → `XAUUSD.crp`.
Risk 0.5% equity per trade, 2% daily, 15% drawdown, one trade per symbol per session.

## Full documentation

| Document | Purpose |
|---|---|
| [STRATEGY_SPEC.md](STRATEGY_SPEC.md) | Source of truth, gate pipeline, validation, open questions |
| [PROJECT_CHARTER.md](PROJECT_CHARTER.md) | Summary, objective, scope, expected results, risks |
| [USER_MANUAL.md](USER_MANUAL.md) | Setup, daily rhythm, reading a ticket, troubleshooting |
| [RESOURCES.md](RESOURCES.md) | Platform, dependencies, accounts, storage, time, cost |
| [CONFIGURATION.md](CONFIGURATION.md) | Every key, its effect, and its config-hash impact |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module ownership, data flow, entry points, exit codes |
| [OPERATIONAL_WORKFLOW.md](OPERATIONAL_WORKFLOW.md) | The scheduled daily workflow |
| [SESSION_PROMPT.md](SESSION_PROMPT.md) | Operator prompt — CLI-driven, never LLM-calculated |
| [STAGED_IMPLEMENTATION.md](STAGED_IMPLEMENTATION.md) · [STAGE1_QUALIFICATION.md](STAGE1_QUALIFICATION.md) | Two-stage release gate and its status |
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | Findings and remediation backlog |
| [REVIEW_RESPONSE.md](REVIEW_RESPONSE.md) | Adjudication of external proposals |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Original delivery plan, with phases marked |

## Quick reference

```powershell
python sspf.py health
python sspf.py readiness
python sspf.py journal sync
python sspf.py analyze --symbol EURUSD
python sspf.py monitor --analysis-id ANALYSIS_ID
python -m unittest discover -s tests -v
```

Artifacts are written to `outputs/<trading-date>/<analysis-id>/`; the journal lives at
`data/sspf_journal.sqlite3`.

## Two stages

| | Question | Status |
|---|---|---|
| **Stage 1** | Does the tool recommend correctly, per the trader's rules? | engine conforms; release-gate and traceability items open |
| *then* | **Day trading begins** with the hybrid workflow | — |
| **Stage 2** | Does the strategy itself have an edge? | **cannot run** — no backtest engine exists |

## Before you trade anything

Expect frequent `NO_TRADE`. The fixed 25%-of-range stop means a sweep only qualifies when the
reclaim candle closes back near the boundary — `STRATEGY_SPEC.md` §7 derives the band. Five
parameters are **provisional** and need your sign-off (`CONFIGURATION.md` §6), and the
specification's own worked example 1 fails its own structural rule — the engine follows the rule.

---

Analysis only. Levels and calculated volume are proposals, not automated signals. Verify every
value against your own chart and broker order window before placing or managing an order manually.
