# Session Trade Codex

> **Start with [`STATUS.md`](STATUS.md)** — current contract, current evidence, open decisions.
> `SESSION_FLOW_V1` (below and in most other documents in this folder) **failed its Stage 2
> backtest verdict on 2026-08-16/17 and is not the live contract.** The project reverted to
> `ASIAN_SESSION_V1` and, separately, opened a newer `SESSION_V2` research track that is currently
> execution-blocked. `STATUS.md` is authoritative on all of this; the rest of this file predates
> that pivot and is kept for the strategy walkthrough only.

| | |
|---|---|
| Live, demo-authorized contract | **`ASIAN_SESSION_V1`** — `config/strategy.yaml`, hash `a41881d1cb4de00c` |
| Legacy contract on this page (`SESSION_FLOW_V1`) | **rejected at Stage 2** — see `STATUS.md` / `ROADMAP.md` |
| Active research track | `SESSION_V2` (`session_strategy/v2_research.py`) — `RESEARCH / EXECUTION_BLOCKED` |
| Newest registered study | `ST04_07_EXECUTION_ATTRIBUTION_V1` — [`ST04_07_EXECUTION_ATTRIBUTION_V1_SPEC.md`](ST04_07_EXECUTION_ATTRIBUTION_V1_SPEC.md), stage `research`, no MT5 calls |
| Data contract | [`data/README.md`](data/README.md) |
| Adding symbols | [`EXPORT_INSTRUCTIONS.md`](EXPORT_INSTRUCTIONS.md) |
| What to do next | [`ROADMAP.md`](ROADMAP.md) |

An execution layer capable of submitting/modifying/closing **demo** orders was added 2026-08-22
(`session_strategy/execution/`); live-account execution remains disabled
(`live_execution_authorized: false`). The claim that "no order-mutating call exists in this
codebase" — still made below and in `PROJECT_CHARTER.md`/`USER_MANUAL.md` — is no longer true for
that layer; see `STATUS.md` for the currently-failing safety test that used to prove it.

---

A local MetaTrader 5 assistant built around **the trader's own** session-based trading rules. The
walkthrough below describes the `SESSION_FLOW_V1` contract as originally designed — read-only,
manual-execution, 22:00–07:00 UTC Asian range. It is retained for the strategy explanation only;
it does not describe what is currently live. For the live contract's actual session window
(`00:00–07:00 UTC`, 28 candles) and execution status, see `STATUS.md`.

**This project does not create or optimise a trading strategy.** The rulebook is an input,
transcribed in `STRATEGY_SPEC.md` §0. Any divergence between the code and that specification is a
defect, even when it looks like an improvement.

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
