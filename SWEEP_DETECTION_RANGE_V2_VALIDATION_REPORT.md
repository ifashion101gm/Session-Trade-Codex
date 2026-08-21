# RETIRED — Post-Session RANGE Sweep Detection V2 Validation Report

> Retired by `SESSION_FLOW_V2_SIMPLE` on 2026-08-21. Retained as evidence for the
> former Cowork branch only; its 55-cycle/97-signal population is not comparable to
> the completed-reference Sweep classifier.

Date: 2026-08-21  
Scope: causal Cowork Sweep signals only; no order, fill, position, or P&L authority.

## Preconditions

Sweep detection runs only when:

1. the Session Box gate returns `VALID_FROZEN_SESSION`;
2. `ER_ONLY_V2` is `VALIDATED` for that same frozen session;
3. the classification is `RANGE`;
4. execution M15 candles are completed, timezone-aware, unique, and chronological.

Trend sessions fail closed with `SWEEP_DETECTION_REQUIRES_RANGE_SESSION`.

## Validated signal behavior

- frozen session High/Low are immutable inputs;
- one-pip-or-greater penetration, including exact one-pip floating-point boundaries;
- inside Open and close-back-inside reclaim;
- wick-ratio `> 0.35` or aligned reversal-body confirmation;
- high-side Short and low-side Long;
- outer body-edge reference price;
- future-append invariance;
- signal evidence remains separate from order and fill evidence.

## Historical evidence

On the same 90 valid reference boxes:

- Trend sessions skipped: 8;
- eligible Range sessions: 82;
- Range cycles with at least one Sweep: 55;
- Range cycles without a Sweep: 27;
- total distinct Sweep signals: 97;
- first directions: 30 Long, 25 Short.

These are signal counts, not fills or trades. M1 Bid/Ask, commission, account sizing, position state, and scheduling remain blocked.

Implementation: `session_strategy/cowork_sweep_v2.py`  
Regression: `tests/test_sweep_detection_range_v2_validation.py`, `tests/test_cowork_sweep_v2.py`
