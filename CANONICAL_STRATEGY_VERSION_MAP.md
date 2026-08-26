# CANONICAL_STRATEGY_VERSION_MAP.md

Version identity for every strategy whose meaning materially changes under
`CANONICAL_SESSION_WINDOWS_V1`, per `CANONICAL_SESSION_MIGRATION_REPORT.md`'s versioning
principle: a strategy calibrated against an old session window is never silently renumbered onto
the new one — it's frozen, and (where a successor was created) a new version consumes canonical
timing from a clean box.

## ASIAN_SESSION_V1 → ASIAN_SESSION_V2

```text
ASIAN_SESSION_V1                          ASIAN_SESSION_V2
config/strategy.yaml                      config/strategy_v2.yaml
status = LEGACY_FROZEN                    status = RESEARCH
session = 00:00-07:00 UTC, 28 M15         session = 00:00-06:00 UTC, 24 M15 (CANONICAL_SESSION_WINDOWS_V1)
execution window = 07:00-16:00            execution window = 06:00-15:00 (same 9h duration, re-anchored to new close)
execution authority = NONE (revoked       execution authority = NONE (never granted)
  2026-08-26: mode analysis_only,
  submit_orders/modify_orders/
  close_positions = false)
governance = APPROVED_FOR_STAGE_2_        governance = RESEARCH_DRAFT_PENDING_VALIDATION
  BASELINE (signoff already stale,
  hash drift predates this migration)
predecessor = SESSION_SOURCE_V1           predecessor = ASIAN_SESSION_V1
                                           canonical_session_version = CANONICAL_SESSION_WINDOWS_V1
```

**Reason for the split**: `strategy.yaml`'s `00:00-07:00` window is the trader's own
MT5-chart-confirmed truth source for 2022-10-03 (exhaustive-search calibration, 2026-08-15
correction note); golden fixtures and `benchmarks/truth_source_setups.json` depend on it. There
is no equivalent trader-confirmed truth for a `00:00-06:00` window. Rewriting V1's numbers in
place would either (a) silently invalidate that calibration, or (b) require fabricating a new
"confirmed truth" this repo has not actually verified — both unacceptable. V2 instead starts
clean: same signed setup rules (`BOX_DIRECTION_V1`, strict-penetration sweep, boundary-rejection
range — see `ACTIVE_STRATEGY_ARCHITECTURE.md`), same risk/cost/symbol parameters (not
session-dependent, copied verbatim), but every session-derived quantity (range, mid, bias, stop,
target) is computed fresh from the canonical box. `governance.specification_status` is honestly
`RESEARCH_DRAFT_PENDING_VALIDATION`, not copied from V1's (already-stale) approval — V2 has never
been reviewed.

Both configs share the same engine code (`session_strategy/config.py`, `engine.py`) — see
`session_strategy/config.py`'s `_SESSION_CONTRACT_REGISTRY`, which enforces each version's frozen
numbers independently (V1's assertion is byte-identical to what it was before this migration).

**Not done**: recalibrating `symbols.*.minimum_range`/`maximum_range` for V2's narrower 6-hour
window. These are a statistical gate on plausible Asian-range width, already listed under both
configs' `governance.provisional_parameters` (`symbol_range_limits`) as an acknowledged open gap
— copied from V1 unchanged rather than guessed. Recalibrating them properly needs a real
distributional study against the canonical window (V2's own `promotion_requirements`), which is
research, not a session-timing edit.

## SMC_3R_V1 — no successor needed

`smc_3r_v1` already used `Asian [00:00, 06:00)` before this migration began (see
`SMC_3R_V1_SPEC.md`). Its only divergence was London AM (`07:00-10:00` instead of canonical
`06:00-11:00`), fixed by consuming `session_clock.py` directly — see
`CANONICAL_SESSION_MIGRATION_REPORT.md` §1 and `LONDON_CANONICAL_DELTA_REPORT.md` for what that
fix changes. This is a genuine in-place fix, not a version fork: the London window was simply
wrong (contradicted the trader-supplied reference table with no prior signed alternative
justifying `07:00-10:00`), not a case of an already-calibrated strategy losing its calibration.
`SMC_3R_V1` remains `SMC_3R_V1` — status `research`, unchanged identity, `smc_3r_v1/matcher.py`'s
fill simulation and all other SMC-specific logic (sweep/displacement/CHoCH/FVG) untouched.

## SESSION_FLOW_V2_SIMPLE, SESSION_STRATEGY_V2_RESEARCH, SESSION_SOURCE_V1, SESSION_USER_RESOLVED_V2(_AGENT)

Archived, not versioned forward. None of these had a real (order-submitting or even
signal-generating-and-consumed) active runtime path — see `CANONICAL_SESSION_CONSUMER_MAP.md`.
`SESSION_SOURCE_V1` and `SESSION_USER_RESOLVED_V2` specifically replay one fixed historical
episode each; forcing them onto canonical timing would corrupt what they're reproducing, not
"upgrade" them (`CANONICAL_SESSION_MIGRATION_REPORT.md` §5). If a canonical-session-based
replacement for what these were researching is wanted later, that is new strategy work, not a
rename of these files.

## R8_OBM_V1, ST04_07_EXECUTION_ATTRIBUTION_V1

Not session-box strategies (order-block model / fill-attribution study respectively — see
`R8_OBM_V1_SPEC.md`) — no Asian/London/NY window dependency found; out of scope for this
migration entirely, not touched.
