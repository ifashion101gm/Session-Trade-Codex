# SESSION_FLOW_V2_SIMPLE Validation Report

Date: 2026-08-21  
Status: **STATELESS SETUP ROUTER VALIDATED / EXECUTION BLOCKED**

## Frozen dependency chain

```text
VALID_FROZEN_SESSION
→ ER_ONLY_V2
→ TREND: Entry 1
→ RANGE: completed-reference Sweep check
    → qualified: Entry 2
    → none: Entry 3
```

The router accepts one argument: an immutable frozen session. It has no execution-window, order, fill, cost, position, or outcome input.

## Validation evidence

- 90 reference sessions: EURUSD, GBPUSD, USDJPY; Asian and London; 15 weekdays.
- Identical frozen inputs returned identical full route objects.
- Every valid session returned exactly one setup family and one entry engine.
- A post-session candle was rejected by the Session Box gate.
- Trend short-circuited Sweep inspection.
- Range plus completed-reference Sweep routed Entry 2.
- Range without completed-reference Sweep routed Entry 3.
- Same-candle dual-side Sweep retained the Sweep family while direction failed closed.

Historical routing population:

| Setup | Entry engine | Count |
|---|---|---:|
| Trend | Entry 1 | 8 |
| Sweep | Entry 2 | 81 |
| Range | Entry 3 | 1 |
| **Total** |  | **90** |

These are setup routes, not orders, fills, trades, or performance observations.

## Retired branch

`COWORK_SWEEP_V2` post-reference observation is retired for strategy selection. Its 55 swept cycles and 97 signals remain audit history and are not comparable with the 81 completed-reference Sweep routes.

Implementation: `session_strategy/session_contract.py::route_v2_simple`  
Regression: `tests/test_session_flow_v2_simple_router.py`
