# Session Strategy Assistant — Implementation Plan

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

> **Status note (revised 2026-08-11).** This is the *original* delivery plan and parts of it were
> never built as written. What actually shipped is specified in `STRATEGY_SPEC.md` and mapped in
> `ARCHITECTURE.md`; the gap between plan and code is itemised in `AUDIT_REPORT.md`.
>
> - **Delivered:** Phases 1–6 in substance — read-only gateway, session/bias calculation,
>   deterministic setup engine with named gates, risk and broker validation, ticket/chart/journal
>   output, and read-only monitoring. Tickets calculate manual partial targets and breakeven
>   instructions.
> - **Delivered late:** Phase 0. `STRATEGY_SPEC.md` was never produced during delivery; it was
>   reconstructed from source on 2026-08-11 and is now the authority for the rules.
> - **Not delivered:** Phase 7 (backtest and demo forward test) in full, the `tests/fixtures/`
>   golden-case layer from §8, automated management, market entries, TREND trailing mechanics, and
>   the news/spread/range filters listed in §3.
> - **Withdrawn:** H1 / higher-timeframe bias. The strategy is M15-only by trader instruction, so
>   this was never a requirement — it was an incorrect assumption in the original plan. Every
>   reference to a bias timeframe below (§3.3, §4, §6 Phase 2) should be read as withdrawn.
> - **Superseded:** §5 (project structure) and §7 (configuration template) below have been
>   rewritten to describe what exists. Their original contents did not match the code.

## 1. Objective

Build a local, read-only MT5 analysis assistant that turns live and historical market data into deterministic Session Trading Strategy tickets. The assistant will never place, modify, or close orders. The trader remains responsible for visual confirmation, position approval, execution, and management.

Initial deployment will use the connected MT5 demo account. Live-account use is outside the first release.

## 2. Safety Boundary

The application may:

- Connect to the locally running MT5 terminal.
- Read terminal, account, symbol, tick, candle, position, and pending-order data.
- Calculate session levels, setup classifications, risk, volume, and management thresholds.
- Generate charts, tickets, warnings, and journal records.

The application must not:

- Call MT5 order-send, position-close, order-delete, or position-modification functions.
- Change terminal or account settings.
- log in to another account.
- Present a trade when required data is incomplete, stale, or inconsistent.

## 3. Decisions Required Before Coding Strategy Logic

Create a signed-off strategy specification containing:

1. Exact broker symbol, including any suffix.
2. Reference-session start, end, and canonical timezone.
3. ~~Analysis and bias timeframes.~~ **Resolved: M15 only, single timeframe, no bias timeframe.**
4. Objective bullish, bearish, and neutral bias rules.
5. Objective range-versus-trend rules.
6. Sweep depth, close-back-inside, and confirmation requirements.
7. Exact entry trigger and pending-versus-market rule.
8. Stop placement rule and minimum structural invalidation rule.
9. Partial-exit priority relative to the 5R target.
10. Maximum spread, minimum range, maximum range, and data-freshness limits.
11. Per-trade risk, maximum daily loss, and maximum trades per session.
12. News-filter policy and the source of event data, if used.

Until these are defined, ambiguous conditions must return `NO_TRADE` rather than being guessed.

## 4. Proposed Architecture

```text
MT5 terminal
    |
    v
Read-only MT5 gateway
    |
    +--> timestamp/session normalization
    +--> candle and tick validation
    |
    v
Strategy engine
    +--> session levels
    +--> [WITHDRAWN] higher-timeframe bias — strategy is M15-only
    +--> market-state classification
    +--> sweep/entry detection
    |
    v
Risk and broker validator
    +--> SL/TP calculations
    +--> tick-value-based volume
    +--> spread/stops/volume checks
    |
    v
Trade ticket + chart + journal
    |
    v
Human approval and manual MT5 execution
```

## 5. Project Structure

*Revised 2026-08-11 to describe the delivered structure. The original fifteen-module layout in
this section was never built; the package was consolidated into eight modules, each owning one
concern. See `ARCHITECTURE.md` §2 for the ownership rules.*

```text
session_strategy/
  __init__.py        version constant
  __main__.py        duplicate entry point (undocumented; see finding A15)
  cli.py             argument parsing, orchestration, exit codes
  config.py          strategy.yaml loading and the config hash
  models.py          data shapes; derived status
  mt5_gateway.py     the only module importing MetaTrader5 — the safety boundary
  engine.py          all strategy calculation and gate evaluation
  journal.py         SQLite persistence, MT5 reconciliation, risk statistics
  render.py          ticket.md, chart.png, the fixed disclaimer
  lifecycle.py       two-stage release gate
config/
  strategy.yaml      active strategy configuration (no .example variant exists)
  lifecycle.json     release-gate thresholds
tests/
  test_engine.py     17 tests — session validation, ER, sweeps, mappings, gates
  test_journal.py     2 tests
  test_lifecycle.py   2 tests
  test_safety.py      4 tests — read-only boundary, quote-refresh behaviour
data/
  sspf_journal.sqlite3
outputs/
  <session-date>/<analysis-id>/{analysis.json,ticket.md,chart.png}
sspf.py                documented entry point
scripts/run_session_check.ps1   canonical version-controlled scheduler entrypoint
requirements.txt
```

Not built: `tests/fixtures/`, `config/strategy.example.yaml`, and the per-concern test files
listed in the original plan.

## 6. Delivery Phases

### Phase 0 — Freeze the Strategy Specification

Deliverables:

- `STRATEGY_SPEC.md` with formulas and decision tables.
- Example tickets for valid sweep, range, trend, and no-trade cases.
- Explicit timezone and daylight-saving policy.
- Defined management-event priority.

Acceptance criteria:

- Two people applying the rules to identical candles produce the same classification, entry, SL, and TP.
- Every ambiguous or missing-data case has a defined outcome.

### Phase 1 — Read-Only MT5 Data Layer

Implement:

- MT5 initialization and clean shutdown.
- Masked account and permission health check.
- Exact symbol resolution and symbol metadata retrieval.
- Completed-candle retrieval by UTC timestamp range.
- Current bid, ask, spread, and server/terminal status.
- Read-only open-position and pending-order retrieval.
- Retry, timeout, stale-data, and empty-data handling.

Important timestamp rule:

- Store all timestamps as timezone-aware UTC values.
- Convert to the configured session timezone only when selecting sessions or displaying output.
- Remove hard-coded broker-offset arithmetic from strategy calculations.

Acceptance criteria:

- Candle count and OHLC values match the MT5 chart for selected timestamps.
- Session selection remains correct across midnight and daylight-saving changes.
- No trading function exists in the gateway interface.

### Phase 2 — Session and Bias Calculations

Implement:

- Reference-session candle filtering using exact start/end timestamps.
- High, low, range, equilibrium, and 25% range calculations.
- ~~Configured higher-timeframe bias calculation.~~ **Withdrawn — M15-only strategy.**
- Previous-day/session context if required by the specification.
- Input validation for missing bars, gaps, zero ranges, and incomplete sessions.

Acceptance criteria:

- Calculations pass hand-worked fixtures.
- The engine refuses analysis before the reference session is complete unless explicitly operating in preview mode.

### Phase 3 — Deterministic Setup Engine

Implement the setup pipeline in a fixed order:

1. Check session validity and trading window.
2. Calculate bias.
3. Classify market as `RANGE`, `TREND`, or `UNCLASSIFIED`.
4. Detect boundary interaction and liquidity sweep.
5. Confirm the configured entry trigger.
6. Return `SWEEP`, `RANGE`, `TREND`, or `NO_TRADE` with reason codes.

Each decision should include evidence, for example:

```text
classification: SWEEP
evidence:
  swept_level: session_low
  penetration: 1.20
  candle_closed_back_inside: true
  bias: bullish
rejected_conditions: []
```

Acceptance criteria:

- Identical input always produces identical output.
- Tests cover boundary equality, one-tick penetrations, large gaps, and contradictory signals.
- The engine reports why a setup was rejected.

### Phase 4 — Risk, Volume, and Broker Validation

Implement:

- SL distance from the strategy formula.
- Structural invalidation checks.
- 5R target and partial-exit level calculations.
- Monetary risk from the lower of current balance and equity.
- Volume using MT5 order-profit estimation or tick value, contract size, tick size, and account currency.
- Rounding to broker volume step and conservative risk rounding.
- Broker checks for minimum stop distance, price digits, volume limits, and current spread.
- Net-R estimates after spread and configured commission assumptions.

Acceptance criteria:

- Calculated worst-case planned loss does not exceed the configured risk after rounding.
- Invalid or oversized trades return `NO_TRADE` with a reason.
- Example ticket arithmetic reconciles exactly.

### Phase 5 — Ticket, Chart, and Journal Output

Produce a ticket containing:

- Data timestamp and freshness.
- Account type and masked login.
- Symbol and session definition.
- Session high, low, range, and equilibrium.
- Bias, market state, setup, and supporting evidence.
- Entry type and price.
- SL, TP, partial-exit level, R multiples, and calculated volume.
- Spread and broker-validation results.
- Invalidation and management rules.
- A prominent `MANUAL EXECUTION ONLY` label.

Extend the existing chart renderer to show session shading, sweep candle, entry, SL, TP, partial exit, and current price. Save a machine-readable JSON analysis beside a human-readable Markdown ticket. Journal only strategy data; do not persist credentials or full account identifiers.

Acceptance criteria:

- Ticket values match the machine-readable result and chart annotations.
- Every ticket includes a unique analysis ID and candle-data timestamp.

### Phase 6 — Read-Only Position Monitoring

Implement on-demand monitoring that:

- Matches an open position by symbol and ticket metadata where possible.
- Reports current R, distance to SL/TP, session-boundary status, and partial-exit/breakeven conditions.
- Issues informational prompts only; it never changes the position.
- Detects that a position was manually changed and recalculates from actual MT5 values.

Acceptance criteria:

- Monitoring remains correct after partial closes and manual SL changes.
- No action is described as completed unless MT5 data confirms the human performed it.

### Phase 7 — Backtest and Demo Forward Test

Backtest requirements:

- Use completed historical candles without look-ahead.
- Model spread, commission, slippage assumptions, partial exits, and simultaneous intrabar SL/TP ambiguity conservatively.
- Report trade count, expectancy, win rate, profit factor, maximum drawdown, average R, and results by setup/session/month.
- Separate development and out-of-sample periods.

Demo-forward requirements:

- Run for at least 30 qualified setups or a predetermined calendar period.
- Record every signal, including rejected setups.
- Compare ticket prices and timestamps with manual MT5 observations.
- Change one strategy version at a time and retain its configuration hash.

Release gate:

- No live-account recommendation until calculation accuracy, operational reliability, and predefined performance criteria all pass.

## 7. Configuration

*Revised 2026-08-11. The nested template originally in this section was never adopted; the
delivered `config/strategy.yaml` is a flat mapping with different key names. Every live key is
documented in `CONFIGURATION.md`. The summary below records only where the plan and the
implementation diverged, so the divergences are not lost.*

| Planned | Delivered | Note |
|---|---|---|
| `risk.basis: LOWER_OF_BALANCE_EQUITY` | risk is a percentage of the lower of balance and equity | Implemented as a fail-safe against unrealized drawdown. |
| `risk.percent_per_trade: 0.5` | `risk_percent_fx: 1.0`, `risk_percent_gold: 2.0` | Per-asset-class risk replaced the single figure. |
| `timeframes.bias: H1` | no higher timeframe is read | **Withdrawn, not outstanding.** The strategy is M15-only by trader instruction; bias is the M15 session close vs midpoint. An H1 input would be an invented rule. See `STRATEGY_SPEC.md` §0.5. |
| `maximum_daily_loss_percent: TBD` | `daily_risk_limit_percent: 2.0` plus `daily_exposure_cap_cash: 20.0` | Resolved; lower of the two binds. |
| `maximum_trades_per_session: 1` | `maximum_trades_per_symbol_session: 1` | Loaded but **never enforced** (finding A13). |
| `filters.maximum_spread_points: TBD` | `range_spread_multiple: 40.0` | Replaced by a range-relative test, gate G4. |
| `filters.minimum_session_range` / `maximum_session_range` | only the G4 relative floor | Absolute bounds still undefined. |
| `filters.maximum_tick_age_seconds: TBD` | `maximum_tick_age_seconds: 300` | Resolved. |
| `filters.news_filter` | absent | **Not implemented**; still undefined. |
| `management.*` | implemented in `engine.analyze` and printed on the ticket | 75 % at the opposite boundary (SWEEP/RANGE) or 4R (TREND), then manual breakeven. |
| `symbol: TBD` | a four-symbol `symbols` map with per-symbol `pip_size` and `trend_min_range` | Expanded from single-symbol to a universe with gate G3. |

Every remaining `TBD` above is an open specification item, tracked in `STRATEGY_SPEC.md` §12.

## 8. Verification Strategy

Use four levels of verification:

1. Unit tests for formulas and decision boundaries.
2. Integration tests against the connected demo terminal using read-only calls.
3. Golden-case tests using saved, anonymized candle fixtures and expected tickets.
4. Manual chart reconciliation in MT5 before accepting each milestone.

Critical test cases include:

- Session crossing UTC midnight.
- Missing or duplicate candles.
- Market closed or stale tick.
- Symbol suffix and different price digits.
- Spread expansion at entry.
- Sweep wick without close-back-inside.
- Both session boundaries touched in one bar.
- Partial boundary beyond or before the 5R target.
- Volume below minimum or above maximum.
- SL rejected by broker stop-distance rules.

## 9. Operational Workflow After Delivery

```text
1. Start MT5 and log in.
2. Run health check.
3. Request analysis after the reference session closes.
4. Review ticket, chart, evidence, and warnings.
5. Visually verify in MT5.
6. Manually place or reject the trade.
7. Request read-only status checks during management.
8. Manually modify or close the position.
9. Record outcome and review journal statistics.
```

## 10. Milestones and Definition of Done

### Milestone A — Reliable analysis foundation

- Phases 0–2 complete.
- Exact session levels independently verified in MT5.

### Milestone B — Complete trade-ticket prototype

- Phases 3–5 complete.
- Deterministic ticket generation with risk and broker checks.

### Milestone C — Operational demo assistant

- Phase 6 complete.
- End-to-end read-only workflow usable during a demo session.

### Milestone D — Validated strategy candidate

- Phase 7 complete.
- Backtest and forward-test reports meet the predeclared release gates.

The project is done only when the system is deterministic, read-only, timestamp-safe, tested against MT5, and capable of producing a fully reconciled ticket or an explicit `NO_TRADE` result without relying on unstated judgment.
