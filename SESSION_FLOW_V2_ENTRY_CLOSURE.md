# SESSION_FLOW_V2 — Entry Closure Addendum

Contract: **`SESSION_FLOW_V2`**  
Addendum status: **PARTIALLY SIGNED / IMPLEMENTATION BLOCKED**  
Decision date: **2026-08-20**

This addendum is the sole closure register for Entry 1, Entry 2, and the common
E1/E2/E3 price-risk and management policy. It does not change an engine, authorize a
backtest, define broker fills, or authorize execution. An unresolved field is a hard
contract blocker and must not be replaced by an implementation assumption.

The Entry 2 rows below are superseded by `COWORK_SWEEP_V2_SPEC.md` where they conflict.
Completed-box Sweep ownership, Sweep-Close reference price, one-fill management, and
no-breakeven assumptions no longer govern the Cowork Sweep branch.

## 1. Authority inherited from the master contract

The signed `ER_ONLY_V2` classifier remains authoritative:

```text
ER >= 0.40 -> TREND
ER <  0.40 -> session_type=RANGE; inspect the same completed reference box for Sweep
```

ER uses the path formula in `SESSION_FLOW_V2_SPEC.md`. Midpoint fields are diagnostics
only and cannot change classification. A midpoint-plus-ER classifier is a separately
versioned challenger, not this contract.

Routing is frozen:

```text
session_type=TREND -> setup_type=TREND -> Entry 1 only
session_type=RANGE + qualified Sweep -> setup_type=SWEEP -> Entry 2 only
session_type=RANGE + no qualified Sweep -> setup_type=RANGE -> Entry 3 only
```

## 2. Entry 1 — Trend closure register

```text
ENTRY_1_TREND

Eligibility:       strategy_type = TREND                  SIGNED
Direction:         BOX_DIRECTION_V1                      SIGNED / IMPLEMENTED
Bias source:       completed-box first Open / final Close SIGNED
Bias resolved_at:  reference-box completion              SIGNED
Trigger:           UNRESOLVED
Signal price:      UNRESOLVED
Order type:        UNRESOLVED
M1 fill rule:      UNRESOLVED
Pre-fill invalidation: UNRESOLVED
Observation expiry:   UNRESOLVED
```

Trend direction is ready, but until every remaining unresolved field is signed,
Entry 1 terminates as
`ENTRY_1_CONTRACT_INCOMPLETE`; it may not emit an executable or analytical trade
ticket. No existing V1 bias or Trend implementation is imported by implication.

## 3. Entry 2 — Sweep closure register

```text
ENTRY_2_SWEEP

Eligibility:       NOT_TREND + qualified Sweep            SIGNED AS ROUTING RULE
Direction:         high sweep -> SHORT; low sweep -> LONG SIGNED
Input window:      completed reference box only           SIGNED
Qualification:     SWEEP_SETUP_V2_CLASSIFIER 1.0           SIGNED / IMPLEMENTED
Multiple-candidate rule: first qualified chronologically   SIGNED
Dual-boundary rule: first chronological; same-candle blocks direction SIGNED
Signal/reference:  Asian Sweep candle Close at 08:00 activation SIGNED
Entry price level: Asian Sweep candle Close              SIGNED
Order type:        UNRESOLVED
M1 fill rule:      UNRESOLVED
Structural gate:   required in principle; exact evidence/failure rule UNRESOLVED
Pre-fill invalidation: UNRESOLVED
Classification expiry: NOT APPLICABLE — box completion is the endpoint
```

The causal zero-clearance, first-qualified classifier is signed in
`SWEEP_SETUP_V2_SPEC.md`. The 08:00–16:00 observation
model is superseded for classification. The 2.5%-reclaim
Sweep Close implementation remains an experiment and has no V2 authority. Every valid
NOT_TREND box now resolves immediately to Sweep or Range. A box classified Sweep still terminates Entry 2 as
`ENTRY_2_CONTRACT_INCOMPLETE` until its execution fields close.

`ENTRY_2_V2_SPEC.md` now owns this closure work. For POST_ASIAN, Sweep candle Close is
the signed Entry 2 reference level known at 08:00 UTC, and causal return-to-level E2-B
is the signed architecture. Exact order selection and M1 fill semantics remain open;
E2-A is a research challenger and E2-C remains a theoretical benchmark only.

## 4. Common E1/E2/E3 policy — signed

The following price-risk and management framework applies identically to all three
entries unless a future signed addendum explicitly versions an exception:

```text
1R price distance       = 0.25 × frozen reference range
TP1                     = fixed 4R
TP1 close fraction      = 75%
TP2                     = fixed 5R
TP2 close fraction      = 25%
automatic breakeven     = NONE
stop after TP1          = original stop, unchanged
maximum filled trades   = 1 per reference leg
```

This freezes price geometry only. It does not define account-risk percentage, lot
size, spread, commission, slippage, currency conversion, order type, or fill price.
Without signed sizing metadata and authoritative M1 execution data, output must remain
`ANALYSIS_ONLY`.

The Entry 2 structural-extreme gate is setup-specific. It never applies to Entry 1 or
Entry 3. The common 1R distance does not permit widening a failed structural stop.

## 5. Causality and fill boundary

- Completed M15 bars may create signal evidence.
- A signal at an M15 close cannot claim a same-close executable fill.
- Authoritative M1 data is required for any executable fill claim.
- Signal definition and M1 fill mechanics remain separate contracts.
- No MT5 adapter or fill simulator may be built for V2 until Entry 1 and Entry 2 close.

## 6. Closure checklist

| Decision group | Status |
| --- | --- |
| ER-only Trend test and equality boundary | SIGNED |
| Midpoint diagnostic-only role | SIGNED |
| Entry 1 eligibility | SIGNED |
| Entry 1 bias, trigger, entry, invalidation, expiry, fill | **OPEN** |
| Entry 2 NOT_TREND-only eligibility and completed-box input | SIGNED |
| Entry 2 classification, direction, multiple/dual sweep | SIGNED / IMPLEMENTED |
| Entry 2 trigger, order, structural evidence, invalidation, fill | **OPEN** |
| Common 25% / 4R / 5R / no-BE / one-fill policy | SIGNED |
| Account sizing and executable costs | **OPEN / ANALYSIS_ONLY** |
| Authoritative V2 M1 execution adapter | **DEFERRED** |

```text
ARCHITECTURE_READY = YES
CONTRACT_READY     = NO
REFACTOR_READY     = NO
```

Phase B remains unauthorized. Contract readiness changes only after the open Entry 1
and Entry 2 fields are explicitly signed and the baseline reproduction identity is
resolved.
