# SESSION_FLOW_V2_SIMPLE — Stateless Completed-Box Router

Strategy flow: **`SESSION_FLOW_V2_SIMPLE`**  
Version: **2.1-simple**  
Decision date: **2026-08-21**  
Status: **ROUTING CONTRACT FROZEN / EXECUTION BLOCKED**

## 1. Version boundary

This is a strategy-definition change. It replaces the post-reference Cowork Sweep branch for setup-family selection. `COWORK_SWEEP_V2` and its execution contract are retired and retained only as audit history; their post-session populations and performance cannot be transferred.

## 2. Input gate

The router accepts exactly one `VALID_FROZEN_SESSION` produced from completed M15 reference candles. Asian is `[00:00,08:00)` with 32 bars; London is `[07:00,12:00)` with 20 bars. Missing, duplicate, extra, invalid, still-forming, or post-session candles fail closed as `INVALID_SESSION_DATA`.

## 3. Stateless routing

```text
VALID_FROZEN_SESSION
        ↓
ER_ONLY_V2
        ├─ ER >= 0.40 → TREND → ENTRY_1
        └─ ER <  0.40 → RANGE
                            ↓
               completed reference-session Sweep
                    ├─ qualified → SWEEP → ENTRY_2
                    └─ none      → RANGE → ENTRY_3
```

The router returns exactly one `setup_type` and one `entry_engine`. It never enters an observation state and takes no execution-window input.

## 4. Reference-session Sweep

Only ER-classified Range sessions are inspected. Each reference candle is evaluated chronologically against highs/lows formed strictly from earlier reference candles:

- strict high penetration plus Close below the prior high → high-side Sweep / Short;
- strict low penetration plus Close above the prior low → low-side Sweep / Long;
- touch-only or close remaining outside → not a Sweep;
- first qualified candle owns the result;
- same-candle dual-side Sweep selects the Sweep family but leaves direction unresolved, blocking Entry 2 downstream.

No post-session candle can change Trend/Range, Sweep/Range, setup type, or entry-engine ownership.

## 5. Output contract

```yaml
strategy_flow: SESSION_FLOW_V2_SIMPLE
box_status: VALID_FROZEN_SESSION
regime:
  classifier: ER_ONLY_V2
  type: TREND_OR_RANGE
sweep_check:
  scope: REFERENCE_SESSION_ONLY
  evaluated: RANGE_ONLY
  qualified: true_or_false_or_not_evaluated
routing:
  setup_type: TREND_OR_SWEEP_OR_RANGE
  entry_engine: ENTRY_1_OR_ENTRY_2_OR_ENTRY_3
status: ROUTE_RESOLVED
```

## 6. Removed states

The setup router has no `OBSERVING_EXECUTION_WINDOW`, `NO_SWEEP_YET`, pending-Range cancellation, post-session same-candle routing conflict, later-Sweep ownership, multiple post-session candidates, or setup-selection expiry.

## 7. Execution boundary

This contract selects a setup family only. Entry triggers, prices, order types, fills, costs, position state, and scheduling remain separately blocked until their versioned contracts pass validation.
