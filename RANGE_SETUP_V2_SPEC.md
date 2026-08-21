# RANGE_SETUP_V2 — Execution Contract Closure Draft

Contract: **`SESSION_FLOW_V2`**  
Component: **`RANGE_SETUP_V2`**  
Status: **SIGNED / IMPLEMENTATION_READY**  
Draft date: **2026-08-20**

This document defines the contract boundary before implementation. It does not
change an engine, regenerate a ticket, or authorize a schedule.

This is the subordinate **Entry 3** component of `SESSION_FLOW_V2`. It is reachable
only after the master router records `session_type=RANGE`, finds no qualified Sweep
inside the completed reference box, and selects `setup_type=RANGE`. It does not define or override
the master Trend test or Sweep classification.

## 1. Objective and hypothesis

After a completed reference session is frozen and classified `RANGE`, a failed entry-window
attempt to leave a reference boundary may revert toward the opposite side of the box. The
hypothesis is research-only. A Range ticket is permitted only when a deterministic,
causal trigger is present and no higher-priority Sweep Setup owns the same event.

## 2. Terms that must remain separate

- `session_type`: final `TREND` or `RANGE` from ER_ONLY_V2.
- `setup_type`: final `TREND`, `SWEEP`, or `RANGE` after the Range-session Sweep split.
- `entry_status`: selected engine's entry outcome, separate from strategy type.

`session_type=RANGE` and `setup_type=RANGE` are eligibility context. They are not an entry signal. A legacy
`session_regime` field may remain for compatibility but is diagnostic, not routing
authority.

## 3. Signed inputs

- Signal data: completed M15 OHLC bars normalized to UTC.
- Leg A reference: Asian `[00:00,08:00)`, exactly 32 bars; activation 08:00 UTC.
- Leg B reference: London `[07:00,12:00)`, exactly 20 bars; activation 12:00 UTC.
- Reference high, low, range, and midpoint become immutable at activation.
- Fixed risk distance: `1R = 0.25 × reference_range`.
- Management: close 75% at fixed 4R; retain the original stop; close the remaining
  25% at fixed 5R. Automatic breakeven is not part of V2.
- Decisions at time `T` may use only bars completed by `T`.

## 4. Eligibility and precedence

The following precedence is frozen for V2:

```text
reference valid and er_trend_test = NOT_TREND
    -> inspect only the completed reference box for Sweep
    -> if Sweep qualifies: strategy_type = SWEEP; do not evaluate Entry 3
    -> if no Sweep qualifies: strategy_type = RANGE; evaluate Range trigger
    -> if Range qualifies: entry_status = RANGE_SIGNAL
    -> otherwise: NO_TRADE at Entry 3 window end
```

Sweep classification is final at box completion. Post-reference candles cannot
reclassify or cancel a Range strategy; they are evaluated only by Entry 3.

## 5. Direction model — signed

- rejection of the frozen reference high -> `SHORT`;
- rejection of the frozen reference low -> `LONG`;
- a candle interacting with both boundaries -> ambiguous, no Range signal.

Direction must come from the boundary event, not from later price action.

## 6. Trigger model — signed

The trigger family is `BOUNDARY_REJECTION_CLOSE` and uses a completed M15 candle.
Sweep qualification is evaluated first and owns the event when it passes.

### Short

```text
bar_high >= reference_high
AND bar_close < reference_high
AND bar_close < bar_open
```

### Long

```text
bar_low <= reference_low
AND bar_close > reference_low
AND bar_close > bar_open
```

`BOUNDARY_TOLERANCE = 0`. The candle must actually touch the boundary. The rule uses
no arbitrary pip, range-fraction, ATR, spread, volatility, wick-ratio, volume, or
retrospective confirmation filter.

Repository reconciliation found a legacy `touch_tolerance_fraction = 0.05` in the
superseded `ASIAN_SESSION_V1` contract. `STATUS.md` records touch tolerance among the
filters removed from the active session-flow architecture. It is not authority for V2.

## 7. Entry and fill model — signed

```text
signal_time = trigger bar close
signal_price = trigger bar close
M15          = signal authority
M1           = executable fill authority when authoritative M1 exists
```

The trigger close is a research signal price, not an assumed same-close fill. Without
authoritative execution data, the result is analytical and may not claim an executable
fill, order type, or volume.

## 8. Invalidation — signed

Setup invalidation and executable risk are not separate price gates in V2. Once filled,
the fixed stop is the sole Range-trade invalidation:

```text
1R = 0.25 × reference_range
SHORT stop = entry + 1R
LONG stop  = entry - 1R
```

A stop touch produces `RANGE_STOPPED` and `-1R`. The stop is never widened, moved to a
reference boundary, or changed after entry. The Sweep structural-extreme gate does not
apply because a Range setup has no sweep extreme.

Before fill, a candidate may end only through Entry 3 observation-window expiry. No
additional boundary-close invalidation is introduced in V2.

## 9. Observation windows — signed

| Leg | Start | End |
| --- | --- | --- |
| Post-Asian | 08:00 UTC | 12:00 UTC |
| Post-London | 12:00 UTC | 18:00 UTC |

Only completed M15 bars whose opens lie in `[start,end)` may create signals. At `end`,
an unresolved leg terminates as `NO_VALID_SETUP_BY_WINDOW_END` or `NO_FILL` according
to whether a valid order was created.

## 10. Conflict and lifecycle state machine — signed

```text
WAITING
  -> qualifying Range event -> RANGE_PENDING

RANGE_PENDING
  -> Range order fills -> RANGE_ACTIVE
  -> observation end before fill -> NO_FILL

RANGE_ACTIVE
  -> later Sweep-like movement -> DIAGNOSTIC_ONLY; never reclassify
```

There is a maximum of **one filled trade per reference leg**. A later event cannot
rewrite a filled trade, and no second setup may fill in that leg.

`AUTOMATIC_BREAKEVEN = NOT_PART_OF_V2`. The original stop remains unchanged after a
partial. No dormant breakeven parameter belongs in the executable V2 contract; any
future breakeven study requires a separately versioned experiment.

## 11. Costs, sizing, and authorization

Range risk is `1R = 25% × reference_range`; the Sweep structural-extreme gate is not
applied. Management is fixed:

```text
TP1 = entry ± 4R; close 75%
SL after TP1 = original SL
TP2 = entry ± 5R; close remaining 25%
```

The opposite reference boundary is diagnostic only and must be reported at its actual
R multiple. It must not be labelled `4R` unless it equals 4R mathematically.

Position size remains unavailable unless authoritative account risk and instrument
contract metadata are present. Spread, slippage, commission, pip/point value, account
currency conversion, and fill rules must be explicit in every research run. Missing
required executable fields produces `ANALYSIS_ONLY`, never a fabricated order.

## 12. Validation policy

- Oct 3–21 remains hypothesis-development data.
- Freeze this signed contract before regenerating that sample.
- Compare V1 and V2 classifications and tickets before comparing returns.
- Use unseen data only after implementation, causality, baseline, and accounting tests
  pass.

Minimum acceptance tests include high/low rejection symmetry, Sweep precedence,
dual-boundary ambiguity, no same-close assumed fill, future-bar perturbation immunity,
window expiry, invalidation, missing-size metadata, and deterministic reruns.

## 13. State machine and terminal names

```text
WAITING_FOR_REFERENCE
  -> REFERENCE_LOCKED
  -> OBSERVING
  -> RANGE_CANDIDATE
  -> RANGE_SIGNAL
  -> ORDER_PENDING

ORDER_PENDING
  -> qualified Sweep before fill -> RANGE_CANCELLED_BY_SWEEP -> route Sweep
  -> fill -> RANGE_ACTIVE
  -> window end -> NO_FILL_BY_WINDOW_END

OBSERVING
  -> window end without signal -> NO_SETUP_BY_WINDOW_END

RANGE_ACTIVE
  -> fixed SL -> RANGE_STOPPED
  -> fixed 4R -> RANGE_PARTIAL_4R; original SL remains
  -> fixed 5R -> RANGE_TARGET_5R
```

The same state machine applies to both legs. Only the frozen reference box and signed
observation window differ.

## 14. Contract closure audit

```text
RANGE_SETUP_V2 CONTRACT STATUS

Direction              : SIGNED
Trigger family         : SIGNED
Boundary tolerance     : SIGNED — ZERO
Entry                  : SIGNED — trigger M15 close is signal price
M1 fill authority      : SIGNED
Risk                    : SIGNED — 25% of reference range
Invalidation            : SIGNED — fixed 1R stop
Partial                 : SIGNED — 75% at fixed 4R
Final target            : SIGNED — 25% at fixed 5R
Breakeven               : NOT_PART_OF_V2
Sweep precedence        : SIGNED
Sweep cancellation      : SIGNED
Trade limit             : SIGNED — one filled trade per leg
Observation windows     : SIGNED

OVERALL                 : IMPLEMENTATION_READY
```

This status authorizes a separately requested implementation phase. It does not itself
authorize engine changes, backtests, or schedules.
