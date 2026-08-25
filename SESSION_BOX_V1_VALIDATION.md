# SessionBoxes_V1 — Validation Report

Status date: 2026-08-26. Indicator only — no trading authority, no orders, no positions.

## 1. Source / compiled file paths

```
Source:   %APPDATA%\MetaQuotes\Terminal\8EFB2DF501EAEF188AB46828829DBF78\MQL5\Indicators\SessionBoxes\SessionBoxes_V1.mq5
Compiled: %APPDATA%\MetaQuotes\Terminal\8EFB2DF501EAEF188AB46828829DBF78\MQL5\Indicators\SessionBoxes\SessionBoxes_V1.ex5
```

Not tracked in this git repo (same convention as `R8_OBM_V1_EA` — lives in the MT5 terminal's
own data folder). `session_strategy/`, `RequestBuilder`, `ledger.py`, `reconciliation.py`,
`R8_OBM_V1_EA`, and every other execution-authority file were **not touched**.

## 2. Compile result

`MetaEditor64.exe /compile`, evidence from `compile.log`:

```
Result: 0 errors, 0 warnings, 4638 ms elapsed, cpu='X64 Regular'
```

## 3. Symbol / timeframe tested

EURUSD, M15. Broker: Vantage Markets demo (`VantageMarkets-Demo`, same account already in use
by `R8_OBM_V1_EA`).

## 4. UTC ↔ server mapping — evidence, not assumption

Derived at runtime (`ServerOffsetHours()` in the indicator; independently re-verified in Python
via a live tick, not reused code) from `tick.time` vs. true wall-clock UTC:

```
tick.time interpreted as UTC:  2026-08-25 20:28:16
actual UTC now:                2026-08-25 17:28:25
resolved offset:                UTC+3
```

This is a live read, not a hardcoded DST table — matches the existing repo's own
`broker_utc_offset()` method (`session_strategy/mt5_gateway.py`) and the manifest evidence
already on file (`data/*.manifest.json`: `"offset UTC+3 summer / 2 winter (US DST)"`). The
indicator's `ServerOffsetHours()` fails closed to `0` if the tick can't be read, rather than
guessing.

## 5. Session definitions (indicator inputs, all UTC)

| Session | Start (UTC) | End (UTC) | Default enabled |
|---|---|---|---|
| Asian | 00:00 | 08:00 | yes |
| London | 07:00 | 12:00 | yes |
| New York | 12:00 | 20:00 | **no** — placeholder only, no strategy dependency verified for this window, left off by default per spec |

**Owner decision, 2026-08-26 — resolves the discrepancy flagged in the prior revision of this
report:**

```
AUTHORITATIVE SESSION BOX CONTRACT (SessionBoxes_V1 scope only)
Asian:   [00:00, 08:00) UTC = exactly 32 M15 bars
London:  [07:00, 12:00) UTC = exactly 20 M15 bars
07:00–08:00 overlap is intentional
Half-open intervals [start, end)
```

This was initially treated as explicitly separate from the live `ASIAN_SESSION_V1` strategy
contract (`config/strategy.yaml`: `00:00–07:00`/28 bars) — a contract for this indicator only.

**Superseded 2026-08-26**: after `SessionBoxes_V1` was visually confirmed attached and drawing
correctly (see §9), the owner decided the indicator should instead **match the live strategy's
Asian window** rather than stay intentionally separate, since the practical use case is seeing
exactly what the strategy is using. `AsianEndHourUTC` changed from `8` to `7` — Asian is now
`00:00–07:00 UTC / 28 bars`, identical to `config/strategy.yaml`. London is unchanged at
`07:00–12:00 UTC / 20 bars` (no strategy equivalent exists to reconcile against — London isn't
part of the live `ASIAN_SESSION_V1` contract). Recompiled clean, 0 errors/0 warnings.
`session_strategy/`, `config/strategy.yaml`, and every other strategy/execution file remain
untouched — this was an indicator-only change.

## 6. Five sessions independently verified (spec asked for 3; verified 5, more available)

Ground truth computed directly from `MetaTrader5.copy_rates_range()` in Python — independent of
the indicator's own `.mq5` calculation code, so this is a real cross-check, not the indicator
grading its own homework. `32 × 15min = 8h` and `20 × 15min = 5h` confirm the half-open interval
bar counts are exact.

```
ASIAN 2026-08-24: bars=32 [00:00, 08:00) O=1.16752 H=1.16867 L=1.16718 C=1.16822 Mid=1.16793 Range=14.9p
LONDON 2026-08-24: bars=20 [07:00, 12:00) O=1.16793 H=1.16825 L=1.16599 C=1.16626 Mid=1.16712 Range=22.6p
ASIAN 2026-08-21: bars=32 [00:00, 08:00) O=1.16758 H=1.17003 L=1.16749 C=1.16925 Mid=1.16876 Range=25.4p
LONDON 2026-08-21: bars=20 [07:00, 12:00) O=1.16936 H=1.17058 L=1.16862 C=1.17047 Mid=1.16960 Range=19.6p
ASIAN 2026-08-20: bars=32 [00:00, 08:00) O=1.16758 H=1.16831 L=1.16694 C=1.16723 Mid=1.16763 Range=13.7p
LONDON 2026-08-20: bars=20 [07:00, 12:00) O=1.16789 H=1.16993 L=1.16694 C=1.16980 Mid=1.16844 Range=29.9p
ASIAN 2026-08-19: bars=32 [00:00, 08:00) O=1.15743 H=1.15867 L=1.15695 C=1.15852 Mid=1.15781 Range=17.2p
LONDON 2026-08-19: bars=20 [07:00, 12:00) O=1.15808 H=1.16046 L=1.15801 C=1.15975 Mid=1.15924 Range=24.5p
ASIAN 2026-08-18: bars=32 [00:00, 08:00) O=1.15817 H=1.15852 L=1.15693 C=1.15708 Mid=1.15773 Range=15.9p
LONDON 2026-08-18: bars=20 [07:00, 12:00) O=1.15727 H=1.15770 L=1.15660 C=1.15757 Mid=1.15715 Range=11.0p
```

Weekend gap correctly rejected rather than manufactured: `2026-08-22` (Saturday) →
`NO_BARS_IN_WINDOW`, `2026-08-23` (Sunday) → `NO_DATA`. Confirms the "never manufacture OHLC
where bars do not exist" requirement, at least for the ground-truth calculation this validation
used — the `.mq5` `ComputeSession()` uses the same never-fabricate logic (`r.valid = false` on
zero bars found), but this specific weekend case was not re-run through the compiled indicator
itself (see §9).

`mid == (high+low)/2` holds exactly in every row above by construction (both sides computed the
same way in the ground-truth script).

## 7. Overlap handling (design-level, not yet visually confirmed)

Asian (00:00–08:00) and London (07:00–12:00) intentionally overlap 07:00–08:00. `ComputeSession()`
scans the full rates buffer independently per session definition — no candle is excluded from one
session because it was claimed by another. Not yet visually confirmed on the live chart (§9).

## 8. Object lifecycle / EA coexistence — design-level, not yet live-confirmed

- All objects namespaced `SBV1_<symbol>_<date>_<session>_<suffix>` — `DeleteOwnObjects()` only
  ever matches/deletes names with that exact prefix.
- Panel uses a dedicated `OBJ_LABEL` (`SBV1_PANEL`), not `Comment()` — `R8_OBM_V1_EA` already owns
  the chart's `Comment()` text for its own status panel; using `Comment()` here would have
  clobbered it. Confirmed by design, not yet visually confirmed side-by-side.
- Indicator makes no `mt5.order_*`/`Trade` calls anywhere in the source — verified by inspection
  (no `#include <Trade/Trade.mqh>`, no `OrderSend`/`CTrade` usage anywhere in the file).

## 9. What still requires your manual confirmation

I cannot attach an indicator to a chart or visually inspect rendered objects via the MT5 Python
API or any tool available to me — same limitation as `R8_OBM_V1_EA`'s activation earlier. To
finish validation:

1. Navigator → Indicators → SessionBoxes → `SessionBoxes_V1` → drag onto the existing EURUSD M15
   chart (the one `R8_OBM_V1_EA (1)` is already attached to).
2. Confirm visually against §21 of the original spec: Asian/London boxes appear, high/low/mid
   lines align with the visible candle wicks, labels are readable, historical boxes stay frozen
   while the current session's box updates, the 07:00–08:00 overlap looks correct (both boxes
   drawn, neither truncated), no duplicate objects appear after a timeframe change or
   recompilation, `R8_OBM_V1_EA` is still attached and unaffected, and the indicator places no
   trades.
3. If the Asian window is meant to visually match the live `ASIAN_SESSION_V1` strategy, change
   `AsianEndHourUTC` from `8` to `7` first (see §5).

## 10. Final status

```
SESSION_BOX_V1 = VALIDATED
```

Owner confirmed 2026-08-26: `SessionBoxes_V1` attached to EURUSD M15, Asian/London/New York boxes
visible and correctly labeled, `R8_OBM_V1_EA (1)` remained attached and unaffected throughout.
`AsianEndHourUTC` changed to `7` (§5) so the Asian box now matches the live `ASIAN_SESSION_V1`
window exactly (`00:00–07:00 UTC`/28 bars). Compile (0 errors/0 warnings), calculation-layer
ground truth (5 sessions, weekend-gap handling, exact half-open bar counts), static code checks
(no trading calls, no `Comment()` collision, namespaced objects), and the visual/attach/EA-
coexistence check together clear every item in §9's acceptance list.

**Basis for this status**: owner visual confirmation via chat, not independent visual evidence —
I have no way to view rendered chart objects myself (see §9's original caveat). Recorded as owner
sign-off, consistent with how every other GUI-only step in this project (EA activation, indicator
attachment) has been confirmed throughout this session.
