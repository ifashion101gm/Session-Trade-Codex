# COWORK_SWEEP_V2_SPEC — Authoritative Sweep Branch

Contract: **`COWORK_SWEEP_V2`**  
Decision date: **2026-08-21**  
Status: **RETIRED BY SESSION_FLOW_V2_SIMPLE / AUDIT HISTORY ONLY**

> Retired 2026-08-21. Post-reference Sweep observation no longer has setup-routing
> authority. See `SESSION_FLOW_V2_SIMPLE_SPEC.md`. Do not transfer this contract's
> populations, signals, or execution assumptions into the Simple strategy version.

## 1. Version boundary

This contract replaces `SWEEP_SETUP_V2_CLASSIFIER 1.0` and the completed-box Sweep
ownership model. It preserves V2 reference boxes and the signed ER session classifier:

```text
ER >= 0.40 → TREND; Sweep branch not eligible
ER < 0.40  → RANGE; activate Cowork Sweep/Range execution cycle
```

The former 81 Sweep / 1 Range split is retired as non-comparable because it scanned
inside the completed reference box. Under this contract the frozen box supplies levels;
subsequent execution candles supply Sweep evidence.

## 2. Cycles

| Cycle | Frozen reference | Activation | Sweep observation |
|---|---|---|---|
| POST_ASIAN | `[00:00,08:00)` | 08:00 UTC | closed M15 candles `[08:00,16:00)` |
| POST_LONDON | `[07:00,12:00)` | 12:00 UTC | closed M15 candles `[12:00,18:00)` |

Management may continue only under a separately implemented position-state contract.
No post-reference candle may modify the frozen High `H`, Low `L`, width `A`, ER, or
session type.

## 3. Sweep qualification

Evaluate each completed execution-window M15 candle chronologically. Pip size must come
from the signed symbol convention; minimum breach is exactly one pip.

High-side Sweep / SHORT requires all of:

```text
Open < H
High >= H + 1 pip
Close < H
confirmation = rejection_wick_ratio > 0.35 OR Close < Open
```

Low-side Sweep / LONG requires all of:

```text
Open > L
Low <= L - 1 pip
Close > L
confirmation = rejection_wick_ratio > 0.35 OR Close > Open
```

The relevant rejection wick ratios are:

```text
SHORT upper_wick_ratio = (High - max(Open, Close)) / (High - Low)
LONG  lower_wick_ratio = (min(Open, Close) - Low) / (High - Low)
```

A zero-range candle cannot pass wick confirmation. An aligned reversal body may confirm
without the wick threshold. A touch, sub-pip breach, outside-open re-entry, or close
remaining outside is not a Sweep. Swept side determines direction; external bias does
not veto a counter-bias Sweep.

## 4. Entry geometry

The signed Cowork entry reference is the outer body edge:

```text
SHORT E = max(Open, Close)
LONG  E = min(Open, Close)
D = 0.25 × frozen reference width
Stop = E - direction_sign × D
TP5  = E + direction_sign × 5D
```

No structural buffer may be added. Entry evidence and fill evidence remain separate:
the completed confirmation candle may create the level, but a retrospective fill at an
earlier price is forbidden. Order and fill mechanics are signed in
`COWORK_SWEEP_EXECUTION_V2_SPEC.md`; historical execution remains blocked until its M1
Bid/Ask and cost inputs pass the data gate.

## 5. Setup-cycle ownership

On every closed execution candle:

1. Evaluate Sweep before Range.
2. A reclaimed breach keeps the cycle on the Sweep branch while confirmation resolves.
3. Before any reclaim, a separately valid Range setup may remain eligible.
4. Sweep has precedence when both signals occur on the same candle.
5. A later distinct Sweep remains eligible subject to trade and circuit limits.

This replaces the old “first Sweep inside the box permanently owns the setup” rule.
Final setup counts are execution-cycle results, not box-completion classifications.

## 6. Management and controls adopted from Cowork

```text
TP1: close 75% after one complete reference-range move,
     normally the opposite frozen boundary
After TP1: move remaining 25% stop to entry
Runner: target 5R
Same-bar SL/target ambiguity: stop first
Maximum executed trades per cycle: 3
After a stop: 4 completed M15 bars cooldown
Cycle lock: TP5 hit OR cumulative gross loss <= -2R
Spread gate: reject when spread > 20% of stop distance
Research slippage assumption: 0.2 pip round trip
```

Spread/slippage are research assumptions, not broker execution claims. Account sizing,
commissions, currency conversion, exact bid/ask fills, partial-fill mechanics, and
end-of-window open-position treatment remain unresolved.

## 7. Implementation gate

No implementation may claim the complete workflow ready until it has:

- authoritative historical M1 Bid/Ask and signed timestamp semantics;
- signed per-symbol price precision and account commission inputs;
- bid/ask, gaps, spread, slippage, missing-bar, expiry, and collision tests;
- event-driven cycle state for cooldown, three-trade cap, and circuit lock;
- regression against the Cowork truth benchmarks without date-specific rules.

Until those fields close:

```text
COWORK_SWEEP_SPEC_ADOPTED = YES
COWORK_SWEEP_EXECUTABLE   = NO
ENTRY_2                   = BLOCKED
SCHEDULING                = BLOCKED
```
