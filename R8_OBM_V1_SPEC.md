# R8_OBM_V1 — Range-8 One-Bar-Momentum Forward-Test EA

Strategy flow: **`R8_OBM_V1`**
Version: **1.00** (EA `#property version`)
Registered in this repo: **2026-08-25**
Status: **FORWARD_TEST / SIGNAL_ONLY** — see `STATUS.md`

## 1. What this is, and why it's different from everything else in this repo

`R8_OBM_V1` is a compiled **MQL5 Expert Advisor** running directly inside the MT5 terminal —
**it does not live in this git repository.** Source and binary live in the terminal's own data
folder:

```
%APPDATA%\MetaQuotes\Terminal\8EFB2DF501EAEF188AB46828829DBF78\MQL5\Experts\R8_OBM_V1_EA.mq5
%APPDATA%\MetaQuotes\Terminal\8EFB2DF501EAEF188AB46828829DBF78\MQL5\Experts\R8_OBM_V1_EA.ex5
```

with its own CSV audit journal at
`MQL5\Files\R8_OBM_V1_EURUSD_journal.csv`. This registration exists so that its lineage, status,
and validation history are recorded in one place rather than living only in an MT5 data folder
nobody else on this project would think to check.

It is registered here as documentation and governance tracking only — this repo does not build,
deploy, or version-control the `.mq5`/`.ex5` files themselves.

## 2. Relationship to the Python `mt5_range_bar_live.py`

Both implement the same idea (synthetic tick-built range bars, one-bar momentum, fixed R:R), but
they are **independent implementations** with different magic numbers and no shared code:

| | `R8_OBM_V1_EA` (this) | `mt5_range_bar_live.py` |
|---|---|---|
| Language / runtime | MQL5, runs inside MT5 | Python, must be launched separately |
| Magic number | `8101501` | `108801` |
| Default range | 8.0 pips | 8.0 pips |
| Default R:R | 1.5R | 1.5R (`fixed_rr`) |
| Trading gate | `InpAllowDemoTrading` (default **false**) | none — trades the instant a bar closes |
| Real-account block | Explicit, hard-coded, unconditional | Checked once at `initialize_mt5()`, not re-checked per order |
| Audit trail | CSV journal + `OnTradeTransaction` deal log | Python `logging` only |

`R8_OBM_V1_EA` is materially safer by design — see §4.

## 3. Relationship to the rejected `ST-01 RANGE8 MOMENTUM` backtest finding

Per the trader's own research-portfolio notes (not stored in this repo, referenced in
conversation 2026-08-25): `ST-01 RANGE8 MOMENTUM` — synthetic PF 1.43, true tick structure PF
1.08, bid/ask-realistic PF 0.81 — was marked **`→ REJECT V1`**. This EA forward-tests
essentially that same idea live, in signal-only mode, which is a reasonable way to sanity-check a
backtest verdict rather than a contradiction of it — **provided it stays signal-only until a
genuine forward-test edge is demonstrated**, not used to relitigate a rejection by hoping live
conditions differ.

## 4. Safety design (as built, read from `R8_OBM_V1_EA.mq5`)

- `InpRequireDemoAccount` (default `true`) plus an **unconditional** second check
  (`AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL`) that blocks real-account
  order submission regardless of any input setting.
- `InpAllowDemoTrading` (default **`false`**) gates actual order submission independently of the
  demo-account check — with `false`, the EA still builds range bars and logs every signal to CSV,
  but never calls `trade.Buy`/`trade.Sell`.
- One position at a time (`InpOnePositionOnly`), a spread gate (`InpMaxSpreadPips`), and broker
  minimum-stop-distance validation before any order would be attempted.
- Every completed bar, every signal (blocked or not), every order attempt/rejection/acceptance,
  and every deal (via `OnTradeTransaction`) is written to
  `MQL5/Files/R8_OBM_V1_EURUSD_journal.csv` with a `reason` code — a real audit trail, not just a
  terminal log line.

## 5. Validation performed 2026-08-25

- **Current account**: confirmed demo (`VantageMarkets-Demo`, login `...746`, `trade_mode=0`) via
  direct MT5 query, matching the EA's own `OnInit` log line `"Account mode: DEMO"` at its most
  recent attach (`21:02:54` per `MQL5/logs/20260825.log`).
- **Current execution gate**: `InpAllowDemoTrading = false` confirmed both on the live chart panel
  and in the terminal log (`"Allow demo trading: false"`) — signal-only, cannot place an order in
  its current configuration.
- **Journal cross-check**: `R8_OBM_V1_EURUSD_journal.csv` shows 6 completed range bars since
  2026-08-24, every one logged `reason=SIGNAL_ONLY_ALLOW_DEMO_TRADING_FALSE` — zero orders
  attempted, zero accepted. Matches the live panel's `Accepted orders: 0`.
- **Magic-number collision check**: `8101501` does not collide with `123456`
  (`ASIAN_SESSION_V1` execution layer / the manual demo test scripts) or `108801`
  (`mt5_range_bar_live.py`).
- **Source/binary consistency**: the running `.ex5` (compiled 2026-08-25 19:57) postdates the last
  `.mq5` source edit (2026-08-24 20:04) — the running binary matches the current source, no drift.
  A duplicate `(1)` copy of both files exists in the same folder and is byte-identical to the
  primary — not a divergent variant, just a duplicate.

## 6. Important finding from this validation — real-account exposure

`MQL5/logs/20260825.log` shows the EA (the `(1)` instance) initializing at **19:00:27 UTC+... with
`Account mode: REAL`**, logging `"HARD SAFETY: REAL account detected. Orders are blocked."` — the
safety check worked exactly as designed, and no order was attempted. But it confirms this MT5
terminal was switched to a **real-money account** earlier the same day the EA was attached, before
being switched back to the demo account by the time of this validation. The terminal's own
Navigator panel lists at least two live accounts alongside the demo
(`VantageGlobalPrimeLLP-Live`, `VantageMarkets-Live 7`). This is not a defect in the EA — the
hard block is exactly why nothing happened — but it is a real fact about how this terminal is
being operated: real and demo accounts are both active in the same terminal session, and only this
EA's own hard-coded check stood between a real-account attach and an attempted real order. No
other artifact in this repo (the Python execution layer, `mt5_range_bar_live.py`) has been
observed running against a real account; this is the first evidence any component has been
attached to one, even briefly and without trading.

## 7. Governance

- `promotion_allowed_from_this_sample: false` — no trades have occurred; there is nothing to
  promote yet.
- Must remain `InpAllowDemoTrading = false` until a forward-test sample with adequate signal count
  is collected and reviewed against the `ST-01` backtest rejection findings, per the same
  discipline `STRATEGY_LEDGER.md` applies to every other strategy in this project.
- `live_execution_authorized: false` unconditionally — the EA's own real-account block already
  enforces this at the code level, independent of anything in this repo.
