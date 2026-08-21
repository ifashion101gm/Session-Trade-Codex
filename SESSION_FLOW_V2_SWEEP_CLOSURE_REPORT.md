# SESSION_FLOW_V2 — Signed Sweep Classifier Implementation Report

> Terminology reconciled 2026-08-21: `TREND/RANGE` are session types;
> `TREND/SWEEP/RANGE` are setup types. The current funnel authority is
> `SESSION_FLOW_V2_ROUTING_RECONCILIATION.md`.

Report date: **2026-08-21**  
Authority: **Owner authorization signing `SWEEP_SETUP_V2_CLASSIFIER 1.0`**

## Worktree and scope

```text
branch = master
HEAD = 2b58c4f011de45bd6d15fca72a091ad72aa99958
working tree before changes = dirty; all unrelated user work preserved
staged before changes = none
```

Only V2 classification, its specifications, tests, configuration, and reports were
changed. No V1 semantics, ER, timing, Range rules, risk management, broker connection,
trade, or schedule changed.

## Signed classifier

```text
Eligibility: ER < 0.40
Input: completed reference-box M15 candles only
Minimum history: one prior candle
prior_high_i = max(H[0 ... i-1])
prior_low_i  = min(L[0 ... i-1])

High Sweep: H[i] > prior_high_i AND C[i] < prior_high_i -> SHORT
Low Sweep:  L[i] < prior_low_i  AND C[i] > prior_low_i  -> LONG

Clearance: 0
Touch equality: not a Sweep
Ownership: first qualified chronologically
No qualified candidate: RANGE
```

The candidate is tested before its own high/low updates the running levels. Different-
candle same/opposite-side candidates cannot replace the first owner. A same-candle
dual-side result is `session_type=RANGE`, `setup_type=SWEEP`, direction unresolved,
and `BLOCKED_DUAL_SIDE_AMBIGUITY`. The 2.5% reclaim
model remains research-only.

Implementation: `classify_sweep` and `classify_completed_box` in
`session_strategy/session_contract.py`. The implementation is pure and has no broker
or order-writing path.

## Master router

```text
TREND?
YES → TREND
NO  → SWEEP?

SWEEP?
YES → SWEEP
NO  → RANGE
```

Asian uses `[00:00,08:00)` and activates at 08:00 UTC. London uses
`[07:00,12:00)` and activates at 12:00 UTC. Extra/post-box bars fail validation.

## Tests

```text
focused V2/Sweep: 32 passed, 0 failed, 0 skipped
full repository: 112 passed, 56 failed, 0 skipped, 0 collection errors
```

The 56 failures remain protected V1/legacy debt: 55 share the existing
ASIAN_SESSION_V1 runtime-window configuration mismatch and one is the legacy literal
midpoint Trend-entry test. No V2-focused failure remains.

The focused matrix covers high/low Sweep, breakout without reclaim, strict touch,
zero clearance, first ownership, later opposite-side non-replacement, same-candle
dual-side blocking, NO_SWEEP → Range, Trend precedence, post-box rejection, causal
update order, ER denominator/threshold/zero path, box timing, and exactly-one type.

## Oct 3 Asian classification

Source: `data/eurusd_m15_2022_10.master.csv`. Exactly 32 M15 bars with opens from
00:00 through 07:45 UTC were used. No 08:00+ candle was read.

```text
ER = 0.1076056338
Trend test = false

causal candidates:
00:45 HIGH  prior_high=0.98014 high=0.98037 close=0.98012
01:30 HIGH  prior_high=0.98165 high=0.98170 close=0.98145
05:00 LOW   prior_low =0.97851 low =0.97843 close=0.97899
05:45 HIGH  prior_high=0.98284 high=0.98344 close=0.98256

winning candidate = 00:45 HIGH
winning prior level = 0.98014
winning extreme = 0.98037
winning close = 0.98012
session type = RANGE
setup type = SWEEP
direction = SHORT
Entry 2 status = BLOCKED_BY_ENTRY_2_SPEC
```

The previously discussed 08:45 candle is outside the box and irrelevant.

## Files changed for authorization

| File | Change |
|---|---|
| `SWEEP_SETUP_V2_SPEC.md` | promoted `1.0-proposed` to signed/implemented `1.0` |
| `SESSION_FLOW_V2_SPEC.md` | made the signed classifier authoritative |
| `SESSION_FLOW_V2_ENTRY_CLOSURE.md` | closed classification fields; preserved Entry 2 execution gaps |
| `config/session_flow_v2.yaml` | added signed classifier parameters and implementation identity |
| `session_strategy/session_contract.py` | implemented pure causal scan and completed-box router |
| `tests/test_session_flow_v2_sweep_classifier.py` | added signed causal regression matrix |
| `tests/test_session_flow_v2_contract.py` | updated machine-authority assertions |
| `STATUS.md` and routing report | updated readiness and remaining blockers |
| this report | recorded evidence and Oct 3 result |

## Readiness

```text
SWEEP_RULE_SIGNED = YES
SWEEP_CLASSIFIER_IMPLEMENTED = YES
SWEEP_CLASSIFICATION_READY = YES
SESSION_CLASSIFIER_READY = YES
TREND_RANGE_SESSION_SPLIT_READY = YES
ALL_THREE_SETUP_TYPES_DETERMINISTIC = YES

TREND_ENTRY_READY = NO
SWEEP_ENTRY_READY = NO
RANGE_ENTRY_READY = SPEC_READY_IMPLEMENTATION_PENDING

OCT_3_21_CLASSIFICATION_STUDY = AUTHORIZED_NOT_RUN
OCT_3_21_EXECUTION_STUDY = BLOCKED

ANALYTICAL_SCHEDULE_READY = NO
TRADE_EXECUTION_READY = NO
LIVE_TRADING_READY = NO
SCHEDULE_CREATED = NO
```

Classification-only study gates pass: box timing, ER, signed Sweep classifier, Range
fallback, and causality tests. The wider Oct 3–21 study was not automatically run in
this pass; only the explicitly required Oct 3 Asian check was calculated.

## Remaining blockers

1. Trend Entry 1 bias, trigger, order, invalidation/expiry, and M1 fill.
2. Sweep Entry 2 trigger, price/order type, structural evidence, invalidation, M1 fill,
   and same-candle dual-side direction (intentionally blocked).
3. Range Entry 3 implementation, executable sizing/cost metadata, and broker fills.
4. V1 baseline identity and legacy test debt.

## Final verdict

```text
COMPLETED-BOX SWEEP CLASSIFIER SIGNED AND IMPLEMENTED /
ALL THREE V2 STRATEGY TYPES DETERMINISTIC /
CLASSIFICATION-ONLY STUDY AUTHORIZED /
ENTRY 1, ENTRY 2, EXECUTION, AND SCHEDULING REMAIN BLOCKED
```
