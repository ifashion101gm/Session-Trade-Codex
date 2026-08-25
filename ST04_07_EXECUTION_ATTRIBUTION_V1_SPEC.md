# ST04_07_EXECUTION_ATTRIBUTION_V1 — Entry 2 (Sweep) Fill-Execution Attribution Study

Strategy flow: **`ST04_07_EXECUTION_ATTRIBUTION_V1`**
Version: **1.0**
Registered: **2026-08-25**
Status: **RESEARCH_ONLY / NOT EXECUTABLE** — see `STATUS.md`

## 0. Frozen invariants — read before touching this module

```
EXPERIMENT
ST04_07_EXECUTION_ATTRIBUTION_V1

PURPOSE
Determine whether MARKET or LIMIT execution preserves
more edge from the SAME qualified Sweep signals.

IMPORTANT
This experiment does NOT optimize or redefine:
- reference boxes
- Trend/Range classification
- Sweep qualification
- Sweep direction
- strategy routing
```

Any change to those five items is a change to `ER_ONLY_V2` / `SESSION_FLOW_V2_SIMPLE` / the
strategy engine, not to this study, and must be made (and re-registered) there — never inside
this module under cover of an "execution improvement." **Audited 2026-08-25**: the registered
`scripts/st04_07_execution_attribution_v1.py` does not violate this — it uses a fixed `ER < 0.40`
threshold, scans forward unbounded for the sweep rather than any fixed clock window, and defines
Contract B's limit price with exactly one reference (`reference_level`), never several tested at
once. Before extracting a ledger against real data, re-verify this holds; that verification is
cheap and this note is not a substitute for it.

## 1. Version boundary

This is a **research/attribution study**, not a live or demo-executable strategy. It does not
replace, modify, or supersede `ASIAN_SESSION_V1` (the only demo-authorized contract) or the
`SESSION_V2` research track. It reuses the `ER_ONLY_V2` regime classifier and the completed-box
Sweep-qualification concept already governed by `SESSION_FLOW_V2_SIMPLE_SPEC.md`, but is an
independent implementation scoped narrowly to one question: **for Entry 2 (Sweep) signals only,
how much of the realized edge is signal versus execution fill model?** It makes no MT5 calls —
read or write — and produces no tradeable orders. It operates entirely on historical OHLC
DataFrames supplied by the caller.

## 2. Upstream engine and regime classification

Operates on the completed Asian reference session without lookahead bias.

- **Reference window:** `00:00–07:00 UTC`, M15 resolution.
- **Efficiency Ratio:** `ER = |box_close - box_open| / sum(high_i - low_i)` over the reference
  bars (Kaufman-style, same formula family as `ER_ONLY_V2`).
- **Regime routing:**
  - `ER >= 0.40` → `TREND` → Entry 1 (Flow/Continuation) — **excluded from this study.**
  - `ER < 0.40` → `RANGE` → routed to Sweep qualification.

## 3. Entry 2 qualification rules

Once a `RANGE` regime is confirmed, subsequent price action is scanned chronologically for a
qualified boundary sweep. First qualified candle owns the result; maximum one qualified signal
per session/day.

- **Bearish sweep (short):** `High > Asian Box High` and `Close < Asian Box High` (rejection back
  inside the range).
- **Bullish sweep (long):** `Low < Asian Box Low` and `Close > Asian Box Low` (rejection back
  inside the range).

## 4. Immutable signal ledger

All qualified setups are written to `ST04_07_SWEEP_SIGNAL_LEDGER.csv` before either execution
contract is simulated, so both contracts consume the exact same population (`N` identical events).

| Field | Type | Description |
|---|---|---|
| `reference_id` | str | `{symbol}_{date}_{entry_type}_{direction}` |
| `symbol` | str | Asset identifier |
| `reference_date` | str | Asian reference-box date (`YYYY-MM-DD`) |
| `box_start` / `box_end` | str | ISO timestamps of the reference box |
| `box_open/high/low/close` | float | OHLC of the reference box |
| `box_range_pips` | float | `(high - low) / 0.0001` |
| `ER` | float | Efficiency ratio (`< 0.40`) |
| `regime` | str | Always `RANGE` |
| `sweep_timestamp` | str | M15 bar-close confirmation time |
| `sweep_direction` | str | `LONG` or `SHORT` |
| `sweep_open/high/low/close` | float | OHLC of the sweeping M15 candle |
| `sweep_extreme` | float | Extreme wick price (`high` for short, `low` for long) |
| `reference_level` | float | Box boundary swept (Asian high or low) |
| `signal_price` | float | M15 close at trigger |
| `sl_price` | float | Initial stop-loss level |

## 5. Execution contracts under attribution

**Contract A — `E2-A_NEXT_MARKET` (control):** fills at the first M1 quote after the M15 sweep
candle closes. Uses real bid/ask columns when the M1 data provides them; otherwise a **symmetric**
modeled half-spread around that quote's open (`long: ask = open + spread/2`,
`short: bid = open - spread/2`) — spread cost applies to both directions, not only to longs.
Fill rate 100% of the ledger by construction.

**Contract B — `E2-B_SWEEP_REFERENCE_LIMIT` (challenger):** a limit order placed at
`reference_level` on sweep-bar close, filled only if M1 price touches the limit net of spread
before it expires (`long: low_M1 <= limit - spread`; `short: high_M1 >= limit + spread`). Expiry
60 minutes (4 M15 bars); an unfilled order is recorded as `NO_FILL` — opportunity cost, not a
trade loss.

## 6. Unified risk geometry

Fixed across both contracts, so the comparison isolates execution attribution from
trade-management variables:

- **Stop:** `long: sweep_low - 1.0 pip`; `short: sweep_high + 1.0 pip`.
- **Risk unit:** `R = |executed_entry - stop|`.
- **Target:** fixed `1.5R` (`long: entry + 1.5R`; `short: entry - 1.5R`).

## 7. Attribution accounting

```
Realized Edge = Signal Edge + Price Improvement
                 - Missed Fill Opportunity Cost - Friction (Spread + Slippage)
```

- **Signal Edge** — Contract A's net R (market baseline).
- **Price Improvement** — benefit of Contract B's tighter risk denominator and better fill level,
  measured per-signal against Contract A's outcome on that same signal (not two independent
  aggregates).
- **Missed Fill Opportunity Cost** — foregone R from setups that hit target without retracing to
  the limit level; counted only where the market side would actually have won (a limit that skips
  a loser is not a cost).
- **Friction** — not separated from the fill price in v1; each contract's spread cost is already
  embedded in its modeled fill, not reported as a standalone line item. Decomposing it further is
  future work, not part of this version's promotion decision.

**Do not report PF/expectancy side by side and stop there** (e.g. "Limit PF 1.32 vs Market PF
1.17"). Report the full breakdown above — a limit with a lower PF but a smaller missed-fill cost
can be the better contract, and vice versa. Implemented in
`scripts/st04_07_execution_attribution_v1.py::compute_attribution()`.

## 8. Rejection / promotion funnel

```
LAYER A (theoretical geometry) -> LAYER B (authoritative M1: chronology, queue, expiry, fills)
  PF <= 1.00 or E[R] <= 0        -> REJECT (no structural edge)
  PF 1.00-1.15                   -> ARCHIVE (kept in sandbox, unfit for tick promotion)
  PF > 1.15 and E[R] > +0.05R    -> sample check: N < 100 -> RESEARCH; N >= 100 -> LAYER C (tick engine)
```

**Limit promotion gate:** Contract B may only be promoted past Layer B if it clears
`PF > 1.15`, maintains `Fill Rate >= 50%`, and `Net R (limit) >= Net R (market)` — preventing
low-sample survivor bias from a thin fill rate.

## 9. Governance

Following this project's strategy-lifecycle discipline (`STRATEGY_LEDGER.md`,
`scripts/strategy_version.py`):

- `baseline_mutation_allowed: false` — this study does not alter `ASIAN_SESSION_V1` or any
  contract in `config/strategy.yaml`.
- `promotion_allowed_from_this_sample: false` until the funnel in §8 is run and a result is
  recorded via `scripts/strategy_version.py record`.
- `sealed_data_allowed: false` — do not spend `data/sealed/` on this study; it is diagnostic
  in-sample research only, same as `config/sweep_entry_experiment.yaml`.
- No order-mutating call exists anywhere in `scripts/st04_07_execution_attribution_v1.py` — it
  reads DataFrames and writes a CSV ledger only.
- Engine: `scripts/st04_07_execution_attribution_v1.py`. Config:
  `config/st04_07_execution_attribution_v1.yaml`.
