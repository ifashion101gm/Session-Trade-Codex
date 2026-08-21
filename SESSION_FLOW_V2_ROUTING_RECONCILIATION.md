# SESSION_FLOW_V2 — Session Router and Funnel Reconciliation

Decision date: **2026-08-21**  
Status: **SESSION/SETUP ROUTER IMPLEMENTED / CLASSIFICATION FUNNEL RECONCILED**

## Authoritative architecture

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

`TREND/RANGE` are session types. `TREND/SWEEP/RANGE` are setup types.
`session_type → setup_type → entry_engine` is authoritative. The legacy
`strategy_type` property is a deprecated alias of `setup_type` only.

## Router equations

```text
SESSION_TREND = ER >= 0.40
SESSION_RANGE = ER < 0.40
TREND_SETUP = SESSION_TREND
SWEEP_SETUP = SESSION_RANGE AND QUALIFIED_SWEEP
RANGE_SETUP = SESSION_RANGE AND NOT QUALIFIED_SWEEP
```

Trend sessions never enter the Sweep denominator. Every valid box has exactly one
setup and one owning entry engine. Entry readiness never changes classification.

## Canonical funnel

`session_strategy/v2_funnel.py` owns funnel validation and counting. Its unique key is
contract version + symbol + date + leg + reference session. It rejects duplicate
owners, invalid boxes entering classification, inconsistent session/setup lineage,
and missing/multiple entry-engine ownership.

```text
REFERENCE_EXPECTED -> REFERENCE_VALID / REFERENCE_INVALID
REFERENCE_VALID -> SESSION_TREND / SESSION_RANGE
SESSION_RANGE -> RANGE_WITH_SWEEP / RANGE_WITHOUT_SWEEP
SESSION_TREND -> TREND_SETUP -> ENTRY_1
RANGE_WITH_SWEEP -> SWEEP_SETUP -> ENTRY_2
RANGE_WITHOUT_SWEEP -> RANGE_SETUP -> ENTRY_3
```

Entry, ticket, fill, and result fields remain explicit. Blocked engines remain in the
denominator; no row is silently dropped.

## Oct 3–21 classification-only funnel

Universe: EURUSD, GBPUSD, USDJPY. Period: 2022-10-03 through 2022-10-21,
weekdays, both V2 legs. Source files are the October 2022 master M15 datasets.

```text
REFERENCE
Expected: 90
Valid: 90
Invalid: 0

SESSION CLASSIFICATION
Trend: 8
Range: 82
Check: 8 + 82 = 90

RANGE SPLIT
Range with Sweep: 81
Range without Sweep: 1
Check: 81 + 1 = 82

SETUP SELECTION
Entry 1 / Trend: 8
Entry 2 / Sweep: 81
Entry 3 / Range: 1
Check: 8 + 81 + 1 = 90

ENTRY
Valid Entry: 0
Spec/implementation blocked: 90
No Valid Entry: 0

TICKET / FILL / RESULT
Created: 0 (NOT AUTHORIZED)
Filled: 0 (NOT AUTHORIZED)
Results: 0 (NOT CALCULATED)
```

All six reconciliation equations pass. The high Sweep frequency (81 of 82 Range
sessions) is a descriptive consequence of the signed one-prior-candle,
zero-clearance rule; it is not optimized or reinterpreted here.

Artifacts:

- `outputs/session_flow_v2_classification_2022-10-03_2022-10-21/classification_records.csv`
- `outputs/session_flow_v2_classification_2022-10-03_2022-10-21/funnel_summary.json`

## Readiness

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
SCHEDULE_CREATED = NO
```

`V1_BASELINE_RECONCILES = BLOCKED`; V1 identity/test debt remains separate.

## Final verdict

```text
SESSION CLASSIFIER RECONCILED /
TREND-RANGE SESSION SPLIT READY /
SWEEP-RANGE SETUP SPLIT READY /
CLASSIFICATION FUNNEL RECONCILES /
ENTRY 1 BLOCKED / ENTRY 2 BLOCKED / ENTRY 3 SPEC READY, NOT IMPLEMENTED /
EXECUTION BLOCKED / NO SCHEDULE CREATED
```
