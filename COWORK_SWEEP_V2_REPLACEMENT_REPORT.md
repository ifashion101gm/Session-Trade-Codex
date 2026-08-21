# COWORK_SWEEP_V2 — Replacement Report

Date: **2026-08-21**  
Scope: **Signal classification only; no orders, fills, P&L, or scheduling**

## Authority change

Owner authorization replaced the completed-box `SWEEP_SETUP_V2_CLASSIFIER 1.0` with
the complete post-reference Claude/Cowork Sweep branch. The retired 81/82 result is
preserved for audit but is not comparable to the replacement because its evidence
window and qualification rules differ.

## Replacement population

| Measure | Result |
|---|---:|
| Valid reference cycles | 90 |
| Trend sessions | 8 |
| Range sessions entering Cowork cycle | 82 |
| Range cycles with at least one Cowork Sweep | 55 |
| Range cycles without a Cowork Sweep | 27 |
| Total distinct Cowork Sweep signals | 97 |
| First Sweep LONG | 30 |
| First Sweep SHORT | 25 |

Leg split:

| Leg | Range cycles | With Sweep | Without Sweep | Total Sweep signals |
|---|---:|---:|---:|---:|
| POST_ASIAN | 45 | 32 | 13 | 66 |
| POST_LONDON | 37 | 23 | 14 | 31 |

The study applies one-pip symbol conventions: EURUSD/GBPUSD `0.0001`, USDJPY `0.01`.
It uses only closed M15 execution-window candles and does not calculate Range-entry
events, orders, fills, management outcomes, costs, or performance.

## Implemented signal rules

- frozen reference High/Low and V2 ER Range eligibility;
- post-reference closed-M15 observation;
- minimum one-pip breach;
- candidate Open strictly inside the swept boundary;
- close-back-inside reclaim;
- wick ratio greater than 0.35 or aligned reversal body confirmation;
- high Sweep SHORT / low Sweep LONG;
- outer body edge reference price;
- chronological, future-append invariant evidence.

## Remaining blockers

The complete execution cycle is specified but not executable. Order type, signal/order
lag, bid/ask fills, gaps, expiry, partial fills, account sizing, currency conversion,
commissions, and end-of-window positions must close before an event-driven backtest.
Cooldown, three-trade cap, breakeven movement, and circuit lock require that fill/position
state and therefore remain unimplemented. Entry 2 and scheduling stay blocked.
