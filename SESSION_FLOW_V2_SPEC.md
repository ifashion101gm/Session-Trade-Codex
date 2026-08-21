# SESSION_FLOW_V2 — Superseded Contract

> Superseded by `SESSION_FLOW_V2_SIMPLE_SPEC.md` on 2026-08-21. Retained for audit
> history. The Simple contract disables post-reference setup observation.

Strategy ID: **`SESSION_FLOW_V2`**  
Decision date: **2026-08-20**  
Status: **TREND ROUTE SIGNED / RANGE EXECUTION BRANCH REOPENED FOR COWORK SWEEP / NO EXECUTION AUTHORITY**

## Owner decision and objective

V2 classifies each immutable completed reference box once. It does not continuously
classify, observe post-session candles, wait for a boundary event, or use a Sweep
expiry timer. This is a causal specification and implementation contract, not an
optimization, trading authorization, or scheduling authorization.

## Time and data contract

All intervals are half-open UTC intervals using completed M15 bars only.

| Leg | Reference box | Bars | Activation | Myanmar time |
|---|---|---:|---|---|
| Leg A | Asian `[00:00,08:00)` | 32 | 08:00 UTC | 14:30 MMT |
| Leg B | London `[07:00,12:00)` | 20 | 12:00 UTC | 18:30 MMT |

The 07:00–08:00 overlap is intentional. At activation the engine freezes reference
start/end, OHLC, range, midpoint, completed candles, path length, displacement, ER,
and signed Sweep diagnostics. Missing, duplicate, incorrectly timed, or invalid OHLC
data fails validation; it is never coerced to Range. Post-reference M15/M1 candles
cannot alter reference levels, ER, `session_type`, or `setup_type`.

## Authoritative session and setup router

```text
REFERENCE BOX COMPLETE
        ↓
TREND OR RANGE
       /      \
    TREND     RANGE
      ↓         ↓
   ENTRY 1    SWEEP?
              /    \
            YES     NO
             ↓       ↓
          ENTRY 2  ENTRY 3
```

Classification uses all and only completed bars inside the reference box. No
post-session observation is used. Authoritative session types are exactly `TREND` and
`RANGE`. Authoritative setup types are exactly `TREND`, `SWEEP`, and `RANGE`.

`session_type=TREND → setup_type=TREND → ENTRY_1`;
`session_type=RANGE` activates the post-box Cowork Sweep/Range execution cycle;
a qualified Sweep owns Entry 2 and otherwise-valid Range evidence may own Entry 3.

`session_type → setup_type → entry_engine` is authoritative. The legacy
`strategy_type` field is a deprecated compatibility alias of `setup_type`, never a
session regime. Exactly one entry engine owns every valid box.

## ER_ONLY_V2 1.0 Trend classifier

For completed closes `C[0] ... C[N-1]` and first-bar open `O[0]`:

```text
directional_displacement = abs(C[N-1] - O[0])
path_length = abs(C[0] - O[0]) + sum(abs(C[i] - C[i-1]), i=1..N-1)
ER = 0 if path_length == 0 else directional_displacement / path_length
```

`ER >= 0.40` selects `session_type=TREND` and Sweep is not evaluated. `ER < 0.40`
selects `session_type=RANGE`, which proceeds immediately to the completed-box Sweep test. ER is not
direction. Midpoint diagnostics are retained but have no routing authority.

## Cowork post-box Sweep branch

Only `session_type=RANGE` boxes are eligible. The completed box freezes levels, then
`COWORK_SWEEP_V2_SPEC.md` evaluates subsequent closed execution-window M15 candles.
This owner-adopted branch supersedes the completed-box scanner described below.

<!-- Historical completed-box model retained for audit only.
Only `session_type=RANGE` boxes are eligible. Sweep input is the same immutable completed box;
Asian uses `[00:00,08:00)` and London uses `[07:00,12:00)`. Box completion is the
classification endpoint: no qualifying Sweep in the box means `NO_SWEEP` and selects
Range. `SPEC_GAP_SWEEP_EXPIRY` is removed by this model.

The authoritative qualification rule is `SWEEP_SETUP_V2_CLASSIFIER 1.0`, signed by
owner authorization on 2026-08-21 and implemented as the pure completed-box scanner
in `session_strategy/session_contract.py`. It uses causal prior highs/lows, strict
penetration, zero-clearance close-back-inside, and first-qualified chronological
ownership. High-side → Short and low-side → Long. A same-candle dual-side result keeps
`session_type=RANGE`, selects `setup_type=SWEEP`, leaves direction unresolved, and
blocks Entry 2. The 2.5% reclaim,
08:00–16:00 observation, Sweep Close entry, and structural-stop gate are research-only;
the post-session window is superseded for V2 classification.

For a Range session, the signed scanner deterministically returns qualified Sweep or
`NO_SWEEP`; it never waits or emits a fourth strategy type. -->

## Range fallback and Entry 3

`RANGE_SETUP = SESSION_RANGE AND NOT_SWEEP_IN_COMPLETED_BOX`. Entry 3 is governed by
signed `RANGE_SETUP_V2_SPEC.md`. `NO_VALID_RANGE_ENTRY` retains both
`session_type=RANGE` and `setup_type=RANGE`.

## Entry and execution separation

Classification, entry trigger, order, fill, and management are separate stages.
Entry 1 remains blocked on causal bias source/timing, trigger, price, order type,
invalidation, expiry, and M1 fill. Entry 2 classification is ready, but execution
remains blocked on trigger, price, order type, invalidation, structural evidence, and
M1 fill. Entry 3 is specification-ready but not implemented for V2.

Direction is setup-specific. Trend direction is signed as `BOX_DIRECTION_V1`:
final Close above first Open → LONG, below → SHORT, and equality → unresolved. Sweep direction is signed as high-side Sweep → SHORT and
low-side Sweep → LONG. Range direction remains governed by boundary rejection in
`RANGE_SETUP_V2_SPEC.md`. ER is unsigned and never supplies LONG or SHORT. Entry 1
remains blocked as `ENTRY_1_CONTRACT_INCOMPLETE` on its trigger, price, order,
invalidation, expiry, and M1 fill—not on direction.

## Classification funnel

Every expected box has one lineage record. The canonical funnel is expected →
valid/invalid → Trend/Range session → Range Sweep/no-Sweep split → Entry 1/2/3 owner.
Classification equations must reconcile exactly. Entry, ticket, fill, and result
stages remain explicit blocked/unavailable states and may not silently drop rows.

The common signed price-risk model is `1R = 25%` of reference range, close 75% at 4R,
close the remaining 25% at 5R, and keep the original stop unchanged; automatic
breakeven is false. Account sizing and executable cost metadata remain unsigned and
analysis-only.

## Safety and version isolation

V1 behavior and `SSPF_V1_3_BASELINE_FROZEN` are not modified by this contract. No MT5
adapter, order placement, live/demo trading, or automated schedule is authorized.
Future analytical activation points are 08:00 and 12:00 UTC only after implementation
and regression gates pass.
