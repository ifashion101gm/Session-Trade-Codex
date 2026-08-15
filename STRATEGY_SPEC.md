# ASIAN_SESSION_V1 — Strategy Specification

Strategy ID: **`ASIAN_SESSION_V1`** · Contract version: **1.0** · Spec date: **2026-08-11**
Active config hash: **`2530b751134fbf6e`**

**§0 is the source of truth.** It is the trader's specification. The engine implements it; it does
not extend, optimise, or improve it. Any divergence between code and §0 is a defect, even when the
divergence looks better. Where §0 is silent, the engine stands aside and returns `NO_TRADE`.

> Supersedes SSPF v2.2 (`fddb7465a73fd724`, `92279f3d42d32fc3`). Evidence gathered under the old
> contract does not transfer — different session window, classification metric, entry model,
> partial target, and risk fraction. See §11.

---

## 0. Source of truth

### 0.1 Decision flow

```
Build Asian range  →  Validate range and costs ──invalid──→ NO TRADE
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
              75% off at 4R → stop to breakeven
                            ▼
                   Exit remainder at 5R
```

### 0.2 Time model

All internal calculation is UTC. Myanmar time (UTC+6:30) is display only.

| Phase | UTC | Myanmar | Action |
|---|---|---|---|
| Asian range construction | 22:00–07:00 | 04:30–13:30 | Observe and build |
| Range locked | 07:00 | 13:30 | Freeze high and low |
| London execution window | 07:00–16:00 | 13:30–22:30 | Detect eligible setup |
| End of entry window | 16:00 | 22:30 | Cancel unfilled signals |

Half-open intervals: `22:00 <= t < 07:00` and `07:00 <= t < 16:00`.
The Asian session crosses midnight; **the trading date is the date the session ends.**
At M15 that is **36** session candles and **36** execution candles.

### 0.3 Levels — immutable at 07:00

```
asian_high  = max(high)          midpoint       = asian_low + 0.50 × range
asian_low   = min(low)           risk_unit R    = 0.25 × range
asian_range = high - low         lower_quartile = asian_low + 0.25 × range
                                 upper_quartile = asian_high - 0.25 × range
```

Candles after the lock must never modify these.

### 0.4 Day rejection

Reject the trading day when: `range <= 0`; candles are missing or duplicated; range is below the
configured minimum or above the configured maximum; spread exceeds the configured limit; required
warm-up history is unavailable; or the execution candle is outside the entry window.

**Minimum and maximum range are configured per symbol. Gold must not reuse FX limits.**

### 0.5 Session classification

```
net_move         = |asian_close - asian_open|
efficiency_ratio = net_move / asian_range
close_location   = (asian_close - asian_low) / asian_range

RANGE          : efficiency_ratio <= 0.35
BULLISH_TREND  : efficiency_ratio > 0.35  and close_location >= 0.65  and close > open
BEARISH_TREND  : efficiency_ratio > 0.35  and close_location <= 0.35  and close < open
UNCERTAIN      : everything else  →  no trade
```

**0.35 and 0.65 are research parameters, not proven optimal values.** Lock them before each
backtest and never change them after seeing out-of-sample results.

### 0.6 Setup A — Liquidity Sweep

Applies when `session_type == RANGE` and a confirmed sweep occurs in the execution window.

```
Bullish:  candle.low  < asian_low  - sweep_buffer   and  candle.close > asian_low
Bearish:  candle.high > asian_high + sweep_buffer   and  candle.close < asian_high

Rejection-quality filter:
  long  : close >= low  + 0.50 × candle_range
  short : close <= high - 0.50 × candle_range

entry = sweep candle body low (long) or body high (short)
SL    = entry ∓ 0.25 × asian_range
TP1   = opposite Asian boundary; close 75% and move SL to breakeven
TP2   = entry ± 5 × initial_risk
```

The sweep candle must open inside the relevant boundary. Opening outside and merely re-entering
the Asian box is not a new liquidity sweep.

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
Long  : candle.low  <= asian_low  + touch_tolerance  and close > asian_low  and close > open
Short : candle.high >= asian_high - touch_tolerance  and close < asian_high and close < open

entry = Asian low (long) or Asian high (short)
SL    = entry ∓ 0.25 × asian_range
TP1   = opposite Asian boundary; close 75% and move SL to breakeven
TP2   = entry ± 5R
```

The rejection candle must open inside the relevant boundary. A candle that opens outside the
box and merely returns inside is not a new Range rejection signal.

A breakout candle that closes convincingly outside the range is not a rejection and invalidates
this setup.

### 0.8 Setup C — Trend Continuation

"Entry at the middle of the range" means a **confirmed retracement into a midpoint zone**, not an
unconfirmed limit order.

```
midpoint_zone = [asian_low + 0.45 × range , asian_low + 0.55 × range]

Bullish : BULLISH_TREND, price retraces into the zone, confirmation candle closes bullish,
          and its low does not trade below lower_quartile
Bearish : BEARISH_TREND, mirrored, and its high does not trade above upper_quartile

entry = Asian midpoint (50% equilibrium)
SL    = entry ∓ 0.25 × asian_range
TP1   = entry ± 4R        TP2 = entry ± 5R
```

An opposite-quartile violation cancels the pending trend setup for the session. The midpoint
entry is emitted only after a closed confirmation candle; it is never armed blindly at 07:00.

Cancel the setup immediately if price violates the opposite quartile before entry.

### 0.9 Management

1. Open the position with its original stop.
2. Sweep/Range: at the opposite boundary close **75%**, and move the remaining stop to entry.
3. Trend: at **+4R** close **75%**, move the remaining stop to entry, and target **5R**.
4. Never move the initial stop farther away.
5. Do not re-enter the same setup after a completed or stopped trade.

Trailing-stop logic is explicitly **out of scope for v1** and may only be added as a separately
tested strategy version.

### 0.10 Risk

```
risk_basis       = min(account balance, account equity)
risk_per_trade   = 0.5% of risk basis          maximum_daily_risk = 2.0%
maximum_drawdown = 15%                         one open position per symbol
one accepted trade per symbol per Asian session
```

Volume = `risk_amount / (stop_distance × value_per_point_per_lot)`, normalised with broker minimum,
maximum, and step, contract size, tick size, tick value, and account-currency conversion. Reject
the order if the normalised volume would exceed the risk limit.

### 0.11 Setup priority and exclusivity

```
1. Valid Sweep            2. Valid Range Rejection
3. Valid Trend Continuation                  4. No Trade
```

Range and Trend setups are mutually exclusive because they require different classifications.
Not permitted: a sweep and a range setup from the same candle; long and short at the same
timestamp; more than one accepted trade per symbol per session; entry on an incomplete candle;
retroactive reclassification.

### 0.12 State machine

```
WAITING_FOR_ASIAN_OPEN → BUILDING_ASIAN_RANGE → ASIAN_RANGE_LOCKED → SESSION_CLASSIFIED
  → WATCHING_EXECUTION_WINDOW ├ SWEEP_DETECTED ├ RANGE_REJECTION_DETECTED
                              ├ TREND_RETRACE_DETECTED └ WINDOW_EXPIRED
  → SIGNAL_VALIDATION ├ SIGNAL_ACCEPTED └ SIGNAL_REJECTED
  → POSITION_OPEN ├ STOPPED ├ TP1_REACHED → BREAKEVEN_ACTIVE ├ BREAKEVEN_EXIT └ TP2_REACHED
                  └ EMERGENCY_EXIT → SESSION_COMPLETE
```

Every transition records its timestamp, candle, reason code, and inputs.

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
| per-symbol `minimum_range` / `maximum_range` | see `config/strategy.yaml` | day rejection |
| per-symbol `maximum_spread` | see `config/strategy.yaml` | cost rejection |

`efficiency_ratio_threshold` (0.35) and `close_location_trend` (0.65) are the trader's own research
parameters, carried verbatim.

### 1.1 Predeclared research grid

To be run during development only, before the sealed out-of-sample period is opened. Selection
must not be by highest historical profit factor alone; use walk-forward.

| Parameter | Baseline | Candidates |
|---|---|---|
| `sweep_buffer_fraction` | 0.02 | 0.00, 0.01, 0.02, 0.03 |
| `stop_buffer_fraction` | 0.02 | 0.00, 0.01, 0.02 |
| `touch_tolerance_fraction` | 0.05 | 0.02, 0.05, 0.08 |
| `rejection_quality_fraction` | 0.50 | 0.50, 0.60, 0.70 |

### 1.2 Governance state

```
specification_status: DRAFT          implementation_authorized: true
demo_execution_authorized: false     live_execution_authorized: false
optimization_allowed: false          research_status: PROVISIONAL_LOCKED_FOR_BASELINE
```

Promotion requires, in order: deterministic unit tests → golden cases → no-look-ahead audit →
baseline backtest → transaction-cost stress → walk-forward → sealed out-of-sample. Backtest
`SWEEP`, `RANGE_REJECTION` and `TREND_CONTINUATION` **separately** so one setup cannot conceal
another's losses.

---

## 2. Gate pipeline

Gates are evaluated in order. Several exit early; a `NO_TRADE` therefore legitimately carries
fewer gates than an accepted signal. Every rejection maps to a stable reason code.

| # | Gate | Passes when | Early exit |
|---|---|---|---|
| 1 | `G1_ENVIRONMENT` | demo account, expected server and login suffix | no |
| 2 | `G2_UNIVERSE` | symbol is configured (exact string) | yes |
| 3 | `G3_BROKER_CLOCK` | offset within ±14h and tick age in `[-5, 300]s` | no |
| 4 | `G4_SESSION_DATA` | 36 contiguous closed M15 candles, valid OHLC, execution window valid, spread > 0 | yes |
| 5 | `G5_RANGE_BOUNDS` | `min <= range <= max` for this symbol | yes |
| 6 | `G6_SPREAD` | spread ≤ this symbol's maximum | no |
| 7 | `G7_SESSION_CLASSIFIED` | classification is not `UNCERTAIN` | yes |
| 8 | `G8_SESSION_QUOTA` | fewer accepted signals than the per-session limit | yes |
| 9 | `G9_NEWS_FILTER` | no relevant high-impact event within the blocked window | yes |
| 10 | `G10_SETUP_DETECTED` | a setup qualified in a closed execution candle | yes |
| 11 | `G11_STRUCTURAL_STOP` | on `SWEEP`, the fixed stop clears the extreme plus buffer | yes |
| 12 | `G12_STOPS_LEVEL` | stop distance ≥ broker minimum | no |
| 13 | `G13_VOLUME_BOUNDS` | normalised volume within broker limits | no |
| 14 | `G14_DAILY_RISK` | journal healthy and used + proposed ≤ daily limit | no |
| 15 | `G15_DRAWDOWN` | journal healthy and drawdown < 15% | no |
| 16 | `G16_EXECUTION_WINDOW` | current time is inside the configured execution window | no |

`status = SIGNAL_ACCEPTED` only when every recorded gate passed **and** a tradeable plan exists.
Otherwise `NO_TRADE`.

---

## 3. Timeframe and candle semantics

**M15 only**, declared explicitly rather than inferred: `timeframe: M15`,
`timeframe_seconds: 900`, `use_closed_candles_only: true`.

Intervals are **half-open by bar-open time** (`interval_semantics: left_closed_right_open`,
`candle_timestamp_semantics: bar_open_time`):

```
Asian     :  22:00 <= bar_open_time < 07:00
Execution :  07:00 <= bar_open_time < 09:00
```

The 07:00 bar belongs to the execution window only. Because MT5 `copy_rates_range` may include
the closing timestamp, the window is **re-applied after retrieval** (`engine.filter_window`)
rather than trusted from the API call. No higher or lower timeframe is consulted anywhere. The package contains exactly one
timeframe reference (`mt5.TIMEFRAME_M15` in `mt5_gateway.py`) and timeframe is not configurable.
An H1 bias would be an invented rule, not a missing feature.

Window/count consistency is enforced at config load: `session_candles` must equal the session
window in minutes ÷ 15, and likewise for the execution window. A mismatched pair raises rather
than silently demanding the wrong number of bars.

---

## 4. Determinism

`engine.analyze()` is a pure function. `now`, account, spec, tick, and both candle lists are
injected; no clock is read and no I/O occurs inside the decision logic. Identical inputs produce
byte-identical output apart from the random `analysis_id` and `timestamp_utc` — asserted by
`test_identical_inputs_produce_identical_output`.

Closed candles only. No look-ahead. Confirmed decisions never repaint.

---

## 5. Output contract

`analysis.json` carries `schema_version`, `strategy_id`, `contract_version`, `config_hash`, the
locked Asian levels, classification inputs (`efficiency_ratio`, `close_location`), the setup and
direction, `signal_time` and the signal candle, `entry`, `stop_loss`, `initial_risk`,
`partial_target`, `partial_target_label`, `runner_management`, compatibility alias `tp1_4r`,
`tp2_5r`, `risk_fraction`, volume and risk figures, every gate, and `reason_codes`.

**A no-trade result is always recorded, with a precise reason.**

---

## 6. Validation of §0 against the implementation

Verified by executing the engine, not by reading the code.

| §0 rule | Implementation | Verdict |
|---|---|---|
| Asian 22:00–07:00, ends on trading date | `session_bounds` → 2026-08-10T22:00Z → 2026-08-11T07:00Z, 9h | ✅ |
| 36 session / 8 execution M15 candles | enforced and cross-checked at config load | ✅ |
| Levels and quartiles | `lock_asian_levels`, pinned by test | ✅ |
| Levels immutable after lock | post-lock candle with a 1.10–1.20 range leaves levels unchanged | ✅ |
| ER = net move ÷ range | `lock_asian_levels` | ✅ |
| RANGE / BULLISH / BEARISH / UNCERTAIN | `classify_session` | ✅ |
| Sweep detection + quality filter | `detect_sweep` | ✅ |
| Fixed 25% stop | `initial_risk` = 0.00100 on the 40-pip fixture | ✅ |
| Structural stop rejection | spec example 1 correctly returns `NO_TRADE` — see §7 | ✅ |
| Range rejection requires a rejection candle | boundary touch with a bearish close is not a signal | ✅ |
| Trend needs confirmed midpoint retracement | candle away from the zone yields no setup | ✅ |
| Trend cancelled by opposite-boundary close | warning recorded, setup suppressed | ✅ |
| 4R partial / 5R final, 75% | `tp1_4r`, `tp2_5r`, management block on the ticket | ✅ |
| Setup priority sweep > rejection > trend | sweep wins on a candle that satisfies both | ✅ |
| One trade per symbol per session | `G8_SESSION_QUOTA` | ✅ |
| 0.5% risk, 2% daily, 15% drawdown | measured from the lower of balance and equity | ✅ |
| Volume floored to broker step | 0.05 lots from 5.00/100.0 | ✅ |
| Reason codes on every outcome | `reason_codes`, required by Stage 1 | ✅ |

46 tests pass, covering midnight crossing, missing and duplicated candles, both sweep directions,
wick-outside-close-outside, boundary touch without rejection, valid and invalid trend
retracements, structural stop failure, spread and risk rejection, 4R/5R arithmetic, and repeat-run
determinism.

---

## 7. Defect found in the supplied specification

**Worked example 1 fails its own structural-stop rule.**

```
asian_high 1.16800   asian_low 1.16400   range 0.00400   R 0.00100
entry 1.16450        SL = entry - R = 1.16350        sweep low 1.16330

rule:  SL < sweep_low - stop_buffer
       1.16350 < 1.16330  →  FALSE   (fails by 0.00020, i.e. 2 pips)
```

The specification states this example "passes". It does not — and example 2, which rejects on the
same rule, is correct. The engine follows the **rule**, not the example, so example 1 returns
`NO_TRADE` with `FIXED_STOP_NOT_BEYOND_SWEEP`. This is pinned by
`test_specification_example_one_is_rejected_by_its_own_structural_rule`.

**Consequence — the feasible sweep band.** Combining sweep qualification with structural
protection:

```
entry - 0.25 × range + stop_buffer  <  sweep_low  <  asian_low - sweep_buffer

feasible only while:  entry < asian_low + 0.25 × range - buffers
```

The reclaim candle must close back to within roughly a quarter of the range above the Asian low
(mirrored for shorts). Expect a high `NO_TRADE` rate on sweeps. If it approaches 100% in practice,
`sweep_buffer` and `stop_buffer` are geometrically incompatible and need the trader's review —
that is a parameter decision, not a code fix.

---

## 8. Trader resolutions

| # | Resolution | Enforced behaviour |
|---|---|---|
| Q1 | Treat legacy example 1 as a narrative error. | strict structural rule followed; example rejected |
| Q2 | Retain USDJPY with symbol-specific limits. | retained and configured |
| Q3 | Approve the provisional grid for the Stage 2 baseline only. | fingerprinted sign-off recorded; optimization remains disabled |
| Q4 | Retain the broker-specific `XAUUSD.crp` symbol. | exact `.crp` mapping enforced |

---

Analysis only. Levels and calculated volume are proposals, not automated signals. Verify every
value against your own chart and broker order window before placing or managing an order manually.
