# TREND_BIAS_V2_SPEC — Decision Contract

Contract: **`TREND_BIAS_V2_SPEC`**  
Decision date: **2026-08-21**  
Status: **`BOX_DIRECTION_V1` SIGNED / IMPLEMENTED / ENTRY 1 STILL BLOCKED**

## 1. Objective and inherited authority

This milestone chooses how an already-classified V2 Trend setup receives LONG or
SHORT. It does not reopen the signed session classifier, Sweep classifier, setup
router, or Range direction contract. It does not define an Entry 1 trigger, order,
fill, exit, sizing rule, backtest authorization, or schedule.

```text
ER >= 0.40 -> session_type=TREND -> setup_type=TREND -> ENTRY_1
ER does not determine LONG or SHORT.
```

The signed authoritative result is:

```yaml
session_type: TREND
setup_type: TREND
entry_engine: ENTRY_1
direction: LONG | SHORT | null_on_exact_equality
entry_status: ENTRY_1_CONTRACT_INCOMPLETE
```

No V1 rule is imported by implication. Midpoint and close-location fields remain
diagnostic-only under the current V2 contract.

## 2. Decisions the signed contract must close

The final signed revision must answer all six fields without hidden assumptions:

1. The exact data fields that determine Trend direction.
2. Whether those fields come from the completed reference box or external context.
3. The exact timestamp at which bias becomes knowable.
4. The complete Boolean condition for LONG.
5. The complete Boolean condition for SHORT.
6. The terminal result when neither side resolves or inputs are invalid/missing.

It must also define equality, conflicting-signal, missing-data, and timezone behavior.
Signal timing and executable fill timing must remain separate: data known at the box
close cannot claim a fill at that same unqualified close.

## 3. Signed baseline — BOX_DIRECTION_V1

```text
Data:        first completed-box open O[0], final completed-box close C[N-1]
Scope:       same completed reference box used by ER classification
Known at:    reference-box completion
LONG:        C[N-1] > O[0]
SHORT:       C[N-1] < O[0]
Unresolved:  C[N-1] = O[0], or either field is invalid/missing
```

This rule is signed as the V2 baseline. It is deterministic and causal at box completion. Using
the same box for regime and direction is not forbidden by a universal rule; it is an
explicit governance choice that requires signature. This candidate uses open-to-close
sign, not ER sign, midpoint, or the existing diagnostic close-location field.

Key limitation: regime and bias are endogenous to one box, so Trend direction expresses
the box's realized direction rather than independent broader context.

## 4. Research challenger B — causal higher-timeframe bias

```text
Data:        an explicitly named HTF instrument/feed, bars, structure feature, and rule
Scope:       external higher-timeframe context
Known at:    latest only after every required HTF bar is complete and published,
             and no later than reference-box completion
LONG/SHORT:  UNDEFINED pending a separate exact structure equation
Unresolved:  stale, missing, conflicting, incomplete, or non-causal HTF evidence
```

This can represent broader context independently of the reference box. It is not ready
to sign until timeframe, bar boundaries, feed, structure equation, precedence, staleness,
and equality behavior are specified. It adds data-dependency and alignment risk.

## 5. Research challenger C — external leg bias

```text
Data:        a specifically named earlier reference/session result
Scope:       external prior leg or session context
Known at:    the source context's signed resolution time, strictly before Entry 1 use
LONG/SHORT:  UNDEFINED pending an exact source and transfer rule
Unresolved:  source absent, invalid, stale, neutral, or conflicting
```

This can preserve a directional narrative across sessions without reusing the active
box. It is not ready to sign until source ownership, date/leg mapping, carry duration,
conflict precedence, and missing-source behavior are specified. It adds state and can
propagate an earlier classification error.

## 6. Evaluation and signature gate

BOX_DIRECTION_V1 is selected because of causal, deterministic, parameter-free,
reproducible structure—not trade outcomes. Candidates B and C are research challengers
with no baseline authority and require their missing equations before a fair comparison.
Any research comparison must be separately versioned,
use frozen evaluation windows, report unresolved coverage as well as outcomes, and may
not silently promote a candidate after observing final-test performance.

Trend direction is ready. Entry 1 remains blocked by its separate execution questions,
and no execution or schedule may be created.

## 7. Candidate study result

`TREND_BIAS_V2_CANDIDATE_STUDY.md` completed the outcome-blind comparison over the
90-reference population. Candidate A resolved all 8 Trend references (5 LONG, 3 SHORT),
but all 8 belonged to POST_LONDON and none to POST_ASIAN. Candidates B and C remain
non-evaluable because their equations and data contracts are incomplete; candidate
agreement therefore remains unavailable. Owner authorization subsequently signed
Candidate A as `BOX_DIRECTION_V1`. Cross-leg validation remains incomplete because the
study observed no POST_ASIAN Trend cases.
