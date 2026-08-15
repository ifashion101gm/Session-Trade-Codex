# Session Trade Codex — Project Charter

Project: **SESSION_FLOW_V1** (supersedes ASIAN_SESSION_V1, which superseded SSPF v2.2)
Owner: Aung · Status: demo / shadow only · Charter date: 2026-08-11 · Config hash `2530b751134fbf6e`

---

## 1. Summary

Session Trade Codex is a local, read-only decision-support tool that applies **the trader's own
Session Trading Strategy** to live MetaTrader 5 data and produces a recommendation. Every weekday
it reads the completed Asian session, applies the trader's rulebook exactly as written, and
produces a proposal — a ticket, a chart, and a machine-readable record — which the trader then
verifies and executes by hand in MT5.

**The project does not create, design, invent, or optimise a trading strategy.** The strategy
belongs to the trader and is fixed; it is transcribed in `STRATEGY_SPEC.md` §0 from the trader's
own specification. The software's entire job is to apply those rules correctly and recommend
accordingly — never to improve on them, fill gaps in them with its own judgement, or substitute
a rule of its own.

Where the trader's rules are silent, the correct behaviour is to say so and stand aside, not to
invent. Every deviation between the code and the trader's specification is tracked as a defect in
`AUDIT_REPORT.md`, regardless of whether the deviation looks like an improvement.

The trader remains the only execution authority. The software cannot place, modify, cancel, or
close an order, and this is enforced by a test, not by a policy.

**One-line description:** it applies the trader's rules to today's chart and says what they imply
— nothing more.

---

## 2. Objective

### Primary objective

**Recommend correctly.** For any trading day, the recommendation the tool produces must be the
one the trader's own rules imply, given the analysed session — and it must be possible to
reconstruct exactly why, from stored evidence, without relying on memory or discretion.

Correctness here means conformance to the trader's specification, not profitability. A tool that
faithfully applies a losing strategy has met this objective; whether the strategy itself is worth
trading is the separate question that Stage 2 answers.

### Secondary objectives

| # | Objective | Measured by |
|---|---|---|
| O1 | Apply the trader's rules without deviation | Every rule in `STRATEGY_SPEC.md` §0 verified against the engine by execution — see §6 there |
| O2 | Eliminate calculation error | Ticket values reconcile exactly against MT5 on manual inspection |
| O3 | Eliminate rule drift between trading days | Every artifact carries a config hash; changing a rule changes the hash |
| O4 | Make standing aside the default | Any incomplete, stale, contradictory, or out-of-window condition returns `NO_TRADE` |
| O5 | Enforce the trader's risk limits before the trader can act | Sizing, daily loss ceiling, and drawdown are gates, not reminders |
| O6 | Keep the human in control of every order | No order-mutating call exists in the codebase |
| O7 | Provide the evidence needed to validate the strategy separately | Stage 2, §5.3 |

### Non-objectives

This project explicitly does **not**:

- **Generate, design, or modify a trading strategy.** The rulebook is an input, not an output.
- **Optimise parameters.** Thresholds come from the trader; the tool does not search for better
  ones.
- Automate execution. This is out of scope by design, not a deferred feature.
- Predict price, score setup quality, or express a market opinion.
- Trade multiple strategies, or run unattended without review.

If the tool ever appears to be improving on the strategy, that is a defect.

---

## 3. Scope

### In scope

- Reading account, symbol, tick, candle, position, order, and deal data from a local MT5 terminal.
- Calculating session levels, classification, setup, entry, stop, target, and volume.
- Enforcing environment, data-integrity, risk, drawdown, and timing gates.
- Writing deterministic artifacts and maintaining a local journal.
- Reconciling manually placed MT5 positions back to their originating proposal.
- A two-stage release gate: analysis conformance, then profitability verification.

### Out of scope

- Order submission, modification, or closure by software.
- Live-account operation before both release stages pass.
- **Any timeframe other than M15.** The strategy is M15-only by trader instruction; a
  higher-timeframe bias would be an invented rule, not a missing feature.
- News filtering — currently unspecified.
- Broker-side automation, EAs, or copy trading.

**Note on trailing stops.** Explicitly out of scope for v1: the specification fixes the 5R exit
for all three setups and states that trailing logic may only be added as a separately tested
strategy version.

### Scope boundary in one sentence

The software's authority ends at the word "proposed"; everything after that is the trader's.

---

## 4. Strategy in brief

Full rules are in `SESSION_FLOW_V1_SPEC.md`. The source of truth is the trader's strategy
diagram (*Episode 18 — Asian Session Trading*, 1BullBear). `STRATEGY_SPEC.md` is superseded and
retained for its analysis only.

Every rule in the active contract carries a provenance tag — **[DIAGRAM]**, **[BENCHMARK]** or
**[UNSIGNED]**. A rule with no tag is a defect. Two decisions (§4-A bias, §4-B range test) are
unsigned and the contract cannot execute until they are resolved.

```
Build Asian range (22:00-07:00 UTC, 36 M15)  ->  lock high / low / range
   -> validate range and spread          -> fail -> NO TRADE
   -> classify:  ER = |close - open| / range
        ER <= 0.35                       -> RANGE  -> swept? -> SWEEP : RANGE_REJECTION
        ER >  0.35 + close location      -> TREND  -> midpoint retracement -> TREND_CONTINUATION
   -> stop 25% of range · TP1 4R (close 75%, stop to entry) · TP2 5R
```

| | SWEEP | RANGE_REJECTION | TREND_CONTINUATION |
|---|---|---|---|
| Entry | sweep candle close | rejection candle close | confirmation candle close |
| Stop | 25% of range | 25% of range | 25% of range |
| TP1 | 4R — close 75%, stop to entry | same | same |
| TP2 | 5R | 5R | 5R |

Priority is Sweep → Range Rejection → Trend. `UNCERTAIN` sessions produce no trade.

**The engine conforms to every rule in `STRATEGY_SPEC.md` §0**, verified by execution rather than
inspection — see §6 of that document. All three setups are live; trailing is out of scope for v1.

**Timeframe: M15 only.** Every level, classification and trigger comes from 15-minute candles.
No higher or lower timeframe is consulted anywhere — verified: the package contains exactly one
timeframe reference, and timeframe is not configurable.

Instruments (logical names; broker suffixes are mapped in config): `EURUSD`, `GBPUSD`, `USDJPY`,
`XAUUSD` → `XAUUSD.crp`.
Asian session: 22:00–07:00 UTC, 36 closed M15 candles; the trading date is the date it ends.
Execution window: 07:00–16:00 UTC (up to 36 closed M15 candles). Signals expire at 16:00 UTC.
Risk: 0.5% of equity per trade, 2% daily, 15% drawdown, one trade per symbol per session.

---

## 5. The two stages

The project has two sequential goals with different questions and different evidence.

```
STAGE 1 — Does the tool recommend correctly?
   verify the engine applies the trader's rules exactly
                 │
                 ▼
   ── DAY TRADING BEGINS with the hybrid workflow ──
                 │
                 ▼
STAGE 2 — Does the strategy itself work?
   validate the rulebook with a suitable backtest
```

### 5.1 Stage 1 — recommendation correctness

**Question:** given an analysed session, does the tool output the recommendation the trader's
rules imply?

**Not in question:** whether those rules make money. Stage 1 can pass on a losing strategy. That
is by design — the two questions are kept separate so a bad result cannot be blamed on a bad
implementation, or vice versa.

**Exit criteria — all must hold before day trading begins:**

| # | Criterion | Status |
|---|---|---|
| S1.1 | Engine conforms to every rule in `STRATEGY_SPEC.md` §0 | ✅ verified by execution |
| S1.2 | No gate reports `PASS` without testing something | ✅ **met** |
| S1.3 | Stage 1 conformance check runs and passes on freshly generated artifacts | blocked by A1 |
| S1.4 | Artifacts are re-verifiable after a config change (schema version + config snapshot) | blocked by A3 |
| S1.5 | 20–30 tickets manually reconciled against the MT5 chart with zero discrepancies | not started |
| S1.6 | Order-capable MT5 tools disabled in the operating environment | ⚠️ partial — code boundary asserted; connector setting still open (A25) |
| S1.7 | Provisional parameters (Q3) signed off | open |
| S1.8 | Journal reconciliation correct, so the daily-risk and drawdown gates are trustworthy in live use | blocked by A4, A5 |

S1.8 matters more once real trading starts than it does today: while shadow-running, a wrong
daily-risk figure is a reporting error; while day trading, it is the control that stops a bad day
becoming a worse one.

### 5.2 Day trading — begins when Stage 1 closes

Once Stage 1 is met, the trader begins day trading with the hybrid workflow: the tool analyses and
recommends, the trader verifies and executes. Every trade is recorded in the journal, so this
phase also produces forward evidence — but forward evidence is a by-product, not the Stage 2
answer.

**Stated plainly, once:** Stage 1 establishes that the tool applies the rules correctly. It says
nothing about whether the rules are profitable. Day trading before Stage 2 means trading a
strategy whose edge has not yet been measured. That is the trader's decision to make; this
document records it so it is a choice rather than an oversight.

### 5.3 Stage 2 — strategy validation by backtest

**Question:** does the trader's strategy have a positive edge?

**Method:** a suitable backtest over historical data, run without look-ahead, with realistic
spread, slippage and cost assumptions, and with development and out-of-sample periods kept
separate.

Thresholds are fixed **in advance** in `config/lifecycle.json` so the bar cannot move after
results are seen. A strategy version is verified only when all six hold simultaneously:

| Criterion | Threshold |
|---|---|
| Total recorded trades | ≥ 50 |
| Compliant out-of-sample trades | ≥ 30 |
| Expectancy | ≥ 0.10R |
| Profit factor | ≥ 1.20 (an infinite value fails — a sample with no losses needs review) |
| Bootstrap confidence that expectancy > 0 | ≥ 90% (2000 resamples, seeded) |
| Maximum drawdown | ≤ 10R |

**Blocking gap:** `sspf.py stage profitability` scores a trade log, but **no backtest engine
exists to produce one** (finding A27). Stage 2 as defined cannot currently be run at all. Building
or sourcing the backtester is the largest single piece of outstanding work in the project.

**What passing means:** the tested version showed a positive edge under the tested conditions. It
does not predict future results and does not authorise automated execution.

### 5.4 Expected result if the strategy fails Stage 2

A documented, evidence-backed "no", produced cheaply. A version that fails should be recorded and
retained with its config hash, then either revised as a new version or abandoned — not quietly
re-tuned until the numbers improve. Since day trading starts before Stage 2, a failure would also
be a signal to stop trading the strategy, not merely to shelve a report.

---

## 6. Success criteria for the project

The project — the tool, as distinct from the strategy — is done when all of the following are
true:

1. The system is deterministic: identical inputs produce identical outputs. **met**
2. It is read-only, and that property is enforced by an automated test. **met**
3. It is timestamp-safe across broker offsets, DST, and midnight. **met**
4. Every refusal names a failing gate. **met**
5. Every rule in the trader's specification is applied without deviation. **9 / 12**
6. Every proposal reconciles exactly against MT5 on manual inspection. **not yet sampled**
7. No branch produces a recommendation the trader's rules do not support. **blocked by A26**
8. Stage 1 conformance passes on freshly generated artifacts. **blocked by A1, A3**
9. A backtest capability exists that can produce a Stage 2 trade log. **not built — A27**
10. Stage 2 has been run and returned a verdict — pass or fail. **blocked by 9**

Criteria 1–4 are met. 5–8 are the Stage 1 work. 9–10 are Stage 2.

Note that criterion 10 is a verdict, not a pass. The project succeeds if it answers the question
honestly; the strategy succeeds only if the answer is yes.

---

## 7. Open decisions blocking progress

D1–D4 are **all closed** by the ASIAN_SESSION_V1 specification: flat 25% stop with structural
rejection, 22:00–07:00 session, 0.5% risk, and no trailing in v1. What remains open are the
parameters the specification names but does not value.

| # | Question | Current | Consequence |
|---|---|---|---|
| Q1 | Worked example 1 fails its own structural rule. Is the example wrong, or the rule? | rule followed, example rejected | Changes how many sweeps are tradeable |
| Q2 | §0 lists EURUSD, GBPUSD, XAUUSD. Is USDJPY still in the universe? | retained | Symbol coverage |
| Q3 | Sign-off on `sweep_buffer`, `stop_buffer`, `touch_tolerance`, and per-symbol range/spread limits | provisional values | **Determines how often any setup qualifies** |
| Q4 | Exact gold symbol | `XAUUSD.crp` | G2 rejects a wrong string |

Q3 is the one that matters most: the buffers set the feasible sweep band, so they control trade
frequency directly. Details in `STRATEGY_SPEC.md` §§1, 7 and 8.

---

## 8. Risks

| Risk | Severity | Current mitigation |
|---|---|---|
| An order reaches the broker through the MT5 connector rather than the codebase | High | Code boundary now asserted at connect time and scanned package-wide; **the connector setting itself is still open** — finding A25 |
| Sweep selectivity is tight, so trade frequency may be very low | Medium | Direct consequence of the fixed 25% stop. Monitor the `NO_TRADE` rate; if sweeps never qualify, the buffers (Q3) need review |
| Evidence is collected under unsigned provisional parameters | High | Blocked on Q3 |
| Day trading begins before the strategy's edge has been measured | High | Accepted by the trader as a deliberate sequencing choice — §5.2. Mitigated only by demo-first operation and the risk gates |
| Stage 2 cannot be run because no backtest engine exists | High | None — finding A27; it is the largest outstanding build |
| Config drift silently invalidates the evidence base | Medium | Config hash on every artifact; no commit traceability yet |
| Over-trading after a loss | Medium | Daily risk ceiling; per-session trade cap is configured but **not enforced** |
| Broker feed error or gap | Medium | Contiguity, OHLC-ordering, and staleness gates |
| Human enters the wrong volume by hand | Medium | Ticket states the gated volume; manual sizing bypasses three gates |

The first four are the ones to close before collecting further evidence.

---

## 9. Governing principle

> Analysis only. Levels and calculated volume are proposals, not automated signals. Verify every
> value against your own chart and broker order window before placing or managing an order
> manually.

Passing every gate means the configured rules passed. Nothing more.
