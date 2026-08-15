# Two-Stage Implementation — ASIAN_SESSION_V1 Hybrid Workflow

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

The project keeps two questions separate, because mixing them makes both unanswerable:

| Stage | Question | Evidence |
|---|---|---|
| **Stage 1** | Does the tool **recommend correctly** according to the trader's rules? | Generated artifacts checked against the specification |
| **Stage 2** | Does the trader's **strategy** have an edge? | A suitable backtest over historical data |

```
STAGE 1 — recommendation correctness
        │
        ▼
   DAY TRADING BEGINS  ← the hybrid workflow: tool recommends, trader executes
        │
        ▼
STAGE 2 — strategy validation by backtest
```

Day trading begins at the end of Stage 1, not at the end of Stage 2. That is a deliberate
sequencing decision by the trader, recorded in `PROJECT_CHARTER.md` §5.2.

Neither stage places, modifies, or closes an MT5 order at any point.

---

## Stage 1 — Recommendation correctness

Stage 1 asks whether the tool applies **the trader's** rulebook exactly. It does not ask whether
the rulebook is any good. A faithful implementation of a losing strategy passes Stage 1, and
should.

### What is checked automatically

```powershell
python sspf.py stage analysis --analysis PATH_TO_ANALYSIS.json --ticket PATH_TO_TICKET.md
```

The saved `analysis.json` and `ticket.md` must use the active configuration hash, a demo account,
an approval status consistent with the recorded gates, the same analysis ID in both files, every
gate reproduced in the ticket, and the fixed manual-execution disclaimer.

### What must also be true — the exit criteria

Automated conformance is necessary but not sufficient. Stage 1 closes when all eight criteria in
`PROJECT_CHARTER.md` §5.1 hold. In short:

1. Every rule in `STRATEGY_SPEC.md` §0 conforms — **verified by execution**.
2. No gate reports `PASS` without testing anything.
3. The conformance check passes on freshly generated artifacts.
4. Artifacts stay verifiable after a config change.
5. 20–30 tickets reconciled by hand against the MT5 chart, zero discrepancies.
6. Order-capable MT5 tools disabled in the environment.
7. Provisional parameters signed off — buffers and per-symbol range/spread limits.
8. Journal reconciliation correct, so the risk gates can be trusted during live trading.

Passing Stage 1 authorises **manual day trading with human verification of every order**. It
authorises nothing automated.

---

## Stage 2 — Strategy validation by backtest

Stage 2 asks the separate question: does the strategy itself have a positive edge?

### Method

A suitable backtest over historical data, which must:

- use completed candles only, with no look-ahead;
- model spread, commission, and slippage assumptions explicitly;
- resolve intrabar stop/target ambiguity conservatively;
- model the 75% partial and the setup-specific management rules;
- keep development and out-of-sample periods separate;
- report results by setup, session, and month — not just in aggregate.

### Scoring

```powershell
python sspf.py stage profitability --trades PATH_TO_TRADES.json
```

Each record must identify `ASIAN_SESSION_V1` contract version 1.0, name its `setup`, be
rule-compliant, non-synthetic, and labelled `out_of_sample` or `forward_demo`.

The versioned thresholds in `config/lifecycle.json` require 50 total records, 30 eligible
out-of-sample records, expectancy of at least 0.10R, profit factor at least 1.20, 90% bootstrap
confidence, and drawdown no greater than 10R. A profit factor of infinity — a sample with no
losses — is an explicit failure requiring review, not a pass.

### The blocking gap

**No backtest engine exists.** `stage profitability` scores a trade log; nothing in this project
produces one. `IMPLEMENTATION_PLAN.md` Phase 7 was never delivered. Stage 2 as defined therefore
cannot be run today, and building or sourcing the backtester is the largest single outstanding
piece of work. Tracked as finding A27.

Until then, the only evidence accumulating is forward-demo and live day-trading records from the
journal. Those are useful, and `accepted_samples` admits them — but they are slow, they are not a
backtest, and they are gathered while trading rather than before it.

---

## What passing means

Passing Stage 1 verifies that the tool applies the recorded rules faithfully.
Passing Stage 2 verifies that the recorded version showed a positive edge under the tested
conditions.

Neither guarantees future profit, and neither authorises live automated execution. Change one
strategy version at a time and retain its configuration hash, or the evidence from either stage
cannot be attributed to anything.
