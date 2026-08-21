# SWEEP_SETUP_V2 — Completed-Box Classification Contract

> **SUPERSEDED 2026-08-21 by `COWORK_SWEEP_V2_SPEC.md`.** Retained for audit and
> reproduction of the retired completed-box 81/82 classification study only.

Strategy: **`SESSION_FLOW_V2`**  
Classifier: **`SWEEP_SETUP_V2_CLASSIFIER`**  
Version: **`1.0`**  
Status: **`SIGNED / IMPLEMENTED`**  
Authority: **OWNER AUTHORIZATION — 2026-08-21**

## 1. Objective and hypothesis

For a completed reference box classified as a Range session, a candle that trades
strictly beyond a level known before that candle and closes back inside may represent
a rejected liquidity excursion. This Boolean classifier selects Sweep or the Range
fallback. It does not define Entry 2 execution or claim profitability.

## 2. Fixed upstream authority

- Eligibility: `session_type=RANGE`, produced by `ER_ONLY_V2 < 0.40`; Trend sessions short-circuit Sweep.
- Asian input: 32 completed M15 bars in `[00:00,08:00)` UTC.
- London input: 20 completed M15 bars in `[07:00,12:00)` UTC.
- Classification occurs once at box completion using no later candles.
- Final router remains Trend/Range session classification, followed by the Range-session Sweep split.
- There is no `WATCH_SWEEP`, future observation, or expiry timer.

`SPEC_GAP_SWEEP_EXPIRY = REMOVED_BY_COMPLETED_BOX_MODEL`.

## 3. Existing authority audit

| Source | Classification | Finding |
|---|---|---|
| `SESSION_FLOW_V2_SPEC.md` | CURRENT SIGNED MASTER AUTHORITY | Completed-box input and precedence signed; exact Sweep rule deliberately open |
| `SESSION_FLOW_V2_ENTRY_CLOSURE.md` | CURRENT AUTHORITY | Completed-box eligibility and classifier signed; Entry 2 remains open |
| `RANGE_SETUP_V2_SPEC.md` | SIGNED ENTRY 3 AUTHORITY | Range is downstream; its boundary rejection is not a Sweep classifier |
| `config/session_flow_v2.yaml` | CURRENT MACHINE AUTHORITY | Records signed 1.0 parameters and pure implementation identity |
| `SWEEP_ENTRY_EXPERIMENT.md`, experiment config/script/tests | RESEARCH_ONLY | Post-session 2.5% reclaim, Sweep Close, structural gate; not V2 authority |
| `versions/ledger.json` | HISTORICAL EVIDENCE | Two-sided detection recorded; “later sweep” tie-break explicitly `[UNSIGNED]` |
| V1 engine/spec/tests and worked examples | V1_PROTECTED / HISTORICAL | Close-back-inside ideas exist under different levels, timing, filters, and entry rules |
| `USER_MANUAL.md`, audit/review reports | SUPERSEDED OR NON-V2 | Describe older continuous/post-session workflow |

No source formally signs a causal completed-box V2 qualification rule. Therefore the
rule below is a proposal requiring one explicit owner decision before production code
or authoritative configuration may use it.

## 4. Signed eligibility and minimum history

```text
eligible = session_type == RANGE (ER < 0.40)
minimum prior history = 1 completed candle
candidate indices = 1 ... N-1
```

One prior candle is sufficient to establish both a causal prior high and prior low.
No swing, ATR, volume, wick/body, FVG, BOS, or discretionary structure filter is added.

## 5. Signed causal reference levels

For candidate candle `i`, calculate before examining/updating with candle `i`:

```text
prior_high_i = max(H[0 ... i-1])
prior_low_i  = min(L[0 ... i-1])
```

Test candle `i` against those levels first; only after a non-qualifying test may its
high/low update the running levels. The final box high/low is never used
retrospectively as the candidate's own reference.

## 6. Signed penetration and reclaim

Strict inequality is required; equality is a touch, not a Sweep.

```text
HIGH SWEEP:
H[i] > prior_high_i
AND C[i] < prior_high_i
direction = SHORT

LOW SWEEP:
L[i] < prior_low_i
AND C[i] > prior_low_i
direction = LONG
```

Clearance is zero. No wick/body ratio or additional confirmation exists. The 2.5%
reclaim remains separately versioned research challenger
`SWEEP_RECLAIM_2P5_CHALLENGER`; it is not mixed with baseline V2 evidence.

## 7. Signed candidate ownership

```text
multiple same-side candidates = first qualified chronologically wins
dual-side on different candles = first qualified chronologically wins
```

The scan stops at the first qualified candle. It never selects the latest, largest,
best-performing, or visually strongest candidate.

## 8. Signed same-candle dual-side policy

If one candle satisfies both high- and low-side conditions against its causal prior
levels:

```yaml
session_type: RANGE
setup_type: SWEEP
direction: null
entry_status: BLOCKED_DUAL_SIDE_AMBIGUITY
```

`SWEEP_AMBIGUOUS` is not a fourth strategy type. This safety representation is part of
the signed v1.0 classifier. It closes
classification ownership while refusing to invent an Entry 2 direction.

## 9. Signed NO_SWEEP and output

`NO_SWEEP` means the chronological scan of all eligible completed-box candles found no
qualified candidate. It is knowable at box completion and immediately selects Range.

Normalized output:

```yaml
sweep:
  qualified: <true|false>
  candidate_index: <int|null>
  candidate_time: <timestamp|null>
  side: <HIGH|LOW|DUAL|null>
  prior_level: <number|null>
  extreme: <number|null>
  close: <number|null>
  penetration: <number|null>
  reclaim_clearance: <number|null>
  classifier_version: "1.0"
direction: <SHORT|LONG|null>
```

## 10. Classification and Entry 2 boundary

A signed Sweep classification selects `session_type=RANGE`, `setup_type=SWEEP`, and
`entry_engine=ENTRY_2` independently of
Entry 2 readiness. Entry 2 trigger, signal price, order type, invalidation, structural
evidence, authoritative M1 fill, and costs remain open/research-only. Until those close:

```text
unambiguous Sweep -> session_type=RANGE, setup_type=SWEEP, entry_status=BLOCKED_BY_ENTRY_2_SPEC
same-candle dual -> session_type=RANGE, setup_type=SWEEP, entry_status=BLOCKED_DUAL_SIDE_AMBIGUITY
```

## 11. Risk boundary

This classifier does not change the signed common geometry: `1R = 25%` of reference
range, 75% at 4R, 25% at 5R, original stop unchanged, automatic breakeven false.
Those values do not supply missing Entry 2 price/fill rules.

## 12. Acceptance tests and implementation

The pure classifier in `session_strategy/session_contract.py` covers high/low Sweep, breakout without reclaim, touch
only, first-qualified ownership, no Sweep → Range, Trend precedence, post-box data
rejection, causal update ordering, same-candle dual-side blocking, and exactly-one
final setup ownership. The signed classifier remains isolated from Entry 2 and broker execution.

## 13. Signed decision register

```text
causal prior high/low model = SIGNED
minimum prior candles = 1 SIGNED
strict penetration = SIGNED
zero-clearance close-back-inside = SIGNED
high -> Short / low -> Long = SIGNED
first-qualified ownership = SIGNED
same-candle dual-side blocks Entry 2 direction = SIGNED
NO_SWEEP at completed-box end = DERIVED FROM SIGNED MASTER MODEL
```

Owner authorization accepted `SWEEP_SETUP_V2_CLASSIFIER 1.0-proposed` without changes
on 2026-08-21. The authoritative identifier is now
`SWEEP_SETUP_V2_CLASSIFIER 1.0`.
