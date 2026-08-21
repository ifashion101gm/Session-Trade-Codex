# ENTRY_2_V2_SPEC — Sweep Execution Decision Contract

Contract: **`ENTRY_2_V2_SPEC`**  
Decision date: **2026-08-21**  
Status: **SUPERSEDED BY `COWORK_SWEEP_V2_SPEC.md` / RETAINED FOR AUDIT**

> The prior completed-box Sweep-close return model is no longer authoritative. The
> owner adopted the complete post-box Cowork Sweep branch on 2026-08-21, including
> outer-body-edge entry geometry and Cowork cycle management.

## 1. Scope and inherited authority

This contract begins only after the frozen V2 decision layer has produced:

```yaml
session_type: RANGE
setup_type: SWEEP
entry_engine: ENTRY_2
direction: LONG | SHORT
```

The signed Sweep classifier, first-qualified ownership, swept-side direction, ER
classifier, setup router, and common price-risk geometry cannot be changed here.
Classification is a permanent property of the completed reference box and has no
post-box expiry. This contract may define a pending order and its expiry; it may not
reintroduce classification expiry.

## 2. Signed Asian signal and reference-level contract

```yaml
timeframe: M15
source_event: FIRST_QUALIFIED_SWEEP_IN_COMPLETED_ASIAN_BOX
source_price: SWEEP_CANDLE_CLOSE
reference_price: SWEEP_CANDLE_CLOSE
engine_activation_time: 08:00:00 UTC
availability: ASIAN_BOX_COMPLETION
status: SIGNED
```

For the Asian leg, the selected Sweep candle Close is the signed Entry 2 reference
price. “Body” means the candle Close in this contract; no open, body edge, midpoint, or
wick price may be substituted. The historical Sweep candle time is evidence provenance,
not the signal availability or fill time. The engine first knows the result when the
complete `[00:00,08:00)` box activates at 08:00 UTC. It may never claim a retrospective
fill at the historical Sweep candle Close.

## 3. Rejected baseline candidate E2-A — next-market execution

```text
Sweep M15 candle completes
→ signal becomes known
→ submit MARKET at the first signed post-signal execution point
→ authoritative subsequent M1 data determines fill time and price
```

Required closure fields:

- exact first permissible M1 timestamp under the feed timestamp convention;
- bid/ask side used for LONG and SHORT;
- market-order requested-time and fill rule;
- spread, slippage, gap, missing-bar, and rejected-order behavior;
- pre-fill invalidation and execution-window end.

E2-A remains a research challenger and has no baseline authority because it does not
preserve the signed Sweep-body reference level as the required execution level.

## 4. Signed architecture E2-B — causal return to Sweep-close level

```text
Asian box completes at 08:00 UTC
→ identify the historical first qualified Sweep
→ create a pending-order intent at the frozen Sweep close
→ only subsequent authoritative M1 prices may prove a fill
→ no return before expiry means NO_FILL
```

Required closure fields:

- exact order placement time;
- correct LONG/SHORT limit-side semantics and bid/ask touch rule;
- price-improvement policy;
- intrabar collision ordering;
- pending-order expiry and cancellation time;
- pre-fill invalidation, spread, gaps, and missing-data behavior.

This return-to-level architecture is signed. It preserves the desired reference price
without retroactive execution and explicitly permits `NO_FILL`. Exact broker order type
and LONG/SHORT side validity are not yet signed: depending on price at 08:00, the same
level may require limit, stop, immediate-marketability handling, or rejection. The
implementation must not label every case “limit” before that rule closes.

## 5. Candidate E2-C — exact-close theoretical benchmark

```text
signal confirmed → analytical entry price = exact Sweep close
```

Status: **RESEARCH BENCHMARK ONLY / NOT AUTHORITATIVE EXECUTION**. This candidate may
measure idealized geometry but cannot create executable tickets, fills, or performance
claims unless a separate data contract proves post-confirmation executability.

## 6. Stop and target anchoring

The signed common distance is:

```text
1R = 0.25 × frozen reference range
```

The proposed fixed-risk anchor remains unsigned:

```text
LONG:  SL = actual fill price − 1R
SHORT: SL = actual fill price + 1R
```

If adopted, 4R and 5R targets must also anchor to the actual fill price. A Sweep-wick
or other structural stop is a materially different challenger and cannot be substituted
silently.

## 7. Decisions required for signature

1. Define whether LONG/SHORT uses limit, stop, or conditional order selection from the
   relationship between the 08:00 executable quote and reference level.
2. Freeze earliest order-submission timestamp after the 08:00 activation event.
3. Freeze requested-price, bid/ask, M1 touch/fill, gap, and collision semantics.
4. Freeze stop anchor and target anchor.
5. Freeze pending-order expiry and execution window.
6. Freeze every pre-fill invalidation condition and precedence rule.
7. Freeze spread, slippage, commission, and missing-data behavior.
8. Decide whether this Asian rule is separately adopted for POST_LONDON at 12:00 UTC.

Until all fields are signed, the terminal state remains:

```yaml
reference_price: SWEEP_CANDLE_CLOSE
order_type: null
requested_price: SWEEP_CANDLE_CLOSE
fill_price: null
fill_time: null
entry_status: SWEEP_ENTRY_SPEC_BLOCKED
```

No order adapter, M1 backtest, execution funnel, or schedule is authorized by this
candidate document.
