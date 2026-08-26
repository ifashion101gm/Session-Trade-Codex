# Strategy ledger

Append-only version history. **Nothing in this file is ever edited or deleted.**
A rule that turned out wrong is superseded by a new version that says so; the old
entry stays, with its results, so the mistake stays visible.

Machine record: `versions/ledger.json` · Tool: `scripts/strategy_version.py`

---

## Why this exists

`outputs/` holds nine folders of Oct-2022 results spanning **−4.6R to +13.9R**, and
nobody can now say which rule set produced which number. Every one of them was a
real backtest. Collectively they are worthless, because the thing they measured
was never recorded alongside the number.

A result is a claim about a rule set, on a dataset, run by some code. Drop any one
of the three and it stops being evidence.

---

## The four rules

**1 · A version is its rules.** The id is the sha256 of the spec plus the engine.
Two people writing the same rules get the same id; changing a threshold by 0.01
makes a new version whether or not anyone remembers to say so. You cannot quietly
edit a live strategy.

**2 · A result names three hashes** — rules, data, code. `record_result` refuses a
number that cannot. Code hash carries `-DIRTY` when the working tree is uncommitted,
because a result from an uncommitted tree is not reproducible and should say so.

**3 · The ledger is append-only.**

**4 · Every hypothesis is counted before its result is known.** A strategy chosen
from forty variants needs a far higher bar than one tested once, and the only
honest way to apply that is to have counted. The tool raises the significance
threshold automatically as the count grows.

## Lifecycle

```
research -> candidate -> paper -> live -> retired
                 |          |       |
                 +----------+-------+----> rejected
```

Forward transitions require a recorded result — the tool refuses without one, and
refuses to skip stages. **Rejection and retirement need nothing.** Killing a
strategy is always allowed; that asymmetry is deliberate.

---

## Lineage

```
SSPF v2.1  ->  SSPF v2.2  ->  ASIAN_SESSION_V1  ->  SESSION_CASCADE_V1
                                      |
                     SESSION_TRADING_SOURCE_WORKFLOW_V2
                                      |
                                      v
                            SESSION_FLOW_V1   <- first version under this ledger
                                      |
                                      v
                          (successor: + BIAS TREND filter)
```

| Version | Id | Stage | Note |
|---|---|---|---|
| SSPF v2.1 / v2.2 | `fddb7465…`, `92279f3d…` | superseded | pre-ledger |
| `ASIAN_SESSION_V1` | `2530b751…` | superseded | pre-ledger; `STRATEGY_SPEC.md` carries a banner |
| `SESSION_TRADING_SOURCE_WORKFLOW_V2` | — | superseded | source of the leg-2 window, later re-signed on evidence |
| `SESSION_CASCADE_V1` | — | superseded | pre-ledger |
| **`SESSION_FLOW_V1`** | **`a6188c364c63f39f`** | **rejected** | see below |

---

## `a6188c364c63f39f` · SESSION_FLOW_V1

**Registered** 2026-08-16 · **research → rejected** same day.

The trader's Session Trading Strategy flowchart (1BullBear, *Episode 18 — Asian
Session Trading*) implemented literally, with the sweep read in the **reference**
session. Supersedes ASIAN_SESSION_V1, SSPF v2.2 and SOURCE_WORKFLOW_V2.

### Results

| Sample | Dataset | n | net R | expectancy | PF | DD | t | survives? |
|---|---|---|---|---|---|---|---|---|
| in-sample | Oct 2022, 3 sym, 15 d | 63 | +27.124R | +0.431R | 1.590 | 6.330R | 1.46 | **no** |
| in-sample | Aug 25–Apr 26, 3 FX, 262 d | 767 | +22.723R | +0.030R | 1.035 | 45.323R | 0.40 | **no** |

**10 hypotheses tested → Bonferroni threshold |t| > 2.81.**

The Oct-2022 result passed all four lifecycle gates and was described in `STATUS.md`
as a research candidate. **At t=1.46 against a 2.81 threshold it never survived
correction.** The gates were passed; the evidence was not there. That is precisely
what this ledger is built to catch, and it caught it retroactively on the first run.

### Hypotheses counted

```
 1  efficiency-ratio threshold sweep 0.25/0.30/0.35/0.40/0.45
 2  slippage stress 0.2 -> 2.0 pips
 3  leave-one-symbol-out x3
 4  leg-2 reference window scan, 30 candidate windows
 5  collision policy STOP_FIRST vs TARGET_FIRST
 6  range test: efficiency ratio vs source middle-portion
 7  middle-portion band sweep 30/40/50/60/80%
 8  symbol universe: with and without XAUUSD
 9  bias filter candidates x7
10  final: ER + 3 FX, no gold
```

This undercounts. The nine pre-ledger folders in `outputs/` are further hypotheses
that were never registered, so the true threshold is higher than 2.81.

### Decisions attached to this version

| # | Decision | Basis |
|---|---|---|
| §5.3b | Leg-2 window `07:00–12:00` | `[BENCHMARK]` — reproduces the Oct-6 chart entry to 0.15 pip; independently confirmed by the source doc hours later |
| — | XAUUSD dropped | gross **−2.455R before any cost**; 45% of R paid in spread |
| §4-B | Source "middle portion" rejected, efficiency ratio kept | all 5 interpretations negative; incumbent the only positive one |
| §4-A | **Bias — declined** | source says "you never invent it"; this project already carries one invented rule on record |
| §4-C | Trail signed by the source | *"75% at 4R, then trail behind each new M15 swing"* — **not yet implemented** |

### Why rejected

Fails 3 of 4 lifecycle gates in its best configuration, at t=0.40 against 2.81.

**Scope of the rejection, stated precisely.** This version omits the BIAS TREND
filter the source mandates, so it measures an unfiltered superset — roughly twice
the trades the source strategy would take. A successor implementing bias is a
**new version**, not a revision of this one, and it gets its own id, its own
hypothesis count and its own evidence.

### Bias candidates tested — none survived

Ex-gold, 767 trades unfiltered at +0.030R. Every signal computable at the reference
close, no lookahead:

```
reference session travel   636   +31.70R   +0.050R   t 0.59
previous day direction     365   +35.42R   +0.097R   t 0.87   <- best
TS-momentum 1 day          467   +12.40R   +0.027R   t 0.27
TS-momentum 1 week         430   +12.67R   +0.029R   t 0.29
TS-momentum 1 month        419   -38.48R   -0.092R   t -0.92
TS-momentum 3 months       508   -27.12R   -0.053R   t -0.58
TS-momentum 6 months       644   +37.63R   +0.058R   t 0.69
```

Best is t=0.87 against a 7-hypothesis threshold of 2.69. **Nothing survives.**

Time-series momentum has the strongest published evidence of any directional
signal — Moskowitz, Ooi & Pedersen (2012) report a 1.28 composite Sharpe across 58
instruments including 12 currency forwards. It does not transfer to a 5-hour
session filter here, which is unsurprising: the documented effect operates on a
12-month horizon.

**The bar to clear:** a bias filter must discard **7.5% of losers while keeping
every winner** to reach +0.10R/trade. Removing trades at random moves expectancy
by exactly zero.

---

### Conformance audit vs the source diagram — 2026-08-16

Checked element by element against the flowchart frame from *Episode 18*, and the
geometry verified numerically on real sessions rather than by reading the code.

| # | Diagram element | Engine | |
|---|---|---|---|
| 1 | Tree shape: `IS RANGE SESSION?` → ✗ TREND, ✓ → `SWEEP DURING SESSION?` → ✓ SWEEP / ✗ RANGE | same branch order | ✅ |
| 2 | `SWEEP DURING SESSION?` — during the **graded** session | candle making the extreme closes its body back inside | ✅ |
| 3 | SWEEP entry = sweep candle body | `e = body edge` | ✅ |
| 4 | RANGE entry = Session Top / Bottom | `e = lv["hi"]` or `lv["lo"]` | ✅ |
| 5 | TREND entry = Middle of the range | `e = lv["mid"]`, verified `= lo + 0.5·rng` | ✅ |
| 6 | STOPLOSS = 25% of range, all three | verified `|e − sl| = 0.25·rng` exactly | ✅ |
| 7 | TARGET = 5× Risk to Reward, all three | verified `|tp2 − e| = 5R` exactly | ✅ |
| 8 | MGMT sweep/range: close 75% **at session range** + breakeven | tp1 = opposite boundary, then `sl = e` | ✅ |
| 9 | MGMT trend: close 75% **at 4R** | tp1 verified at exactly 4.00R | ✅ |
| 10 | MGMT trend: **and Trail** | `sl = e` — breakeven, no trail | ❌ **GAP** |
| 11 | `BIAS TREND` ∧/∨ at the head of the tree | computed from `close_location ≥ 0.50` | ❌ **DIVERGES** |
| 12 | `IS RANGE SESSION?` — definition | `efficiency_ratio ≤ 0.35` | ⚠️ **the diagram defines nothing here** |

**9 of 12 conform exactly.** The entry/stop/target/management geometry — the whole
of the source's table — reproduces to floating-point equality.

**Item 12 matters more than it looks.** The diagram poses the question and gives no
test. So the efficiency ratio is an interpretation, *and so is the "middle portion"
wording in the trader's typed spec* — that text is a gloss on the diagram, not the
diagram. Rejecting it (all five bands negative) rejects one interpretation in
favour of another, not the source. §4-B remains genuinely `[UNSIGNED]`.

**Item 11 is the live divergence.** In the frame, `BIAS TREND` sits at the head with
an up and a down chevron — an input with two states, not a computed quantity. The
engine derives direction from it, so the mandated NO-TRADE branch can never fire.

**Item 10 is unimplemented, not wrong.** The source says trail; the engine holds
breakeven. It is the only signed rule not yet built, and it lands on TREND — the
bucket carrying what edge remains (+0.076R/trade ex-gold over 493 trades).

**Verdict: the version is still relevant.** The rejection of `a6188c364c63f39f`
stands and its recorded scope note is confirmed by this audit — it measures the
source geometry faithfully, minus the bias filter, minus the trail.

### External review, 2026-08-16 — four items raised, five confirmed

Full spec: **`ENGINE_FIX_SPEC.md`**. Summary of what the review changed.

| Fix | Item | Status |
|---|---|---|
| **0** | **RANGE SETUP is unreachable** | **found during the review, blocks the rest** |
| 1 | bias circularity — `resolved_at ≤ session.start` | confirmed, **and it reaches further** |
| 2 | trail: swing width, confirmation lag, ratchet, floor; `T-cap`/`T-open` | confirmed |
| 3 | "middle portion" was a reviewer's gloss, not the diagram | confirmed, **retracted in §4-B** |
| 4 | `sweep candle body` is a two-price object | confirmed |

**FIX 0 outranks all of them.** `RANGE` fired **0 times in 1030 trades** and 0 in 63.
`swept = body < session_high` is trivially true unless a candle closed exactly on its
own high, so `SWEEP` is taken every time and one of the diagram's three buckets is
dead code. Every bucket statistic in the results above is a measurement of a tree
with one fork wired to a constant.

**FIX 1 is worse than the review could see without the source.** The review expected
bias to be a *veto* on SWEEP and TREND and a *selector* only on RANGE. In this engine
`ext = lv["hi"] if bear else lv["lo"]` — **bias chooses which side to hunt the sweep
on**, so the source's "trade away from the swept side" never executes. The review's
caveat about RANGE understating the difference does not bind, because RANGE
contributed zero trades. The artefact is larger and elsewhere: **all 370 SWEEP trades
had their direction set by a statistic of the session being graded.**

**Hypothesis count raised 10 → 16**, all five fixes plus the pre-registration
declared *before* measurement. Bonferroni threshold is now **|t| > 2.96**. The
Oct-2022 result stands at t=1.46 and the 12-month at t=0.40.

---

## `c121748f69283b55` · ST04_07_EXECUTION_ATTRIBUTION_V1

**Registered** 2026-08-25 · stage `research`.

Not a successor to `SESSION_FLOW_V1` or any other entry in this ledger — a standalone research
study, side-by-side with `ASIAN_SESSION_V1` and the `SESSION_V2` research track, answering one
narrow question: for Entry 2 (Sweep) signals only, how much of the realized edge is signal versus
execution fill model. Spec: `ST04_07_EXECUTION_ATTRIBUTION_V1_SPEC.md`. Engine:
`scripts/st04_07_execution_attribution_v1.py`. Config: `config/st04_07_execution_attribution_v1.yaml`.

Reuses the `ER_ONLY_V2` regime classifier (`ER < 0.40` → RANGE → Sweep-qualification, same
threshold family as `SESSION_FLOW_V2_SIMPLE`) and a completed-Asian-box Sweep-qualification rule,
but as an independent implementation — it does not call into `session_strategy/` and mutates
nothing in `config/strategy.yaml`.

Compares two fill models on one shared, immutable signal ledger
(`ST04_07_SWEEP_SIGNAL_LEDGER.csv`):

- **`E2-A_NEXT_MARKET`** (control) — fills at the first M1 quote after the sweep bar closes.
- **`E2-B_SWEEP_REFERENCE_LIMIT`** (challenger) — resting limit at the swept reference level,
  60-minute expiry, unfilled orders tracked as opportunity cost rather than a loss.

Fixed risk geometry across both (`SL = sweep extreme ± 1.0 pip`, `TP = 1.5R`) isolates execution
attribution from trade-management variables. No result has been recorded yet — `promotion_allowed_
from_this_sample: false` and no hypotheses are registered until the funnel in the spec §8 is run
against authoritative M1 data.

No MT5 calls anywhere in the engine (read or write). Not authorized for demo or live execution.

---

## `7728ae9d414865d7` · R8_OBM_V1

**Registered** 2026-08-25 · stage `research` · **not a Python component of this repo.**

A compiled MQL5 Expert Advisor (`R8_OBM_V1_EA`, magic `8101501`) discovered live-attached to a
EURUSD M15 chart in the MT5 terminal itself. Source, binary, and audit journal live in the
terminal's own data folder (`%APPDATA%\MetaQuotes\Terminal\...\MQL5\Experts\`), not in this git
repository — this ledger entry exists only to track its governance status in one place. Full
detail: `R8_OBM_V1_SPEC.md`, `config/r8_obm_v1.yaml`.

Same underlying idea as `mt5_range_bar_live.py` (tick-built synthetic range bars, one-bar
momentum, fixed R:R) but an independent implementation — different magic number, no shared code,
and materially better safety design: an unconditional hard-coded real-account block plus an
`InpAllowDemoTrading` gate (default and, as of this validation, actually set to `false`) that
keeps it signal-only-logging even on a permitted demo account.

Related to (not a revision of) the trader's own external research finding `ST-01 RANGE8
MOMENTUM → REJECT V1` (bid/ask-realistic PF 0.81) — this EA appears to forward-test that same
idea live, in signal-only mode, which is reasonable as a sanity check but must not be treated as
relitigating that rejection without a real forward-test sample and review.

**Validated 2026-08-25**: currently on the correct demo account (`VantageMarkets-Demo`,
`...746`), `InpAllowDemoTrading=false` confirmed via both the chart panel and terminal log,
journal shows 6 completed range bars / 0 orders attempted since 2026-08-24. **Also found**: the
terminal was briefly attached to a REAL account the same day (`MQL5/logs/20260825.log`,
19:00:27, `"Account mode: REAL"`) while this EA was loaded — its hard block correctly prevented
any order, but it is the first evidence any trading component in or around this project has been
attached to a real account, even momentarily.

No trades, no hypotheses, no results recorded — nothing to promote yet.

---

## `9bd4c67a8404c8f9` · SMC_3R_V1

**Registered** 2026-08-26 · stage `research` · **not a successor to any existing entry.**

An externally-authored, complete SMC (Smart Money Concepts) implementation supplied ready-made:
Asian-session/PDH/PDL liquidity sweep → displacement + CHoCH (change of character) confirmed
against a causal 3-bar fractal → immediate next-bar FVG (fair value gap) → limit entry, stop
beyond the sweep extreme, fixed 3R target. M5 signal detection, M1 fill/exit simulation with
spread, data-gap detection, and a same-bar-SL/TP-touch tie-break. Full detail: `SMC_3R_V1_SPEC.md`.
Code: `smc_3r_v1/` (`reference_levels.py`, `smc_features.py`, `smc_state_machine.py`, `matcher.py`).

Placed in its own package and two internal imports adjusted to package-relative
(`from .reference_levels import ...`) so the four modules work as supplied — no rule, threshold,
or geometry was changed from what was given.

**Known gap at registration:** the test suite this was written against
(`tests/test_smc_3r_v1_complete.py`) was referenced in the handoff but never supplied, and did
not exist in this repository. Only a local import/execution smoke test on synthetic OHLC data had
been run.

### Stage 0 — 2026-08-26

Wrote `tests/test_smc_3r_v1_complete.py` from scratch against the registered package (no prior
artifact existed to recover, despite the module docstrings referencing this exact filename) — 20
hand-built deterministic fixtures, no randomness, covering `reference_levels.py` (4),
`smc_features.py` (4), `PendingOrder` geometry (2), session-window gating (2), and
`smc_state_machine.py` integration via `scan_dataset()` (5: BUY order construction, SELL order
construction, sweep invalidation past `max_sweep_bars`, setup abandonment when the immediate-FVG
bar fails with no retry, zero orders outside the session window), plus `matcher.py` (3: limit
fill detection, same-bar SL/TP touch marked as loss with `intrabar_ambiguity`, data-gap
detection).

```
collected = 20
passed    = 20
failed    = 0
errors    = 0
relevant warnings = 0
```

**One real finding, left unfixed by design:** `smc_state_machine.py` divides `bar['body'] /
bar['median_body_20']` when building `disp_body_ratio` (lines ~129, ~144) with no zero-guard —
a `RuntimeWarning: divide by zero` (→ `inf` in that meta field) whenever the trailing 20-bar
median body is exactly zero, which a flat/no-movement market can produce. Worked around at the
test-fixture level (tiny nonzero baseline body) rather than patched in the frozen module — fixing
it is a V2 concern, not a silent V1 mutation.

```
stage        = research
stage0       = passed
verification = deterministic_unit_and_integration (20/20)
execution_authority = none
```

No hypotheses, no backtest result, no MT5 wiring, no magic number. Not authorized for demo or
live execution. Nothing about this entry supersedes `ASIAN_SESSION_V1` / `SESSION_SIMPLE_V1`,
`SESSION_FLOW_V1`, `R8_OBM_V1`, or `ST04_07_EXECUTION_ATTRIBUTION_V1` — it runs alongside them,
untouched by this registration.

Frozen at Stage 0 pass: `1.5x` displacement multiple, `0.60` body efficiency, `8`-bar sweep
window, `2`-pip SL buffer, `5`-minute activation delay, `25`-minute expiry, `3R` target. Any
change to these is `SMC_3R_V2`, not a revision of this entry.

---

## `c0765fca04f80794` · ASIAN_SESSION_V2

### 2026-08-26 — canonical-session force migration

Registered as part of the owner-directed force migration onto `CANONICAL_SESSION_WINDOWS_V1`
(`CANONICAL_SESSION_MIGRATION_REPORT.md`, `CANONICAL_STRATEGY_VERSION_MAP.md`). Successor to
`ASIAN_SESSION_V1` (`config/strategy.yaml`) — see that engine's own entry immediately below,
which this migration flipped to `LEGACY_FROZEN`.

`ASIAN_SESSION_V1`'s `00:00-07:00` Asian window is a trader-confirmed truth source (exhaustive
search against the trader's own MT5 export, 2026-08-15 correction note in `config/strategy.yaml`)
that golden fixtures and `benchmarks/truth_source_setups.json` depend on. There is no equivalent
confirmed truth for `00:00-06:00`, so V1 was frozen byte-for-byte rather than renumbered, and this
new version — same signed setup/risk/cost rules, evaluated on a canonical `[00:00,06:00)` box
instead — was registered separately rather than silently reusing V1's identity for a materially
different reference session.

```
stage                = research
spec                 = ASIAN_SESSION_V2_SPEC.md (sha256 b47efb75...)
engine               = session_strategy/engine.py (sha256 e2d48979...)
supersedes           = ASIAN_SESSION_V1 (config/strategy.yaml, LEGACY_FROZEN 2026-08-26)
execution_authority  = none  (config/strategy_v2.yaml: mode analysis_only, all
                               execution_permissions false, no parameter_signoff)
```

No hypotheses, no backtest result, no MT5 wiring. `symbols.*.minimum_range`/`maximum_range` are
copied from V1 unrecalibrated for the narrower 6-hour window — flagged, not silently inherited
(see `governance.provisional_parameters` in `config/strategy_v2.yaml`, and
`CANONICAL_STRATEGY_VERSION_MAP.md`).

---

## `ASIAN_SESSION_V1` (`config/strategy.yaml`) — status change, no re-registration

### 2026-08-26 — flipped to LEGACY_FROZEN

Pre-dates this ledger tool (never had its own registered id here — see `SESSION_FLOW_V1`'s
`supersedes` field above, which already names it). As part of the canonical-session force
migration, its execution authority was explicitly revoked: `mode` changed from `trading_enabled`
to `analysis_only`, and `execution_permissions.{submit_orders,modify_orders,close_positions}`
from `true` to `false`. Its session window (`00:00-07:00`, 28 M15 candles) is **not** changed —
it remains the trader-confirmed truth source golden fixtures and
`benchmarks/truth_source_setups.json` depend on, frozen for reproducibility, not deleted. This is
a status change, not a rules change (`session_strategy/config.py`'s SSOT assertion for
`ASIAN_SESSION_V1` is byte-identical to before this migration), so no new version id is
warranted — see `CANONICAL_SESSION_MIGRATION_REPORT.md` §4 and `CANONICAL_STRATEGY_VERSION_MAP.md`
for the full reasoning. Re-enabling execution authority is an explicit, separate decision, not a
side effect of `ASIAN_SESSION_V2`'s existence or of this migration succeeding.

---

## Out-of-sample reserve

`data/sealed/` — May–Aug 2026, four symbols, 4 datasets, **unopened**. Every number
above is in-sample. Do not open it until a successor version's rules are frozen and
registered; it can only be spent once.
