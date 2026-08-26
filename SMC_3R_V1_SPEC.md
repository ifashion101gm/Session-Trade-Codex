# SMC_3R_V1 — Specification (as-implemented)

**Status: research. Not authorized for demo or live execution. No MT5 wiring exists.**

This spec documents the rules exactly as coded in `smc_3r_v1/` — it was written from an
externally-authored, complete implementation supplied to this repository on 2026-08-26, not
derived from a trader's source document the way `SESSION_FLOW_V1`/`ASIAN_SESSION_V1` were. There
is no independent narrative source to conform this against yet; treat every rule below as "what
the code does," not "what was intended."

## Data / timeframes

- M5 bars for signal detection, M1 bars for fill/exit simulation (`smc_3r_v1/matcher.py`).
- Session windows (Asian reference, London AM, New York AM) are read from
  `config/canonical_sessions.yaml` (`CANONICAL_SESSION_WINDOWS_V1`) via
  `smc_3r_v1/canonical_sessions.py`, not hardcoded in this package. As of 2026-08-26 that file
  defines, in UTC, half-open `[start, end)`:
  - Asian reference: `[00:00, 06:00)` — requires exactly 72 M5 bars (24 M15 bars × 3) or the
    level is `None` for that day (`reference_levels.compute_reference_levels`).
  - London AM: `[06:00, 11:00)`
  - New York AM: `[12:00, 15:00)`

  **Correction, 2026-08-26**: London AM was originally hardcoded here as `07:00–10:00` UTC,
  which conflicted with the trader-supplied canonical session table (`06:00–11:00`). Fixed as
  part of canonical-session reconciliation — see `config/canonical_sessions.yaml` and
  `STRATEGY_LEDGER.md`. Other strategies in this repo (`ASIAN_SESSION_V1`, `SESSION_FLOW_V2_SIMPLE`,
  `SESSION_STRATEGY_V2_RESEARCH`, `SESSION_SOURCE_V1`) still use their own, different session
  windows and were intentionally left unchanged to preserve reproducibility of past backtests —
  see `legacy_session_windows` in `config/canonical_sessions.yaml`.
- Prior Trading Day (PDH/PDL): most recent prior calendar date with ≥95% of 288 expected M5 bars,
  found by walking backward.
- Session windows strategy will evaluate in: London AM and New York AM (`SMCStateMachine.
  is_in_session_window`). State resets to `SEARCH_SWEEP` outside these windows.

## State machine (`smc_3r_v1/smc_state_machine.py`)

`SEARCH_SWEEP → WAIT_DISPLACEMENT_CHOCH → WAIT_IMMEDIATE_FVG → (order or reset)`

1. **Sweep**: a bar's low breaks below Asian Low or PDL and closes back above it (BUY setup), or
   high breaks above Asian High/PDH and closes back below it (SELL setup).
2. **Displacement + CHoCH**, within `max_sweep_bars=8` M5 bars of the sweep: a bar with
   body ≥ 1.5× the 20-bar median body and body/range ≥ 0.60, whose close breaks the last
   *causally confirmed* 3-bar fractal swing in the trade direction.
3. **Immediate FVG**: the bar immediately following displacement (C3) must leave a gap versus the
   pre-displacement bar (C1) — `c3_low > c1_high` for BUY, `c3_high < c1_low` for SELL. No FVG on
   that exact next bar → setup is abandoned, not retried later.
4. **Order geometry**: limit entry at the FVG edge, stop beyond the sweep extreme by a
   2-pip buffer, target at fixed `3R` (`tp_r=3.0`). Order activates 5 minutes after the FVG bar's
   timestamp and expires 25 minutes after activation (5 M1... note: comment says "5 M5 bars" but
   the code uses `pd.Timedelta(minutes=25)` measured in M1 terms during matching — flagged as a
   documentation inconsistency in the source, not fixed here).

## Fill/exit simulation (`smc_3r_v1/matcher.py`)

- Resting limit order filled on M1 bars within `[activation, expiry)`; BUY fills when
  `low + spread <= limit`, SELL fills when `high >= limit`.
- Any gap in M1 continuity (missing minute) at or after activation is reported as `DATA_GAP`, not
  silently skipped.
- Both SL and TP touched in the same M1 bar → recorded as a loss (`intrabar_ambiguity=True`),
  a conservative (not proven) tie-break.
- Forced exit at `21:55` UTC daily cutoff if neither SL nor TP has been hit.
- Fixed 1-pip simulated spread (`spread_pips=1.0` default), applied on the SELL side's exit only
  per the code as given — not re-derived here.

## What this spec does NOT establish

- No backtest result, hypothesis count, or promotion has been run. Zero hypotheses registered.
- No parameter (`sl_buffer_pips`, `tp_r`, session windows, displacement thresholds) has been
  validated against data in this repo — they are the values shipped in the supplied code.
- No MT5 execution integration exists; this is signal/backtest logic only, structurally similar
  to `ST04_07_EXECUTION_ATTRIBUTION_V1` in that no order-sending path is present.
- The promised test suite (`tests/test_smc_3r_v1_complete.py`) was referenced but not supplied
  alongside the modules — it does not exist in this repository as of registration and no claim of
  "tests pass" can be made.

See `STRATEGY_LEDGER.md` for the registration entry.
