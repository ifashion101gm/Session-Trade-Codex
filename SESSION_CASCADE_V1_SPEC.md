# SESSION_CASCADE_V1 — Strategy Specification

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

Strategy ID: **`SESSION_CASCADE_V1`** · Contract version: **1.0-draft** · Spec date: **2026-08-15**
Config hash: **not yet assigned** — assigned on first config load after §9 sign-off.

**§0 is the source of truth.** It is the trader's specification, transcribed from the Session
Trading Strategy flowchart supplied 2026-08-15 and generalised from one session pair to an
ordered cascade of legs. The engine implements it; it does not extend, optimise, or improve it.
Any divergence between code and §0 is a defect, even when the divergence looks better. Where §0
is silent, the engine stands aside and returns `NO_TRADE`.

> **Status: DRAFT — NOT EXECUTABLE.** `G18_CONTRACT_SIGNED` fails closed until every §9 decision
> is signed. Nothing in `outputs/` was produced under this contract.

> Extends `ASIAN_SESSION_V1` (`2530b751134fbf6e`). Two substantive changes: the single
> Asian→London pair becomes a list of legs (§0.1a), and Trend management trails instead of
> resting at breakeven (§0.9, §9-D). **Evidence gathered under `ASIAN_SESSION_V1` does not
> transfer** — different level source per leg, different management on Trend.

---

## 0. Source of truth

### 0.1 Decision flow — per leg

```
Build reference range  →  Validate range and costs ──invalid──→ NO TRADE
                              │ valid
                              ▼
                     Determine session type
                    ┌─────────┴──────────┐
                  RANGE                TREND
                    │                    │
          Was liquidity swept?           │
           ┌────────┴────────┐           │
         yes                no           │
           │                 │           │
      SWEEP setup   RANGE REJECTION   TREND CONTINUATION
           └────────────────┬──────────────┘
                            ▼
            Calculate entry, SL and 4R/5R targets
                            │ risk checks pass
                            ▼
                    Generate trade signal
                            ▼
     Sweep/Range: 75% off at the opposite boundary → stop to breakeven → 5R
     Trend:       75% off at 4R → stop to breakeven → TRAIL  (§9-D)
```

### 0.1a The cascade

A **leg** is one (reference session → execution session) pair. The strategy is identical on every
leg; only the windows change. Legs are evaluated independently, in order. A leg's range is built
from its own reference session and locks at that session's close. **No leg reads another leg's
levels.**

```
LEG 1   reference ASIAN    →  execution LONDON
LEG 2   reference LONDON   →  execution NEW YORK
```

| | Leg 1 | Leg 2 |
|---|---|---|
| Reference session | Asian | London |
| Reference window (UTC) | `22:00 → 07:00` | **§9-A** |
| Reference candles (M15) | 36 | **§9-A** |
| Lock time | 07:00 | **§9-A** |
| Execution window (UTC) | `07:00 → 16:00` | **§9-A** |
| Execution candles (M15) | 36 | **§9-A** |
| New-entry cutoff | 16:00 | **§9-A** |

Leg 2's reference window must equal leg 1's execution window, or the two legs describe different
Londons. That constraint makes §9-A one decision rather than four.

**Config shape.** `session_contract` becomes an ordered list. Each leg carries
`leg_id`, `reference_start_utc`, `reference_end_utc`, `reference_candles`,
`execution_start_utc`, `execution_end_utc`, `execution_candles`. Config load asserts per leg that
`candles == window_minutes / 15`, exactly as the single-leg contract does today.

### 0.2 Time model

All internal calculation is UTC. Myanmar (UTC+6:30) is display only.
Half-open intervals by bar-open time: `start <= bar_open_time < end`.
A session crossing midnight belongs to the date it **ends**.

| Phase | Leg 1 UTC | Leg 1 Myanmar |
|---|---|---|
| Reference construction | 22:00–07:00 | 04:30–13:30 |
| Range locked | 07:00 | 13:30 |
| Execution window | 07:00–16:00 | 13:30–22:30 |
| End of entry window | 16:00 | 22:30 |

Leg 2 equivalents follow from §9-A.

### 0.3 Levels — immutable at the reference close

```
ref_high  = max(high)          midpoint       = ref_low + 0.50 × range
ref_low   = min(low)           risk_unit R    = 0.25 × range
range     = high - low         lower_quartile = ref_low + 0.25 × range
                               upper_quartile = ref_high - 0.25 × range
```

Candles after the lock must never modify these. `R = 0.25 × range` is the stop distance for all
three setups, which is what makes the opposite boundary exactly 4R from an edge entry.

### 0.4 Day rejection

Reject the leg when: `range <= 0`; candles missing or duplicated; range below the configured
minimum or above the configured maximum; spread above the configured limit; warm-up history
unavailable; or the execution candle falls outside the entry window.

**Minimum and maximum range are configured per symbol AND per leg. Gold must not reuse FX limits,
and London ranges must not reuse Asian limits** — see §9-B.

### 0.5 Session classification

Computed on the leg's reference session:

```
net_move         = |ref_close - ref_open|
efficiency_ratio = net_move / range
close_location   = (ref_close - ref_low) / range

RANGE          : efficiency_ratio <= 0.35
BULLISH_TREND  : efficiency_ratio > 0.35 and close_location >= 0.65 and close > open
BEARISH_TREND  : efficiency_ratio > 0.35 and close_location <= 0.35 and close < open
UNCERTAIN      : everything else  →  NO TRADE
```

**0.35 and 0.65 are research parameters, not proven optimal values.** Lock them before each
backtest and never change them after seeing out-of-sample results. They were calibrated on Asian
ranges; whether they carry to a London reference is **§9-B**.

### 0.6 Setup A — Liquidity Sweep

Applies when `session_type == RANGE` and a confirmed sweep occurs in the execution window.

```
Bullish:  candle.low  < ref_low  - sweep_buffer   and  candle.close > ref_low
Bearish:  candle.high > ref_high + sweep_buffer   and  candle.close < ref_high

Rejection-quality filter:
  long  : close >= low  + 0.50 × candle_range
  short : close <= high - 0.50 × candle_range

entry = sweep candle body low (long) or body high (short)
SL    = entry ∓ 0.25 × range
TP1   = opposite boundary; close 75% and move SL to breakeven
TP2   = entry ± 5 × initial_risk
```

The sweep candle must open inside the relevant boundary. Opening outside and merely re-entering
the box is not a new liquidity sweep.

**Structural validation.** The calculated stop must lie beyond the sweep extreme plus the buffer:

```
long  : SL < sweep_candle.low  - stop_buffer
short : SL > sweep_candle.high + stop_buffer
```

If it does not, **reject the trade**. Do not silently enlarge the stop — that would violate the
fixed 25% rule.

### 0.7 Setup B — Range Rejection

Applies when `session_type == RANGE`, no confirmed sweep has occurred, and price rejects a
boundary. Entry at the boundary must never be blind; a rejection candle is required.

```
Long  : candle.low  <= ref_low  + touch_tolerance  and close > ref_low  and close > open
Short : candle.high >= ref_high - touch_tolerance  and close < ref_high and close < open

entry = ref_low (long) or ref_high (short)
SL    = entry ∓ 0.25 × range
TP1   = opposite boundary; close 75% and move SL to breakeven   (exactly 4R)
TP2   = entry ± 5R
```

The rejection candle must open inside the relevant boundary. A candle that opens outside the box
and merely returns inside is not a new Range rejection signal. A breakout candle that closes
convincingly outside the range is not a rejection and invalidates this setup for the leg.

### 0.8 Setup C — Trend Continuation

"Entry at the middle of the range" means a **confirmed retracement into a midpoint zone**, not an
unconfirmed limit order.

```
midpoint_zone = [ref_low + 0.45 × range , ref_low + 0.55 × range]

Bullish : BULLISH_TREND, price retraces into the zone, confirmation candle closes bullish,
          and its low does not trade below lower_quartile
Bearish : BEARISH_TREND, mirrored, and its high does not trade above upper_quartile

entry = midpoint (50% equilibrium)
SL    = entry ∓ 0.25 × range
TP1   = entry ± 4R        TP2 = entry ± 5R
```

An opposite-quartile violation cancels the pending trend setup for that leg. The midpoint entry
is emitted only after a closed confirmation candle; it is never armed blindly at the lock.

### 0.9 Management

1. Open the position with its original stop.
2. **Sweep / Range:** at the opposite boundary close **75%**, and move the remaining stop to entry.
3. **Trend:** at **+4R** close **75%**, move the remaining stop to entry, then **TRAIL** (§9-D).
4. Never move the initial stop farther away.
5. Do not re-enter the same setup after a completed or stopped trade **on that leg**.

> **CHANGE FROM `ASIAN_SESSION_V1` §0.9.** That contract puts trailing out of scope for v1 and
> runs the Trend remainder to 5R from breakeven. The flowchart says *"Close 75% at 4R and Trail."*
> The flowchart governs — but trailing is not yet arithmetic. Until §9-D is signed, `TREND` setups
> return `NO_TRADE` with reason code `TREND_TRAIL_UNSPECIFIED`.

For Sweep and Range the partial is stated as "at the session range". From an edge entry that is
exactly 4R; from a sweep body it is strictly less, because the entry sits inside the range.
**Compute it from the actual fill — never assume 4R.** If it computes below 1.5R, report that and
recommend holding to 5R rather than banking a partial worth almost nothing.

### 0.10 Risk

```
risk_basis        = min(account balance, account equity)
risk_per_trade    = 0.5% of risk basis
maximum_daily_risk = 2.0%     shared across ALL legs, consumed in leg order   ← §9-C
maximum_drawdown  = 15%
one open position per symbol
one accepted trade per symbol per LEG                                          ← §9-C
```

Volume = `risk_amount / (stop_distance × value_per_point_per_lot)`, normalised with broker
minimum, maximum and step, contract size, tick size, tick value, and account-currency conversion.
Reject the order if the normalised volume would exceed the risk limit.

Leg 1 books against the daily budget first; leg 2 sees the remainder. A leg that cannot fit
inside the remaining budget returns `NO_TRADE` with the figure — **never a reduced position**.

### 0.11 Setup priority and exclusivity

```
1. Valid Sweep     2. Valid Range Rejection     3. Valid Trend Continuation     4. No Trade
```

Range and Trend are mutually exclusive because they require different classifications.
Not permitted: a sweep and a range setup from the same candle; long and short at the same
timestamp; more than one accepted trade per symbol per leg; entry on an incomplete candle;
retroactive reclassification.

### 0.12 State machine — instantiated per leg

```
WAITING_FOR_REFERENCE_OPEN → BUILDING_REFERENCE_RANGE → RANGE_LOCKED → SESSION_CLASSIFIED
  → WATCHING_EXECUTION_WINDOW ├ SWEEP_DETECTED ├ RANGE_REJECTION_DETECTED
                              ├ TREND_RETRACE_DETECTED └ WINDOW_EXPIRED
  → SIGNAL_VALIDATION ├ SIGNAL_ACCEPTED └ SIGNAL_REJECTED
  → POSITION_OPEN ├ STOPPED ├ TP1_REACHED → BREAKEVEN_ACTIVE ├ TRAILING_ACTIVE
                  ├ BREAKEVEN_EXIT └ TP2_REACHED
                  └ EMERGENCY_EXIT → LEG_COMPLETE
```

Every transition records its timestamp, candle, reason code, inputs, **and `leg_id`**.

---

## 1. Parameters requiring sign-off

§0 names these but supplies no values. They are a **locked research preset**
(`governance.research_status: PROVISIONAL_LOCKED_FOR_BASELINE`, `optimization_allowed: false`),
not approved values. Do not tune them after seeing out-of-sample results.

| Parameter | Provisional value | Used by |
|---|---|---|
| `sweep_buffer_fraction` | 0.02 × range | how far beyond the boundary counts as a sweep |
| `stop_buffer_fraction` | 0.02 × range | how far beyond the extreme the stop must sit |
| `touch_tolerance_fraction` | 0.05 × range | boundary-touch tolerance for range rejection |
| `rejection_quality_fraction` | 0.50 | sweep close position within its own candle |
| per-symbol, per-leg `minimum_range` / `maximum_range` | `config/strategy.yaml` | day rejection |
| per-symbol, per-leg `maximum_spread` | `config/strategy.yaml` | cost rejection |

`efficiency_ratio_threshold` (0.35) and `close_location_trend` (0.65) are the trader's own research
parameters, carried verbatim.

**Leg 1 carries fingerprinted sign-off `0f2e89f3a44fca01`. Leg 2 carries none** — see §9-B.

### 1.1 Predeclared research grid

Development only, before the sealed out-of-sample period is opened. Selection must not be by
highest historical profit factor alone; use walk-forward.

| Parameter | Baseline | Candidates |
|---|---|---|
| `sweep_buffer_fraction` | 0.02 | 0.00, 0.01, 0.02, 0.03 |
| `stop_buffer_fraction` | 0.02 | 0.00, 0.01, 0.02 |
| `touch_tolerance_fraction` | 0.05 | 0.02, 0.05, 0.08 |
| `rejection_quality_fraction` | 0.50 | 0.50, 0.60, 0.70 |

### 1.2 Governance state

```
specification_status: DRAFT          implementation_authorized: false
demo_execution_authorized: false     live_execution_authorized: false
optimization_allowed: false          research_status: PROVISIONAL_LOCKED_FOR_BASELINE
```

Promotion requires, in order: deterministic unit tests → golden cases → no-look-ahead audit →
baseline backtest → transaction-cost stress → walk-forward → sealed out-of-sample.

**Backtest `SWEEP`, `RANGE_REJECTION` and `TREND_CONTINUATION` separately, AND leg 1 separately
from leg 2**, so neither a setup nor a leg can conceal another's losses. That is six cells, not
one number.

---

## 2. Gate pipeline

Evaluated in order, **per leg**. Several exit early; a `NO_TRADE` legitimately carries fewer
gates than an accepted signal. Every rejection maps to a stable reason code.

| # | Gate | Passes when | Early exit |
|---|---|---|---|
| 1 | `G1_ENVIRONMENT` | demo account, expected server and login suffix | no |
| 2 | `G2_UNIVERSE` | symbol is configured for this leg (exact string) | yes |
| 3 | `G3_BROKER_CLOCK` | offset within ±14h and tick age in `[-5, 300]s` | no |
| 4 | `G4_SESSION_DATA` | configured contiguous closed M15 candles, valid OHLC, execution window valid, spread > 0 | yes |
| 5 | `G5_RANGE_BOUNDS` | `min <= range <= max` for this symbol **and leg** | yes |
| 6 | `G6_SPREAD` | spread ≤ this symbol's maximum | no |
| 7 | `G7_SESSION_CLASSIFIED` | classification is not `UNCERTAIN` | yes |
| 8 | `G8_SESSION_QUOTA` | fewer accepted signals than the per-leg limit | yes |
| 9 | `G9_NEWS_FILTER` | no relevant high-impact event within the blocked window | yes |
| 10 | `G10_SETUP_DETECTED` | a setup qualified in a closed execution candle | yes |
| 11 | `G11_STRUCTURAL_STOP` | on `SWEEP`, the fixed stop clears the extreme plus buffer | yes |
| 12 | `G12_STOPS_LEVEL` | stop distance ≥ broker minimum | no |
| 13 | `G13_VOLUME_BOUNDS` | normalised volume within broker limits | no |
| 14 | `G14_DAILY_RISK` | journal healthy and used + proposed ≤ **shared** daily limit | no |
| 15 | `G15_DRAWDOWN` | journal healthy and drawdown < 15% | no |
| 16 | `G16_EXECUTION_WINDOW` | current time inside this leg's execution window | no |
| **17** | **`G17_LEG_ELIGIBILITY`** | this leg has not already produced an accepted trade for this symbol; cross-leg rule of §9-C satisfied | yes |
| **18** | **`G18_CONTRACT_SIGNED`** | every §9 decision is signed | yes |

`G18` fails closed and is evaluated first in practice: a draft contract must never produce a
tradeable signal.

`status = SIGNAL_ACCEPTED` only when every recorded gate passed **and** a tradeable plan exists.
Otherwise `NO_TRADE`.

---

## 3. Timeframe and candle semantics

**M15 only**, declared explicitly: `timeframe: M15`, `timeframe_seconds: 900`,
`use_closed_candles_only: true`.

Half-open by bar-open time (`interval_semantics: left_closed_right_open`,
`candle_timestamp_semantics: bar_open_time`):

```
Leg 1 reference :  22:00 <= bar_open_time < 07:00     (36 candles)
Leg 1 execution :  07:00 <= bar_open_time < 16:00     (36 candles)
Leg 2 reference :  per §9-A
Leg 2 execution :  per §9-A
```

> **Defect inherited from `ASIAN_SESSION_V1` — corrected here.** That document's §3 states
> `Execution : 07:00 <= bar_open_time < 09:00` and its §6 validation table claims
> "36 session / **8** execution M15 candles". Both are stale. `config/strategy.yaml` carries
> `execution_start_utc: "07:00"`, `execution_end_utc: "16:00"`, `post_session_candles: 36`, and
> §0.2 of that same document says 36. **16:00 / 36 is correct**; the 09:00 / 8 pair must be
> struck from §3 and §6 there. `USER_MANUAL.md` §2 carries the same stale 09:00 expiry.

The first execution bar belongs to the execution window only. Because MT5 `copy_rates_range` may
include the closing timestamp, the window is **re-applied after retrieval**
(`engine.filter_window`) rather than trusted from the API call. No higher or lower timeframe is
consulted anywhere; the package contains exactly one timeframe reference
(`mt5.TIMEFRAME_M15` in `mt5_gateway.py`) and timeframe is not configurable. An H1 bias would be
an invented rule, not a missing feature.

Window/count consistency is enforced at config load, **per leg**: `reference_candles` must equal
the reference window in minutes ÷ 15, and likewise for the execution window. A mismatched pair
raises rather than silently demanding the wrong number of bars.

---

## 4. Determinism

`engine.analyze()` is a pure function. `now`, account, spec, tick, leg descriptor and both candle
lists are injected; no clock is read and no I/O occurs inside the decision logic. Identical
inputs produce byte-identical output apart from the random `analysis_id` and `timestamp_utc`.

Closed candles only. No look-ahead. Confirmed decisions never repaint.

Adding a leg must not change leg 1's output for the same inputs. Pin this:
`test_leg_one_output_unchanged_by_presence_of_leg_two`.

---

## 5. Output contract

`analysis.json` carries `schema_version`, `strategy_id`, `contract_version`, `config_hash`,
**`leg_id`**, **`reference_session`**, the locked levels, classification inputs
(`efficiency_ratio`, `close_location`), the setup and direction, `signal_time` and the signal
candle, `entry`, `stop_loss`, `initial_risk`, `partial_target`, `partial_target_label`,
`runner_management`, `tp1_4r`, `tp2_5r`, `risk_fraction`, volume and risk figures, every gate,
and `reason_codes`.

**A no-trade result is always recorded, with a precise reason.**

`leg_id` is mandatory and must be a first-class journal dimension, so per-leg expectancy is
measurable from day one. Pooling legs into one figure lets a profitable leg hide a losing one —
the same trap §1.2 guards against for setups.

---

## 6. Validation status

| Scope | Status |
|---|---|
| Leg 1 rules (`ASIAN_SESSION_V1` §0) | ✅ verified by execution, 46 tests, extended to 124 |
| Leg 1 Stage 1 conformance | 7 of 8 criteria met; S1.5 (20 reconciliations) outstanding |
| **Leg 2 rules** | ❌ **not implemented, not tested** |
| **Cascade interaction** (§9-C) | ❌ **undefined** |
| **Trail behaviour** (§9-D) | ❌ **undefined** |
| Stage 2 (profitability) | ❌ no backtest engine — finding A27 |

Leg 1's verified behaviours carry over unchanged: midnight crossing, missing and duplicated
candles, both sweep directions, wick-outside-close-outside, boundary touch without rejection,
valid and invalid trend retracements, structural stop failure, spread and risk rejection,
4R/5R arithmetic, and repeat-run determinism.

---

## 7. The feasible sweep band — why `NO_TRADE` is the common outcome

**Worked example 1 of the supplied specification fails its own structural-stop rule:**

```
high 1.16800   low 1.16400   range 0.00400   R 0.00100
entry 1.16450  SL = entry - R = 1.16350      sweep low 1.16330
rule:  SL < sweep_low - stop_buffer
       1.16350 < 1.16330  →  FALSE   (fails by 2 pips)
```

The engine follows the **rule**, not the example, and returns `NO_TRADE` with
`FIXED_STOP_NOT_BEYOND_SWEEP`. Pinned by
`test_specification_example_one_is_rejected_by_its_own_structural_rule`.

**The band, with the §1 provisional values.** For a long sweep, the candle must open and close
inside the boundary, so `entry = body_low > ref_low`. Combining sweep qualification with
structural protection:

```
sweep      : candle.low < ref_low - 0.02 × range
structural : entry - 0.25 × range < candle.low - 0.02 × range
           → entry < candle.low + 0.23 × range

feasible entry band = ( ref_low , ref_low + 0.21 × range )
```

**The reclaim body must land in a window 21% of the range wide, sitting directly above the
boundary.** Mirrored for shorts. That is narrow by construction — a direct consequence of the
fixed 25% stop — and a high sweep `NO_TRADE` rate is expected, not a fault.

If it approaches 100% in practice, `sweep_buffer` and `stop_buffer` are geometrically
incompatible and need the trader's review. **That is a parameter decision, not a code fix.**

### 7.1 Measured funnel, leg 1, 10–14 Aug 2026 (159 runs, `ASIAN_SESSION_V1`)

```
159 runs
 ├─ 55  rejected before classification   (mostly G5_RANGE_BOUNDS)
 └─ 104 classified
     ├─ 45  UNCERTAIN        → G7 rejects            43% of classified
     ├─ 40  BULLISH/BEARISH_TREND                    38%
     └─ 19  RANGE            → only these reach Sweep/Range setups   18%
 ⇒ 1 accepted signal
```

**The binding constraint is upstream of the sweep band.** Only 19 of 104 classified sessions were
`RANGE` at all, so Setups A and B were eligible on 12% of runs before any buffer was consulted.
`UNCERTAIN` — efficiency above 0.35 with a close between the 0.35 and 0.65 locations — is the
single largest loss.

Before touching `sweep_buffer`, the question to answer is whether the 0.35 / 0.65 pair is
partitioning sessions the way the trader intends. **Neither should be changed after seeing
out-of-sample results** (§1).

---

## 8. Trader resolutions carried forward

| # | Resolution | Enforced behaviour |
|---|---|---|
| Q1 | Legacy example 1 is a narrative error. | strict structural rule followed; example rejected |
| Q2 | Retain USDJPY with symbol-specific limits. | retained and configured |
| Q3 | Provisional grid approved for the Stage 2 baseline only. | fingerprint `0f2e89f3a44fca01`; optimization disabled |
| Q4 | Retain the broker-specific `XAUUSD.crp` symbol. | exact `.crp` mapping enforced |

Q1–Q4 were resolved against leg 1. **None has been re-asked for leg 2.**

---

## 9. Decisions required before this contract may execute

`G18_CONTRACT_SIGNED` fails until all five are closed.

### 9-A · Leg 2 windows

Leg 2's reference must equal leg 1's execution. Three self-consistent arrangements; all candle
counts verified:

| | Leg 1 exec | Leg 2 reference | Leg 2 execution | Overlap |
|---|---|---|---|---|
| **A1 disjoint** | 07:00–12:00 (20) | London 07:00–12:00 (20) | NY 12:00–22:00 (40) | none |
| **A2 prior V2** | 07:00–16:00 (36) | London 07:00–12:00 (20) | NY 12:00–22:00 (40) | **12:00–16:00, 16 candles** |
| **A3 sequential** | 07:00–16:00 (36) | London 07:00–16:00 (36) | NY 16:00–21:00 (20) | none |

A2 matches `SESSION_TRADING_SOURCE_WORKFLOW_V2` (`reference_session: LONDON`, `07:00-12:00`,
`execution 12:00-22:00`, `new_entry_cutoff 18:00`) but creates a four-hour window in which both
legs can fire on the same symbol. A1 shortens the London entry window; A3 keeps it whole at the
cost of a shorter New York window. **No default is applied.**

### 9-B · Per-leg parameters

The §1 values and the 0.35 / 0.65 thresholds were signed against **Asian** ranges. London ranges
are structurally larger — the 2022-10-03 validation chart records Asian 50.1p, London 74.7p, New
York 88.5p. Reusing Asian `minimum_range` / `maximum_range` on a London reference will admit or
reject the wrong days. Either re-sign per leg, or state explicitly that one set governs both.

### 9-C · Cross-leg exclusivity and risk

- May leg 2 trade a symbol leg 1 already traded today?
- If leg 1's position is still open when leg 2 signals — second position, replacement, or skip?
- Is 2.0% daily shared across legs (§0.10's reading) or per leg, making it 4%?

§0.10 states the shared-budget reading. **Confirm or overrule.**

### 9-D · Trail definition

"Trail" must be arithmetic before it can be code: trail on what (confirmed M15 swing points, a
fixed R distance, a fraction of range), evaluated on which candle, and whether it may ever sit
worse than breakeven (it must not). Until signed, `TREND` returns `NO_TRADE` with
`TREND_TRAIL_UNSPECIFIED`.

### 9-E · Leg 2 universe

Leg 1 runs EURUSD, GBPUSD, USDJPY, XAUUSD (`XAUUSD.crp`). Whether leg 2 runs the same four, a
subset, or different per-symbol limits is unstated.

---

## 10. Golden case — EURUSD 2022-10-03 Asian→London, and the three defects it exposes

`benchmarks/truth_source_setups.json` records
`eurusd-2022-10-03-asian-to-london-short-sweep` as **`USER_CONFIRMED_TRUTH`**. It is the
reference case for leg 1 and must pass before this contract executes.

| Field | Confirmed truth | Engine (7 independent runs) | |
|---|---|---|---|
| Session type / bias | RANGE / BEARISH | RANGE / BEARISH | ✅ |
| Reference high / low | 0.98344 / 0.97843 | 0.98344 / 0.97843 | ✅ |
| Range | 50.1 pips | 50.1 pips | ✅ |
| Setup / direction | SWEEP / SHORT | SWEEP / SHORT | ✅ |
| Entry | 0.98342 | **0.98342** | ✅ |
| Stop (25% of range) | 0.9846725 (12.525p) | 12.525p | ✅ |
| 75% partial target | 0.97843 (opposite boundary) | 0.97843 | ✅ |
| 5R target | 0.9771575 | **0.977158** | ✅ |
| **Outcome** | **TP5_HIT, +5.0R** | **END_WINDOW, +1.038R** | ❌ |

**The signal generator is correct.** Entry, stop, both targets and the classification reproduce
the confirmed truth to the last decimal, in every variant. The divergence is entirely in exit
handling.

### 10.1 Defect D1 — `END_WINDOW` is an invented exit

§0.9 defines management as: open with the original stop → 75% off at the target → stop to
breakeven → remainder to 5R. **§0 specifies no time-based exit for an open position anywhere.**
§0.2's "End of entry window → cancel unfilled signals" governs *unfilled signals*, not live
positions.

The engine force-closes the open position at the execution-window boundary and books `END_WINDOW`
at +1.038R. Signal time was 15:15 UTC against a 16:00 boundary: **45 minutes to travel 62.6 pips.
The trade cannot succeed by construction.**

Under the project's own standard — *where §0 is silent, the engine stands aside* — inventing an
exit is a defect, and this one is the entire difference between +1.04R and +5R.

**Required refinement.** Separate the two concepts, per leg:

```
new_entry_cutoff_utc    last bar on which a NEW signal may be generated
position_hold_end_utc   last bar on which an OPEN position is force-closed
```

`ASIAN_SESSION_V1` has only `execution_end_utc` and uses it for both. The trader's own prior
`SESSION_TRADING_SOURCE_WORKFLOW_V2` separated them (`new_entry_cutoff_utc: 18:00`,
`execution_end_utc: 22:00`). **§0 must state `position_hold_end_utc` explicitly, or state that
positions are held until stop or target with no time exit.** Silence is what produced D1.

### 10.2 Defect D2 — `REJECTED_MOMENTUM_ALIGNMENT` is an invented rule

Five of the seven Oct-3 runs reject the first sweep signal with `REJECTED_MOMENTUM_ALIGNMENT`.
`asian_session_backtester.py` carries module constants that appear nowhere in §0:

```
MOMENTUM_BODY_MULTIPLIER      = 1.5
MINIMUM_SWEEP_WICK_RATIO      = 0.35
MINIMUM_BOUNDARY_PIERCE_PIPS  = 1.0
POST_LOSS_COOLDOWN_BARS       = 4
MAX_SESSION_LOSS_R            = -2.0
```

Each is a filter the trader did not specify. They may be good ideas; they are not this contract.
**Required refinement:** remove them from the decision path, or promote them into §0 with values
and a sign-off. Until then any result they touch is measuring a different strategy.

### 10.3 Defect D3 — the reference window contradicts the golden case

```
confirmed truth        reference_window: 00:00-07:00   → 28 M15 candles
ASIAN_SESSION_V1 §0.2  22:00-07:00                     → 36 M15 candles
config                 data_quality.require_exact_candle_count: true
```

`G4_SESSION_DATA` demands exactly the configured count. **Run the confirmed-truth case through
the current contract and it is rejected before classification** — wrong candle count.

On 2022-10-03 the 22:00–00:00 block happened not to extend the range, so both windows yield
0.98344 / 0.97843. That is coincidence, not agreement; on other days the high, low, range, R,
entry and both targets will all differ.

**Required decision (extends §9-B):** either the golden case is re-derived on 22:00–07:00, or
§0.2 adopts 00:00–07:00. They cannot both stand.

### 10.4 RESOLVED against broker data — 2026-08-15

Fixture: `data/eurusd_m15_2022_10_utc.csv` — 1,440 M15 bars, VT Markets MT5 export
2022-10-03 → 2022-10-21 server time, converted to UTC. `sha256[:16] = 658199e50c2846b8`.

**Broker server offset is UTC+3** for this period (Europe left DST on 30 Oct 2022).

**The reference window is `00:00–07:00 UTC`, 28 M15 bars.** Confirmed by exhaustive search: this
is the only session boundary that reproduces the golden levels.

| Field | Confirmed truth | Recomputed from broker data | |
|---|---|---|---|
| Reference high | 0.98344 | 0.98344 | ✅ |
| Reference low | 0.97843 | 0.97843 | ✅ |
| Range | 50.1 pips | 50.1 pips | ✅ |
| Efficiency ratio | — | 0.088 → **RANGE** | ✅ |
| Close location | — | 0.265 → BEARISH lean | ✅ |
| Risk unit R | 12.525 pips | 12.525 pips | ✅ |
| Signal time | 15:15 UTC | **15:15 UTC** (first sweep passing quality) | ✅ |
| Entry (body high) | 0.98342 | 0.98342 | ✅ |
| Stop | 0.9846725 | 0.9846725 | ✅ |
| Partial target | 0.97843 | 0.97843 | ✅ |
| 5R target | 0.9771575 | 0.9771575 | ✅ |
| **Outcome** | **TP5_HIT +5.0R** | **STOP_LOSS −1.0R** | ❌ |

**Every input, level and target reproduces exactly — eleven of eleven.** The signal generator
conforms to §0 without deviation. Only the outcome diverges.

**Why.** On VT Markets ticks the trade reached a maximum favourable excursion of **3.69R**
(low 0.97881) and **missed the partial target by 3.8 pips**. TP1 therefore never fired, the stop
was never moved to breakeven, and price reversed to take the original stop at
**2022-10-04 05:45 UTC**.

The screenshot confirming +5R is an **EIGHTCAP** feed. On a feed whose 3 Oct low ran ~4 pips
deeper, TP1 fires, 75% books at 4R, the stop moves to breakeven, and the runner rides free to 5R.

> **The gap between +5.0R and −1.0R on this trade is under four pips of feed difference.**
> That is the finding, not the engine. Any golden case must name its feed, and results must not
> be transferred between brokers.

### 10.4a Sensitivity to the position-hold policy (D1)

Same signal, same levels, four exit policies:

| Policy | Result |
|---|---|
| No time exit (§0 as written) | STOP_LOSS **−1.000R** |
| Hold to 16:00 UTC (current engine's `END_WINDOW`) | **+2.080R** |
| Hold to 20:00 UTC | +0.424R |
| Hold to 22:00 UTC (prior V2) | +1.112R |

**Correction to the first analysis of D1.** It was recorded here that `END_WINDOW` at +1.038R was
truncating a +5R winner. On broker data that is wrong: the trade never reached TP1, and the time
exit **avoided a full −1R loss rather than costing 4R**.

D1 remains a genuine defect — §0 defines no time exit, so the engine is inventing one, and an
undocumented rule that happens to help is still undocumented. But its cost was mis-stated, and on
this trade its sign was positive. Fix it by **specifying** `position_hold_end_utc`, not by
assuming removal improves results.

### 10.5 Acceptance test

```
test_golden_case_eurusd_2022_10_03_asian_to_london
  fixture : data/eurusd_m15_2022_10_utc.csv  (sha256[:16] 658199e50c2846b8)
  offset  : UTC+3      reference window: 00:00-07:00 UTC, 28 M15 bars
  asserts : session_type RANGE · setup SWEEP · direction SHORT
            signal_time 2022-10-03T15:15:00Z
            entry 0.98342 · stop 0.9846725 · partial 0.97843 · tp2 0.9771575
```

**The test asserts the signal, not the outcome.** Outcome depends on the feed and on the
unresolved D1 policy; asserting `TP5_HIT` would pin the engine to another broker's ticks.
Record the realised R per feed separately.

This test passes today. `G18_CONTRACT_SIGNED` is not blocked by it.

### 10.5a LEG 2 validation — London → New York, 2022-10-03

Runner: `scripts/validate_golden_oct3.py`. Benchmark:
`eurusd-2022-10-03-london-to-new-york-short-sweep`, status `USER_CONFIRMED_TRUTH`,
**`outcome: STOP_LOSS`** — *"User confirmed the New York entry stopped for -1R in the source
strategy."*

| Field | Confirmed truth | §0 engine | |
|---|---|---|---|
| Reference high / low | 0.98273 / 0.97526 | 0.98273 / 0.97526 | ✅ |
| Range | 74.7 pips | 74.7 pips | ✅ |
| R (25%) | 18.675 pips | 18.675 pips | ✅ |
| Session state | RANGE | **BEARISH_TREND** (ER 0.396) | ❌ |
| Setup | SWEEP @ 14:15Z, entry 0.98181 | **rejected** | ❌ |

**Two independent reasons the current contract refuses this trade.**

**(a) The classifier.** London ER = 0.396. `ASIAN_SESSION_V1` uses `efficiency_ratio <= 0.35` →
`BEARISH_TREND`. The benchmark was generated under the prior V2 rule — *"closed M15 path
efficiency <= 55% is RANGE"* — under which 0.396 is `RANGE`. This is §9-B made concrete: the
0.35 threshold was signed against **Asian** ranges and does not reproduce a **London**-referenced
benchmark.

**(b) The sweep buffer, and it is right to refuse.** Even forcing `RANGE`, the 14:15Z candle
breaches the London high by **0.4 pips**:

```
14:15Z  O 0.97938  H 0.98277  L 0.97873  C 0.98181
London high 0.98273 · breach 0.4p · required buffer 2% × 74.7p = 1.49p  ->  REJECTED
```

`entry 0.98181` is that candle's body high, so the benchmark and the engine agree on the
arithmetic — they disagree on whether a 0.4-pip clip is a sweep. §0.6's buffer says it is not.
Prior artifacts (`eurusd_2022-10-03_london_to_newyork`, `..._truth_baseline`) used a smaller
buffer, produced entry 0.98181, and recorded **STOP_LOSS −1.037R** — matching the confirmed truth
on both entry and outcome.

> **The 2% sweep buffer filtered out a losing trade.** On 2022-10-03 the source strategy took
> leg 1 (+5R) and leg 2 (−1R) for +4R net. §0 as written takes leg 1 and refuses leg 2.

Leg 2 must **not** be treated as a conformance failure. It is a benchmark generated under
superseded parameters, and the current rule outperformed it on this date. Re-derive the leg-2
benchmark under signed §9-B parameters before using it as a gate.

### 10.6 D3 — closed

`ASIAN_SESSION_V1` §0.2 specifies `22:00–07:00 UTC` and **36** session candles.
The confirmed-truth case is `00:00–07:00 UTC` and **28** candles, and only that window reproduces
0.98344 / 0.97843. With `require_exact_candle_count: true`, the current contract would reject its
own golden case at `G4_SESSION_DATA`.

**Resolution: §0.2 adopts `00:00–07:00 UTC`, 28 session candles.** `sweep_window_hours` and the
execution window are unaffected. This must be applied to `STRATEGY_SPEC.md` §0.2 and to
`config/strategy.yaml` (`session_start_utc: "00:00"`, `session_candles: 28`) before the next run,
and it invalidates every artifact generated under the 22:00 window.

---

Analysis only. Levels and calculated volume are proposals, not automated signals. Verify every
value against your own chart and broker order window before placing or managing an order
manually. Passing every gate means the configured rules passed — nothing more.
