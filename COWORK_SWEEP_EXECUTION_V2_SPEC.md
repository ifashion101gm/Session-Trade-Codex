# COWORK_SWEEP_EXECUTION_V2_SPEC — Order and Fill Contract

Contract: **`COWORK_SWEEP_EXECUTION_V2`**  
Decision date: **2026-08-21**  
Status: **RETIRED WITH COWORK SWEEP BRANCH / AUDIT HISTORY ONLY**

> Retired 2026-08-21 for `SESSION_FLOW_V2_SIMPLE`. These mechanics are not the
> Entry 2 execution contract for the completed-reference Sweep route.

## 1. Signal and activation

The order cannot exist before the qualifying M15 Sweep candle ends. The first eligible
M1 observation must begin at or after that end timestamp; no overlapping M1 interval
from the forming signal candle may be used.

```text
SHORT requested price = max(Sweep Open, Sweep Close)
LONG requested price  = min(Sweep Open, Sweep Close)
order type             = LIMIT
```

## 2. Authoritative M1 Bid/Ask fills

LONG is a BUY LIMIT filled against Ask. SHORT is a SELL LIMIT filled against Bid.
Only subsequent M1 observations may fill an order:

```text
BUY LIMIT:
  AskOpen <= limit → fill AskOpen
  otherwise AskLow <= limit → fill limit

SELL LIMIT:
  BidOpen >= limit → fill BidOpen
  otherwise BidHigh >= limit → fill limit
```

The open-price cases allow causal price improvement after a gap. Midpoint, last price,
M15 OHLC, and the historical signal candle cannot substitute for Bid/Ask evidence.

## 3. Exact expiry

```text
POST_ASIAN:  cancel unfilled order at 16:00:00 UTC
POST_LONDON: cancel unfilled order at 18:00:00 UTC
```

Only M1 intervals starting strictly before expiry are eligible. An unfilled order becomes
`NO_FILL_EXPIRED`. A Sweep confirmed at or after expiry creates no order.

## 4. Fill-anchored risk

For fill `F`, frozen reference width `A`, and `R = 0.25A`:

```text
LONG:  SL = F - R; TP5 = F + 5R
SHORT: SL = F + R; TP5 = F - 5R
```

No structural-stop or Sweep-wick adjustment applies to this baseline.

## 5. Gaps and exit execution

Stops are market exits and can fill adversely through the level:

```text
LONG SL:  BidOpen <= SL → BidOpen; otherwise BidLow <= SL → SL
SHORT SL: AskOpen >= SL → AskOpen; otherwise AskHigh >= SL → SL
```

Targets are limit exits and can receive opening improvement:

```text
LONG TP:  BidOpen >= TP → BidOpen; otherwise BidHigh >= TP → TP
SHORT TP: AskOpen <= TP → AskOpen; otherwise AskLow <= TP → TP
```

If one M1 bar contains both stop and target evidence without finer authoritative
sequencing, process STOP first. Stored tick evidence may replace this assumption only
when used consistently for the complete run.

## 6. Cost layers

Every research run must produce separately labelled results:

1. `ZERO_COST_MECHANICAL`: spread, slippage, and commission are zero; this validates
   mechanics and is not achievable-performance evidence.
2. `REALISTIC_COST`: observed historical Bid/Ask spread, adverse slippage, and signed
   commission inputs. The initial Cowork research slippage is `0.1 pip per side`
   (`0.2 pip round trip`). If Bid/Ask or commission is missing, realistic net results
   are `UNAVAILABLE`, never silently zero.

Gross P&L, spread, slippage, commission, and net P&L must be separate fields.

## 7. Position-state gate

Only after entry, stop, TP1, and TP5 fill tests pass may the event engine enable the
four-M15 cooldown, three-trade cap, TP1→breakeven transition, cumulative `-2R` lock,
and TP5 cycle lock.

```text
ORDER_AND_FILL_MECHANICS = SIGNED
HISTORICAL_FILL_RUN      = BLOCKED_ON_M1_BID_ASK
REALISTIC_COST_RESULT    = UNAVAILABLE_PENDING_COMMISSION
POSITION_STATE           = BLOCKED_AFTER_FILL_GATE
SCHEDULING               = BLOCKED
```
