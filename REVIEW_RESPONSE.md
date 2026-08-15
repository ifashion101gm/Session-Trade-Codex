# Adjudication of External Proposals — 2026-08-11

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

> **⚠ Written against SSPF v2.2, superseded 2026-08-11.** The project migrated to
> **ASIAN_SESSION_V1** — different session window (22:00–07:00 UTC), classification metric,
> entry model, partial target and risk fraction. Findings below that describe v2.2 behaviour are
> retained as history, not as a description of the current engine. Items still live under V1 are
> listed in `STAGE1_QUALIFICATION.md`: **A1** (conformance status model), **A3** (config
> snapshot), **A4/A5** (journal reconciliation — partially repaired), **A6** (broker-clock failure
> writes no artifact), **A8** (orphan chart script), **A10** (automations out of tree),
> **A11** (test fixtures), **A12–A16** (traceability and hygiene), **A25** (connector setting),
> **A27** (no backtest engine). Current strategy conformance is in `STRATEGY_SPEC.md` §6.


- **Part A** — technical review proposing corrections to the stop, partials, session and risk.
- **Part B** — a proposed three-phase operational workflow. See §B.

---

# Part A — Technical review

An external review proposed corrections to the SSPF workflow. Each point below was checked
**against the source**, not against the prose in the docs. Verdicts:

- **UPHELD** — the finding is real; logged in `AUDIT_REPORT.md`.
- **UPHELD, REDIAGNOSED** — the concern is real but the stated cause is not what the code does.
- **ALREADY SATISFIED** — the code already does this.
- **NOT APPLICABLE** — the claim describes a different workflow than the one implemented.
- **DECISION REQUIRED** — valid, but it changes the strategy and needs trader sign-off.

Nothing in this pass changed code or configuration.

---

## Scoreboard

| # | Review point | Verdict | Logged as |
|---|---|---|---|
| 1 | Keep MT5 trading permissions disabled | **UPHELD** (environment, not repo) | A25 |
| 2 | Stop-loss contradiction | **UPHELD, REDIAGNOSED** — worse than claimed | A20, A21 |
| 3 | Partial-profit mathematics | **UPHELD** | A23 |
| 4 | Closed candles only | **ALREADY SATISFIED**; timestamp reporting is thin | — |
| 5 | Risk per trade 0.5% | **DECISION REQUIRED** | A22 |
| 6 | Asian session 22:00–07:00 UTC | **DECISION REQUIRED** — conflicts with implementation | A24 |
| 7 | Spread as a percentage of R | **ALREADY SATISFIED** — expressed differently | — |
| 8 | Trade only the Sweep setup for now | **DECISION REQUIRED** — sound, unenforced | A13 |
| 9 | Do not chase; signal vs executable price | **ALREADY SATISFIED** structurally | — |
| 10 | Never use fixed lot size | **ALREADY SATISFIED** | — |
| 11 | Reject sub-minimum volume | **ALREADY SATISFIED** (G9) | — |
| 12 | Four-state decision `BUY/SELL/WAIT/INVALID` | **NOT APPLICABLE** as stated | — |
| 13 | Replace the system prompt with M15-SESSION-SWEEP v1.0 | **NOT APPLICABLE** — that is a fork | — |

---

## 1. MT5 permissions — UPHELD, and it is the most valuable point in the review

The *project* is read-only and that is enforced by a test. But the review is right that the
guarantee is narrower than it looks. The assistant session operating this project has an MT5
connector loaded that exposes `place_market_order`, `place_pending_order`, `modify_position`,
`close_position`, `close_all_positions`, and `cancel_all_pending_orders`, among others.
`tests/test_safety.py` inspects `MT5ReadOnlyGateway`; it cannot see the connector.

Adopt the recommendation as written: `MT5_TRADING_ENABLED=false`, `MT5_DEMO_ONLY=true`, or a
read-only connector variant. Logged as **A25**.

The related claim that "Allow algorithmic trading" need not be enabled is already true and
already documented — `README.md` and `OPERATIONAL_WORKFLOW.md` §1 both state it.

## 2. Stop-loss — UPHELD in effect, REDIAGNOSED in cause

**The alleged contradiction does not exist.** The review states the workflow requires both
"SL distance = exactly 25% of range" and "SL placed 25% beyond the sweep wick". The code requires
neither in isolation — it takes the *more distant* of the two:

```python
stop_loss = min(candle.low - buffer, entry - r0)      # BUY
```

There is no double requirement, so there is nothing arithmetically inconsistent to resolve.

**What is actually wrong is worse.** Two defects were found while checking this claim:

- **A20 — `G7_STOP_PROTECTION` can never fail.** Since `stop_loss ≤ candle.low - buffer` by
  construction, the gate that verifies the stop clears the sweep is true by definition. Attempted
  falsification at sweep depths of 2×, 7×, 19× and 99× the nominal R returned `G7=True` every
  time. A gate that always passes is worse than no gate: it prints `PASS` into every ticket and
  every `analysis.json` as evidence.
- **A21 — the widening is unbounded.** A deep sweep silently replaces the 25%-of-range risk
  distance with an arbitrarily larger one. Risk cash holds (volume floors down), but the partial
  target collapses to 1.44R, then 0.42R, then 0.16R, then 0.03R, and the 5R take-profit walks
  outside the session range entirely.

So the review's *instinct* — that the stop rule quietly changes the risk model — is correct, and
its proposed fix would genuinely close the hole. Its canonical rule (fix `SL = entry ∓ R`,
validate against the sweep extreme, return `INVALID_STOP_NOT_PROTECTED` otherwise) is a legitimate
design and would make G7 meaningful for the first time.

**The trade-off must be stated before choosing.** The two models are not equal:

| | Current code | Review's model |
|---|---|---|
| Risk cash per trade | fixed | fixed |
| Stop distance | varies, unbounded | fixed at `0.25 × range` |
| Deep sweep | trades with a wider stop and lower volume | rejected as `INVALID_STOP_NOT_PROTECTED` |
| Trade frequency | higher | lower |
| Failure mode | degraded expectancy, silently | missed opportunity, loudly |

A bounded middle option also exists: keep the widening but cap it — reject when
`actual_r > 1.5 × R0` — which preserves most trades while removing the tail. Recorded as an open
decision in `STRATEGY_SPEC.md` §12.

The review's two worked examples are arithmetically correct and were checked. Note that under the
**current** code, its second example (entry 2341, sweep low 2338, R 2.50) is *not* rejected — the
stop widens to below 2338 and the trade proceeds. That is precisely the behaviour A21 describes.

## 3. Partial-profit mathematics — ~~UPHELD~~ → **PARTLY OVERTURNED**

> **Revised after the strategy diagram was adopted as source of truth.** The diagram specifies
> management as "Close 75% at **session range** and Breakeven". That is the opposite boundary, not
> 4R. The code's `partial_target = session_high / session_low` for SWEEP and RANGE therefore
> **conforms to specification**, and the review's prescription — "do not automatically replace the
> 4R target with the opposite Asian boundary" — is incorrect against the source.
>
> What stands is the review's **observation**, below: the two levels are genuinely different
> numbers, the resulting R multiple varies with sweep depth, and the ticket should display both so
> the trader can see which one they are being told to use. The original analysis follows.

The review is right that `4R` and "the opposite Asian boundary" coincide only when the entry sits
exactly on a range boundary, and right that the code conflates them. `RANGE` entries are on the
boundary, so `partial_target_r` is exactly 4.00 (a test pins this). `SWEEP` entries are the
reclaim candle body, so the partial lands below 4R — measured between 1.44R and 0.03R depending
on sweep depth. `TREND` uses `entry ± 4R` directly.

The blended-return arithmetic quoted (`0.75 × 4R + 0.25 × 5R = 4.25R`) is correct, and only holds
for `TREND` and `RANGE`. Logged as **A23**, with the recommendation the review makes: report the
4R price and the opposite-boundary price as separate lines, and say which is the instruction.

## 4. Closed candles only — ALREADY SATISFIED

This is one of the project's strongest properties and needs no change. `cli.analyze_command`
floors `now` to the last M15 boundary and requests candles up to one microsecond before it;
`validate_candles` then rejects any gap, duplicate, or out-of-window bar and verifies OHLC
ordering. No decision can be reached from a forming candle.

The review's *reporting* requirement is partly unmet. `ticket.md` currently carries the UTC
timestamp, the analysis ID and the strategy version in its title, but not the broker server time,
Myanmar time, or the last closed candle timestamp — although the full candle list and the derived
broker offset are both in `analysis.json`. Surfacing three lines on the ticket is a low-risk
rendering change and a fair suggestion; it is not a correctness gap.

## 5. Risk per trade — DECISION REQUIRED

The review asserts the established policy is 0.5% and that 1% was carried over from an example.
The active config is 1% FX / 2% gold, and `STAGE1_QUALIFICATION.md` records that as a *completed*
qualification item — so if 0.5% is the true policy, the qualification evidence is itself
mis-stated. Logged as **A22**.

The related recommendation — no more than two failed session trades per day — has no mechanism
behind it. `maximum_trades_per_symbol_session` is parsed and never read (A13), so there is
currently no overtrading guard at all. If this limit matters, it needs a gate.

Not applied. Changing `risk_percent_fx` alters the config hash and invalidates every stored
artifact for Stage 1.

## 6. Asian session 22:00–07:00 UTC — DECISION REQUIRED, and it is the big one

The implementation uses 00:00–08:00 UTC / 32 candles. The review specifies 22:00–07:00 UTC —
nine hours, 36 candles. Its Myanmar conversion is correct (UTC+6:30 → 04:30–13:30), so the review
is internally consistent; it simply describes a different session.

No document in the project settles which is right, because the v2.2 source
(`Session_Trading_Hybrid_Workflow_v2.2.md`) is still missing. If the review is correct, every
session level and every stored artifact was computed from the wrong window. Logged as **A24** and
flagged as the highest-consequence open question in the project.

## 7. Spread as a percentage of R — ALREADY SATISFIED

The review asks for spread to be reported relative to R and to invalidate the trade when
excessive. Gate G4 already does exactly this, expressed differently. Since `R0 = 0.25 × range`:

```
range ≥ 40 × spread   ⟺   4·R0 ≥ 40 × spread   ⟺   spread ≤ 0.10 × R0
```

G4 is therefore a "spread must not exceed 10% of nominal R" filter. This equivalence has been
added to `STRATEGY_SPEC.md` so it is not re-derived every time. One caveat worth noting: the test
is against nominal `R0`, not the widened `actual_r`, so on a deep sweep the effective spread cost
per R is *lower* than G4 assumes — a conservative direction.

## 8. Trade only the Sweep setup — DECISION REQUIRED, and sound

Reasonable and consistent with `STAGED_IMPLEMENTATION.md`, which requires one strategy version at
a time with independent evidence. The code currently emits `RANGE` and `TREND` as approvable
setups with no way to disable them short of editing the engine. If you want sweep-only operation,
it needs a config switch (for example `enabled_setups: [SWEEP]`) and a gate — not a note in a
document that the engine cannot read.

## 9–11. Chasing, lot sizing, volume bounds — ALREADY SATISFIED

- **Chasing** is structurally prevented: every proposal is a `{SIDE}_LIMIT` order at a
  precomputed price. The engine never proposes a market order. The ticket does not currently
  display signal price versus current executable price side by side, which would make the
  protection visible; bid and ask are shown.
- **Fixed lot size** is impossible — volume is always derived from
  `order_calc_profit` and floored to the broker step.
- **Sub-minimum volume** is rejected by G9 (`volume_min ≤ volume ≤ volume_max`).

## 12. Four-state decision output — NOT APPLICABLE as stated

The review proposes `BUY / SELL / WAIT / INVALID`. The implementation uses a different but
equivalent decomposition: a **status** (`APPROVED_FOR_MANUAL_ENTRY` / `PROVISIONAL_RANGE_SETUP` /
`NO_TRADE` / `EXPIRED`), a **side** (`BUY` / `SELL`), and a **setup** (`SWEEP` / `RANGE` / `TREND`
/ `NONE`), with every rejection attributable to a named gate.

This carries strictly more information than a four-state enum — `WAIT` and `INVALID` both map to
`NO_TRADE` plus the specific failing gate. Adopting the review's enum would lose the gate
attribution that Stage 1 depends on. The review's underlying requirement — never emit a setup
merely because price is near a level — is already met: setups require a closed-candle sweep with
close-back-inside, or an explicit classification.

## 13. Replacement system prompt — NOT APPLICABLE

The supplied `M15-SESSION-SWEEP v1.0-draft` prompt is a different strategy, not a patch to SSPF
v2.2: different session window, different risk percentage, single symbol, no efficiency-ratio
classification, no gate model, and a market-style entry at the reclaim close rather than a limit
proposal. Adopting it would fork the project and orphan the journal, the config hash lineage, and
both lifecycle stages.

The useful content in it has been extracted into the findings above. If you want that strategy,
it should be a **new** strategy ID with its own spec and its own evidence set — not a rewrite of
v2.2's prompt.

---

## What the review got right, in one line each

1. The read-only guarantee is narrower than it looks — correct, and worth acting on today.
2. Something is wrong with the stop rule — correct, and the real defect is more serious.
3. 4R and the opposite boundary are not the same number — correct.
4. Spread must be bounded relative to R — correct, and already implemented.
5. Don't run three setups on one evidence set — correct, and currently unenforceable.

## What it got wrong

1. There is no arithmetic contradiction in the stop rule; there is an unbounded substitution.
2. The 22:00–07:00 session is asserted, not reconciled against the implementation.
3. The four-state output would lose gate attribution.
4. The replacement prompt is a fork presented as a correction.

---

## Open decisions requiring sign-off

| # | Decision | Default if unanswered | Blast radius |
|---|---|---|---|
| D1 | Stop model: unbounded widening (current), capped widening, or fixed-R with rejection | current | changes trade selection and expectancy |
| D2 | Reference session: 00:00–08:00 UTC (current) or 22:00–07:00 UTC | current | invalidates all stored artifacts |
| D3 | Risk per trade: 1%/2% (current) or 0.5% | current | invalidates all sizing evidence |
| D4 | Setup scope: all three (current) or `SWEEP` only | current | reduces trade count |

Each of D1–D4 changes the config hash or the engine, and therefore starts a new evidence set.
`STAGED_IMPLEMENTATION.md` requires one change at a time.

---

# Part B — Proposed three-phase operational workflow

**Overall verdict: REJECT as an operating model. Adopt one item, extract three.**

The proposal is a well-organised description of how this project worked *before* v2.2 — a
prompt-driven analyst computing levels conversationally. Adopting it would move the calculation
out of a tested pure function and into an LLM turn, which discards, in a single step: the twelve
gates, the config hash, the deterministic artifacts, the journal reconciliation, and both
lifecycle stages. Every safeguard in this project exists below the prompt layer.

The core problem is one sentence: **it asks Claude to calculate what `sspf.py analyze` already
calculates deterministically.** An LLM computing a session high from a candle dump is
non-reproducible, unversioned, ungated, and unauditable. The same request routed through the CLI
produces `analysis.json`, `ticket.md`, `chart.png`, a journal row, and a config hash.

## B.1 Item-by-item

| Phase | Instruction | Verdict |
|---|---|---|
| 1.1 | "Allow algorithmic trading toggled **ON**" | **REJECT — safety regression** |
| 1.1 | Test MCP connectivity before trading | **ADOPT** — this is `python sspf.py health` |
| 1.2 | Feed Claude the strategy rules each session | **REPLACE** — see `SESSION_PROMPT.md` |
| 2.1 | "Fetch the last 100 candles on M15" | **REJECT — wrong data-selection model** |
| 2.1 | "Identify the higher timeframe bias trend" | **REJECT — the strategy is M15-only; an H1 input would be an invented rule** |
| 2.2 | Ask Claude to classify Range/Trend/Sweep | **REJECT — replaces the engine with a prompt** |
| 2.3 | Standardised trade ticket | **ALREADY SATISFIED — and stricter** |
| 2.4 | Visual verification in MT5 before entry | **ADOPT — already mandated** |
| 2.4 | "Calculate your lot size based on your risk tolerance" | **REJECT — bypasses G9/G10/G11** |
| 2.3 | "BUY LIMIT / **MARKET**" | **REJECT — market entry is not authorised** |
| 3.1 | Ask Claude to check open positions | **REPLACE** — `sspf.py monitor --analysis-id` |
| 3.2 | Manual 75% close and breakeven move | **ALREADY SATISFIED** |
| 3.2 | "Trail the remaining 25% behind structure" | **UPHELD IN PRINCIPLE** — trailing *is* specified for TREND; the instruction is too vague to follow (revised) |
| Follow-up | Screenshot-annotation tooling | **UNNECESSARY — already rendered deterministically** |
| Follow-up | "Would you like a ready-to-use system prompt?" | **YES — delivered as `SESSION_PROMPT.md`** |

## B.2 The rejections that matter

### Algorithmic trading must stay OFF

The proposal opens by requiring `Allow algorithmic trading` to be enabled. This project requires
the opposite, and the code proves the toggle is irrelevant: `expert_allowed` is captured into
`AccountSnapshot` and **read by no gate**. Nothing in SSPF needs it. Enabling it only widens the
surface through which an order could reach the broker — the exact exposure logged as A25, which
Part A of this document upheld. Leave it off.

### "Last 100 candles" is the wrong data model

`copy_rates_from_pos`-style relative fetching has no session anchor. The engine instead requests
an exact UTC range and then validates that it received precisely 32 contiguous M15 bars with
correct OHLC ordering, after deriving the broker's whole-hour offset from a cross-symbol
consensus. Swapping to "the last 100 candles" reintroduces the broker-offset class of error that
`mt5_gateway.broker_utc_offset` exists to eliminate, and removes the contiguity check entirely.

### Manual lot sizing silently disables three gates

The proposal has the human compute volume from "1% risk divided by the 25% SL distance". The
engine computes it from `order_calc_profit`, floors to the broker volume step, then applies:

- **G9** volume within broker min/max,
- **G10** proposed risk plus today's used risk within the daily limit,
- **G11** drawdown below the configured boundary.

A hand-calculated lot passes none of these. It also detaches the position from the journal, so
`match_active` cannot reconcile it and every subsequent daily-risk calculation is wrong.

### The proposal's own example demonstrates finding A23

Its ticket instructs "close 75% at $2,350.00 (Asian High)" and separately labels the model 4R.
With entry 2341.00 and R 2.50:

```
(2350.00 - 2341.00) / 2.50  =  3.6R      not 4R
4R price would be 2351.00,  5R is 2353.50   ✓ (its 5R figure is correct)
Blended:  0.75 × 3.6R + 0.25 × 5R = 3.95R      vs  4R model: 4.25R
```

The opposite boundary and the 4R price are different levels, exactly as Part A §3 concluded. The
proposal reproduces the defect rather than correcting it. Its 5R arithmetic is right.

### Trailing stops — verdict revised

> **Revised after the complete strategy diagram was supplied.** The original verdict here was
> "REJECT — trailing rules do not exist". That was wrong. The source specifies TREND management as
> "Close 75% at 4R **and Trail**", so trailing is a required part of the strategy and the
> proposal was right to raise it. The verdict changes to **UPHELD IN PRINCIPLE, UNUSABLE AS
> WRITTEN**.

What remains valid is the objection to the *specific* instruction. "Trail the remaining 25% behind
key structural highs/lows" supplies no definition of a structural point, no confirmation
requirement, and no invalidation rule, so two people following it would trail differently.
Trailing is *specified as required* but *undefined in mechanics* — the gap is now tracked as
finding A26 and decision D4, and it applies to `TREND` only. Trailing a `SWEEP` or `RANGE`
position remains wrong: those are managed to breakeven.

Until the mechanics are defined, a trailed TREND trade cannot be judged `rule_compliant` for
Stage 2, because there is no rule to judge it against.

## B.3 What was adopted

The proposal's closing question — a ready-to-use session prompt — was the useful part, and it has
been built: **`SESSION_PROMPT.md`**. The corrected version inverts the proposal's premise. Rather
than instructing Claude to fetch candles and compute levels, it instructs Claude to **run the CLI
and never compute anything itself**, then read back the gate results. It preserves the health
check, the visual-verification step, and the manual-execution discipline the proposal got right.
