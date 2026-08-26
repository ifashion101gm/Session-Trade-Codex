# ASIAN_SESSION_V2 — Specification (as-implemented)

**Status: research. Not authorized for demo or live execution — `config/strategy_v2.yaml`
`mode: analysis_only`, all `execution_permissions` false, no `parameter_signoff`.**

Canonical-session successor to `ASIAN_SESSION_V1` (`config/strategy.yaml`, now `LEGACY_FROZEN`).
See `CANONICAL_SESSION_MIGRATION_REPORT.md` and `CANONICAL_STRATEGY_VERSION_MAP.md` for why the
split exists rather than editing V1 in place.

## What changed from V1

- Reference session: `[00:00, 06:00)` UTC / 24 M15 candles — `CANONICAL_SESSION_WINDOWS_V1`
  (`config/canonical_sessions.yaml`), not V1's trader-confirmed-but-non-canonical
  `[00:00, 07:00)` / 28.
- Execution window: `[06:00, 15:00)` UTC / 36 M15 candles — same 9-hour duration as V1's
  `sweep_window_hours: 9`, re-anchored to this session's own close (06:00) instead of V1's
  absolute clock time (07:00).
- `governance.specification_status`: `RESEARCH_DRAFT_PENDING_VALIDATION`, not V1's (already
  stale) `APPROVED_FOR_STAGE_2_BASELINE` — this config has never been reviewed.

## What did not change

Every signed setup/risk/cost rule is copied from V1 verbatim (not session-dependent, so
mathematically compatible per the migration report's versioning principle):
classification (`efficiency_ratio_threshold: 0.35`, `close_location_trend: 0.65`), setup
priority (`SWEEP > RANGE_REJECTION > TREND_CONTINUATION`), `fixed_stop_policy`
(`stop_range_fraction: 0.25`, `distance_source: ASIAN_RANGE`), `management` (partial 75% @ 4R,
runner to 5R), `cost_model`, `risk` (0.5%/trade, 2%/day). All of these are evaluated against the
*new* box (V2's own high/low/range/mid), not reused from V1's historical levels — there is no
code path that could reuse them, since both versions run the same stateless `session_strategy`
engine (`session_bounds()`/`analyze()`) parameterized purely by whichever config is loaded.

`symbols.*.minimum_range`/`maximum_range` are copied from V1 **unrecalibrated** — flagged as an
open, acknowledged gap (`governance.provisional_parameters`), not silently inherited. See
`CANONICAL_STRATEGY_VERSION_MAP.md`.

## Implementation

Shares `session_strategy/config.py`, `session_strategy/engine.py`, `session_strategy/models.py`
with V1. The only V2-specific code is `session_strategy/config.py`'s
`_SESSION_CONTRACT_REGISTRY["ASIAN_SESSION_V2"]` entry, which enforces V2's own frozen numbers
(`00:00-06:00`/24/`06:00-15:00`/36) independently of V1's entry.

## What this spec does NOT establish

- No backtest result, hypothesis count, or promotion has been run — this is a Stage-0
  registration, same as `SMC_3R_V1_SPEC.md` was.
- No re-derivation of `symbols.*` range gates against the new 6-hour window.
- No MT5 execution integration; `mode: analysis_only` and all `execution_permissions` are false.

See `STRATEGY_LEDGER.md` for the registration entry.
