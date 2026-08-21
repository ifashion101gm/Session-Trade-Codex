# SESSION_FLOW_V2 — Simplified Router and Funnel Evidence Report

> Superseded by `SESSION_FLOW_V2_SIMPLE_VALIDATION_REPORT.md`. The new strategy
> version restores completed-reference Sweep routing and retires Cowork observation.

> **Historical completed-box evidence.** The owner-adopted
> `COWORK_SWEEP_V2_SPEC.md` supersedes this report's Sweep/Range population. The
> 8/81/1 result remains reproducible evidence for the retired classifier only.

Report date: **2026-08-21**

## Trend-direction regression

Owner-signed `BOX_DIRECTION_V1` was implemented after the outcome-blind bias study.
The 90-reference funnel remains exactly 8 Trend / 81 Sweep / 1 Range. The only
classification-record change is that the eight Trend rows now resolve to 5 LONG and
3 SHORT. No session type, setup type, or entry-engine population changed. Cross-leg
validation remains incomplete because all eight Trend rows are POST_LONDON.

## A. Worktree

```text
branch = master
HEAD = 2b58c4f011de45bd6d15fca72a091ad72aa99958
working tree before = dirty
staged before = none
user changes preserved = YES
```

No destructive Git operation, V1 semantic change, trade, broker write, or schedule
was performed.

## B. Old architecture

The preceding V2 implementation used one field/enum for the final
`TREND/SWEEP/RANGE` result and described all three as strategy classifications. It did
not encode a separate two-class session result or a canonical funnel.

## C. Final architecture

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

`TREND/RANGE` are session types. `TREND/SWEEP/RANGE` are setup types. Authoritative
lineage is `session_type → setup_type → entry_engine`. Legacy `strategy_type` is only
a deprecated alias of `setup_type`.

## D. Session classifier

```text
classifier = ER_ONLY_V2
version = 1.0
threshold = 0.40 inclusive for Trend
displacement = abs(C[N-1] - O[0])
path = abs(C[0] - O[0]) + Σ abs(C[i] - C[i-1])
ER = 0 if path = 0 else displacement / path
ER >= 0.40 -> session_type=TREND
ER < 0.40 -> session_type=RANGE
```

## E. Sweep

Eligibility is Range sessions only. `SWEEP_SETUP_V2_CLASSIFIER 1.0` uses causal prior
high/low, strict penetration, zero-clearance close-back-inside, and first-qualified
chronological ownership. High → Short; Low → Long. Same-candle dual side selects
Sweep setup but leaves direction unresolved and blocks Entry 2. The 2.5% model remains
research-only.

## F. Setup routing

```text
TREND SESSION -> TREND SETUP -> ENTRY 1
RANGE SESSION + SWEEP -> SWEEP SETUP -> ENTRY 2
RANGE SESSION + NO SWEEP -> RANGE SETUP -> ENTRY 3
```

Exactly one engine owns each valid reference box.

## G. Oct 3–21 classification funnel

Universe: EURUSD, GBPUSD, USDJPY; weekdays 2022-10-03 through 2022-10-21; Asian and
London reference boxes independently.

```text
reference expected = 90
reference valid = 90
reference invalid = 0

Trend sessions = 8
Range sessions = 82

Range with Sweep = 81
Range without Sweep = 1

Trend setups / Entry 1 = 8
Sweep setups / Entry 2 = 81
Range setups / Entry 3 = 1

entry valid = 0
entry blocked = 90
no valid entry = 0
tickets = 0 NOT_AUTHORIZED
fills = 0 NOT_AUTHORIZED
results = 0 NOT_CALCULATED
```

Classification rates: valid 100%; Trend 8.89%; Range 91.11%; Sweep among Range
98.78%; Range setup among Range 1.22%. Entry-valid and ticket rates are 0 because all
entry engines are blocked/not implemented. Fill and outcome rates are unavailable,
not zero-performance claims.

Oct 3 EURUSD Asian: ER 0.1076056338 → Range session → qualified 00:45 High Sweep
(prior 0.98014, high 0.98037, close 0.98012) → Sweep setup → Entry 2 → Short →
`SWEEP_ENTRY_SPEC_BLOCKED`. No 08:00+ candle was used.

## H. Funnel reconciliation

```text
8 Trend + 82 Range = 90 valid
81 Sweep + 1 Range setup = 82 Range sessions
8 Trend setup + 81 Sweep setup + 1 Range setup = 90 valid
```

Population identities also pass: Trend setups=Trend sessions, Sweep setups=Range with
Sweep, Range setups=Range without Sweep.

`FUNNEL_RECONCILES = PASS`.

## I. Files changed

| File | Old → new |
|---|---|
| `session_strategy/session_contract.py` | one final strategy label → normalized session/setup/engine router |
| `session_strategy/v2_funnel.py` | absent → canonical fail-closed funnel and metrics |
| `scripts/session_flow_v2_classification_study.py` | absent → reproducible classification-only study |
| `config/session_flow_v2.yaml` | three final strategy types → two session types plus three setup routes |
| `SESSION_FLOW_V2_SPEC.md` | conflated classification → authoritative hierarchy and funnel |
| `SWEEP_SETUP_V2_SPEC.md` | NOT_TREND eligibility → Range-session eligibility |
| `RANGE_SETUP_V2_SPEC.md` | strategy_type eligibility → Range session + Range setup |
| `SESSION_FLOW_V2_ENTRY_CLOSURE.md` | strategy labels → session/setup/engine mapping |
| routing and Sweep reports, `STATUS.md` | old terminology/readiness → reconciled funnel evidence |
| V2 router/Sweep/funnel/study tests | expanded causal, ownership, and population coverage |

Generated artifacts:

- `outputs/session_flow_v2_classification_2022-10-03_2022-10-21/classification_records.csv`
- `outputs/session_flow_v2_classification_2022-10-03_2022-10-21/funnel_summary.json`

## J. Tests

```text
focused V2 = 40 passed, 0 failed, 0 skipped
full repository = 120 passed, 56 failed, 0 skipped, 0 collection errors
```

Failure classification: 55 `V1_PREEXISTING/CONFIGURATION` failures share the legacy
ASIAN_SESSION_V1 runtime-window mismatch; one `LEGACY` literal midpoint Trend-entry
test fails. V2 session classifier, Sweep classifier, setup router, funnel, and study
have zero failures.

## K. Studies

```text
OCT_3_21_CLASSIFICATION_STUDY = COMPLETED_RECONCILED
OCT_3_21_EXECUTION_STUDY = BLOCKED_NOT_AUTHORIZED
```

## L. V1

`V1_BASELINE_RECONCILES = BLOCKED`; the unresolved frozen identity and legacy failures
remain separate from V2 classification readiness.

## M. Readiness

```text
BOX_TIMING_READY = YES
SESSION_CLASSIFIER_READY = YES
TREND_SETUP_SELECTION_READY = YES
SWEEP_SETUP_SELECTION_READY = YES
RANGE_SETUP_SELECTION_READY = YES
FUNNEL_CLASSIFICATION_READY = YES

TREND_ENTRY_SPEC_READY = NO
SWEEP_ENTRY_SPEC_READY = NO
RANGE_ENTRY_SPEC_READY = YES
TREND_ENTRY_IMPLEMENTED = NO
SWEEP_ENTRY_IMPLEMENTED = NO
RANGE_ENTRY_IMPLEMENTED = NO

TICKET_GENERATION_READY = NO
M1_FILL_READY = NO
RISK_MANAGEMENT_READY = PRICE_GEOMETRY_ONLY
OCT_3_21_CLASSIFICATION_STUDY_READY = YES_COMPLETED
OCT_3_21_EXECUTION_STUDY_READY = NO
ANALYTICAL_SCHEDULE_READY = NO
TRADE_EXECUTION_READY = NO
LIVE_TRADING_READY = NO
```

## N. Schedule

```text
ANALYTICAL_SCHEDULE_READY = NO
TRADE_SCHEDULE_READY = NO
SCHEDULE_CREATED = NO
```

## O. Final verdict

```text
SESSION CLASSIFIER RECONCILED /
TREND-RANGE SESSION SPLIT READY /
SWEEP-RANGE SETUP SPLIT READY /
FUNNEL RECONCILED /
ENTRY 1 BLOCKED / ENTRY 2 BLOCKED / ENTRY 3 SPEC READY, NOT IMPLEMENTED /
EXECUTION BLOCKED / NO SCHEDULE CREATED
```
