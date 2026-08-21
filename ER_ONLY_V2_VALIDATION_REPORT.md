# ER_ONLY_V2 Validation Report

Date: 2026-08-21  
Scope: Trend/Range classification only; no Sweep, setup, entry, fill, or P&L authority.

## Frozen contract

```yaml
classifier_id: ER_ONLY_V2
threshold: 0.40
equality: TREND
zero_path: RANGE
status: VALIDATED
```

## Gate and calculation

Classification accepts only a `VALID_FROZEN_SESSION` produced after the Session Box gate validates the complete half-open M15 schedule, count, uniqueness, completion time, timezone awareness, and OHLC integrity.

```text
Displacement = abs(final Close - first Open)
Path Length  = abs(first Close - first Open)
             + sum(abs(current Close - previous Close))
ER           = 0 if Path Length = 0, otherwise Displacement / Path Length
```

`ER >= 0.40` is Trend; lower is Range. Trend direction comes only from final Close versus first Open. Range direction is unassigned.

## Historical evidence

- Inputs: EURUSD, GBPUSD, USDJPY M15, 2022-10-03 through 2022-10-21.
- Reference boxes: 90 total: two legs x 15 weekdays x three symbols.
- Dataset manifests: all hashes verified with zero drift.
- Structural OHLC audit: 1,440 rows per symbol, zero reported issues.
- Independent ER reproduction: 90 of 90 matched a separately calculated formula.
- Deterministic rerun: 90 of 90 identical.
- Result: 8 Trend and 82 Range sessions.

## Acceptance tests

Passed:

- exact `0.40` returns Trend;
- zero path returns ER 0 and Range;
- incomplete, missing, extra, duplicated, mistimed, or invalid session inputs fail closed;
- a post-session candle cannot enter the frozen box;
- the result schema has no setup or entry fields;
- the `0.70` model is explicitly forbidden under `ER_ONLY_V2`.

Implementation: `session_strategy/session_contract.py`  
Regression: `tests/test_er_only_v2_validation.py`
