# TREND_BIAS_V2 — Candidate Study

Study status: **COMPLETE / OUTCOME-BLIND / CANDIDATE A SUBSEQUENTLY SIGNED**  
Population: **90 valid references, 8 signed-ER Trend references**  
Period: **2022-10-03 through 2022-10-21**  
Symbols: **EURUSD, GBPUSD, USDJPY**

## Controls

The study did not use entries, trade outcomes, targets, stops, costs, or optimization.
It did not change the signed router, ER threshold, Sweep classifier, Range direction,
execution contracts, or scheduling state.

## Results

| Candidate | Coverage | LONG | SHORT | Unresolved | Box-completion availability |
|---|---:|---:|---:|---:|---|
| A — completed-box Close vs Open | 8/8 (100%) | 5 | 3 | 0 | Yes |
| B — causal HTF structure | Not evaluable | — | — | — | Undefined |
| C — external prior-leg/session bias | Not evaluable | — | — | — | Undefined |

Candidate A's observed LONG/SHORT balance is 62.5% / 37.5%. By symbol: EURUSD
1 LONG / 2 SHORT, GBPUSD 1 LONG / 1 SHORT, and USDJPY 3 LONG / 0 SHORT.

## Leg split

| Leg | Trend references | LONG | SHORT | Unresolved |
|---|---:|---:|---:|---:|
| POST_ASIAN — Asian reference | 0 | 0 | 0 | 0 |
| POST_LONDON — London reference | 8 | 5 | 3 | 0 |

Candidate A is deterministic for every observed Trend reference, but this sample does
not establish cross-leg behavior: all eight Trend cases belong to POST_LONDON. That is
a coverage limitation, not an unresolved direction result.

## Candidate comparability

B and C cannot be computed reproducibly from the current contract. B lacks a signed
timeframe, feed, structure equation, direction conditions, staleness rule, and conflict
rule. C lacks a named source context, transfer equation, direction conditions, carry
duration, and missing/conflict behavior. Therefore A/B/C agreement and disagreement
rates are **not calculable**. Supplying values would require inventing strategy rules.

## Decision interpretation

Candidate A passes the predeclared simplicity, causality, reproducibility, and observed
direction-coverage checks. It does not yet pass a cross-leg evidence check because the
study contains no POST_ASIAN Trend observations. No performance claim is made, and this
report did not itself sign Candidate A. Subsequent owner authorization signed it as
`BOX_DIRECTION_V1`; the historical limitation remains:

```yaml
direction: BOX_DIRECTION_V1
entry_status: ENTRY_1_CONTRACT_INCOMPLETE
```

Raw evidence is stored in
`outputs/trend_bias_v2_candidate_study_2022-10-03_2022-10-21/`.
