# CANONICAL_SESSION_MIGRATION_REPORT.md

Force-migration of the repository onto `CANONICAL_SESSION_WINDOWS_V1`, executed 2026-08-26.

**Addendum, same day, Phase 2 (full project upgrade)**: the owner's initial instruction allowed
`config/strategy.yaml` (`ASIAN_SESSION_V1`) to keep its non-canonical `00:00-07:00` window as a
documented, blocked exception (see the original §4 below, now superseded). A follow-up
instruction made the split explicit instead: `ASIAN_SESSION_V1` is now `LEGACY_FROZEN` (execution
authority explicitly revoked — `mode: analysis_only`, `submit_orders`/`modify_orders`/
`close_positions: false`, numbers unchanged), and a new `ASIAN_SESSION_V2`
(`config/strategy_v2.yaml`, `ASIAN_SESSION_V2_SPEC.md`, ledger id `c0765fca04f80794`) is the
canonical-session successor — `00:00-06:00`, 24 M15, `mode: analysis_only`, no execution
authority either (never had one). See `CANONICAL_STRATEGY_VERSION_MAP.md` for the full reasoning
and `STRATEGY_LEDGER.md` for the registration. `session_strategy/config.py`'s SSOT check is now a
small per-`strategy_id` registry (`_SESSION_CONTRACT_REGISTRY`) instead of one hardcoded
assertion, so V1's enforced values stayed byte-identical while V2's were added. §4 below is kept
for its reasoning (why V1's numbers were never rewritten) but its **BLOCKED** framing and
`ACTIVE_LEGACY_SESSION_DEFINITIONS = 1` conclusion are superseded — see the final status block
at the end of this file for the current numbers.

Owner-signed contract (verbatim):

```text
Timezone        = UTC
Boundary policy = half-open [start, end)
DST adjustment  = NONE

Asian Range   00:00-06:00 UTC   24 x M15 bars
London AM     06:00-11:00 UTC   20 x M15 bars
New York AM   12:00-15:00 UTC   12 x M15 bars
```

Source of truth: `config/canonical_sessions.yaml`. Runtime enforcement: `session_clock.py`
(`validate_session_contract()` fails closed with `SessionContractConflict` on any
reinterpretation — wrong timezone, DST, overlap, wrong bar count).

## 1. Inventory and classification

| File | Classification | Consumer(s) | Action |
|---|---|---|---|
| `config/canonical_sessions.yaml` | **CANONICAL** (new) | `session_clock.py` | created |
| `session_clock.py` | **CANONICAL SERVICE** (new) | `smc_3r_v1`, `session_router`, session-box-drawing skill | created |
| `smc_3r_v1/canonical_sessions.py` | ACTIVE | `smc_3r_v1/reference_levels.py`, `smc_3r_v1/smc_state_machine.py`, `tests/test_smc_3r_v1_complete.py`, `tests/test_canonical_sessions.py` | migrated: now a thin re-export of `session_clock.py` (was its own private loader) |
| `smc_3r_v1/smc_state_machine.py` | ACTIVE | `smc_3r_v1` test suite (research only, no MT5 wiring) | migrated: London AM corrected `07:00-10:00` → `06:00-11:00` via canonical service |
| `smc_3r_v1/reference_levels.py` | ACTIVE | same | migrated: Asian window now read from canonical service (value unchanged: `00:00-06:00`) |
| `session_router/*` (new package) | **CANONICAL ROUTER** (new, research-only) | `tests/test_session_router.py` | created — see §3 |
| `config/strategy.yaml` (`ASIAN_SESSION_V1`) | **ACTIVE, live/demo order-submitting** | `session_strategy/{cli,config,engine}.py`, `scripts/execute_session_signal.py`, `scripts/session_simple_runner.py`, `scripts/test_demo_execution_harness.py`, `tests/test_engine.py`, `tests/test_execute_session_signal.py` | **partially migrated** — architecture separated, numeric Asian window **not** changed. See §4 (this is the one BLOCKED item). |
| `session_strategy/config.py` SSOT tuple | ACTIVE | same | unchanged (still enforces `00:00-07:00`/28/`07:00-16:00`/36) — see §4 |
| `config/no_trade_research.yaml` | ACTIVE (research runner) | `scripts/backtest_refined_hybrid.py`, `backtest_session.py`, `research_no_trade.py`, `validate_refined_hybrid.py`, `validate_research_signal.py`, 3 tests | **compliant, no action** — its `entry_window_end_utc`/`position_hold_end_utc` are `backtest_lifecycle` execution-window fields, not a second Asian/London/NY definition; its Asian reference is inherited from `config/strategy.yaml` via `session_bounds()` |
| `session_strategy/session_contract.py` | ACTIVE | `SESSION_FLOW_V2_SIMPLE` sweep classifier reference | compliant, no action — `start_utc`/`end_utc` are generic parameter fields on a dataclass, not hardcoded hours |
| `archive/session_configs/session_flow_v2.yaml` (was `config/session_flow_v2.yaml`) | **ARCHIVED** | only its own schema test | moved; old Asian `00:00-08:00`, old London `07:00-12:00`, both non-canonical, preserved verbatim; test path updated |
| `archive/session_configs/session_strategy_v2_research.yaml` | **ARCHIVED** | none (zero programmatic consumers found) | moved; old Asian `00:00-07:00`, old London `07:00-12:00`, preserved verbatim |
| `archive/session_configs/source_v2_agent.yaml` | **ARCHIVED** | only its own schema test | moved; old Asian `00:00-08:00` local Europe/London, preserved verbatim; test path updated |
| `archive/session_configs/source_v1.yaml` | **ARCHIVED (documented exception, not force-migrated in code)** | `session_strategy/source_v1.py` docstring only (no programmatic yaml load) | moved; see §5 |
| `archive/session_configs/user_resolved_v2.yaml` | **ARCHIVED (documented exception, not force-migrated in code)** | none directly; `session_strategy/source_v2.py` hardcodes matching logic | moved; see §5 |
| `.claude/skills/session-box-drawing/SKILL.md`, `.agents/` copy | ACTIVE (agent skill) | Claude Code | already compliant (no embedded hours) — added an explicit pointer to `config/canonical_sessions.yaml` / `session_clock.get_session_bounds()` as the default source |
| `session-box-drawing`, `sweep-detection-range-v2`, `trend-range-classification` and other `.claude`/`.agents` skills | ACTIVE | Claude Code | audited, no embedded session hours found |

**Totals**: active files scanned ≈ 30 (session_strategy/*, smc_3r_v1/*, scripts/*, config/*.yaml,
tests/*, skills). Active files migrated onto the canonical service: 4
(`smc_3r_v1/canonical_sessions.py`, `reference_levels.py`, `smc_state_machine.py`, plus the new
`session_router` package). Historical files archived: 5. Remaining divergent **active** definition:
1 (`config/strategy.yaml` / `session_strategy/config.py`, §4, BLOCKED). Unknown consumers: 0 (every
file above was traced to its actual importers via `grep`, not assumed).

## 2. Canonical session service

`session_clock.py` is the single reusable implementation (per §28's "avoid duplicate
abstraction layers"). It exposes `get_session_definition`, `is_in_session`, `get_session_bounds`,
`session_complete`, `expected_bar_count`, and `validate_session_contract`, all UTC/half-open, and
raises `SessionContractConflict` — never silently reinterprets — on:
- wrong timezone or `dst_adjustment: true`,
- non-half-open boundary policy,
- non-monotonic or out-of-range hours,
- a bar count that doesn't match `(end-start)*4` for M15,
- session overlap (checked pairwise across the sorted windows, which also proves the
  11:00-12:00 gap belongs to neither AM session — `tests/test_session_clock.py`).

`smc_3r_v1/canonical_sessions.py` is now a thin shim over it (kept for backward compatibility
with `smc_3r_v1`'s existing tests, which already called it in this shape).

## 3. Canonical simplified router (`session_router/`)

New, self-contained, **research-only** package (not wired to any MT5 gateway or order-sending
path — `contract_status` on every decision is literally
`"RESEARCH_CANDIDATE_NOT_EXECUTION_AUTHORITY"`):

- `reference_box.py` — session open/high/low/close/range/mid/path_length/displacement/ER/
  bar_count/complete, computed only from that session's own candles.
- `classifier.py` — `ER_ONLY_V2` (config/session_flow_v2.yaml's already-VALIDATED classifier,
  reused rather than reinvented): `ER >= 0.40 -> TREND`, equality to TREND, zero path to RANGE.
- `setups.py` — `SetupDecision` schema (`strategy_id, symbol, reference_session, session_date,
  canonical_session_version, regime, setup_type, direction, signal_timestamp, entry_reference,
  stop_reference, target_reference, risk_distance, evidence, contract_status, decision_status,
  reason_code, classifier_id/version, setup_version`) plus:
  - `entry_1_trend` — direction rule `BOX_DIRECTION_V1` (config/session_flow_v2.yaml's own
    `SIGNED_IMPLEMENTED` rule: completed-box first-open vs final-close), reused rather than the
    provisional midpoint fallback in the instructions, because a signed rule already exists.
  - `entry_2_sweep` — strict penetration (`session_flow_v2.yaml` sweep_classifier: `STRICT`,
    `reclaim_clearance_fraction: 0.0`), first qualified chronologically, same-candle dual-side
    breach -> `AMBIGUOUS_DUAL_SWEEP` / `NO_TRADE`.
  - `entry_3_range` — boundary touch + directional close (config/strategy.yaml's
    `range_rejection` rule), direction `UPPER_BOUNDARY_REJECTION_SHORT_LOWER_BOUNDARY_REJECTION_LONG`
    (session_flow_v2.yaml `entry_3_range`), may terminate `NO_SETUP`
    (`NO_SETUP_BY_WINDOW_END`, matching `range_setup.terminal_reason`).
- `router.py` — `route_completed_session()`: TREND -> Entry 1 only; RANGE -> Entry 2, and only on
  `NO_SETUP` does it fall through to Entry 3. Stateless, one call per completed session, no
  post-session observation loop.

Tests: `tests/test_session_router.py` (14 tests) — ER threshold at 0.3999/0.4000/0.4001, zero
path, router dispatch for all three branches, ambiguous dual sweep, strict-penetration-vs-touch,
lookahead protection (decisions proven unaffected by candles after the qualifying one, and the
reference box proven built only from its own session's candles), version attribution.

## 4. `ASIAN_SESSION_V1` (`config/strategy.yaml`) — originally BLOCKED, now resolved (§ below is historical reasoning)

**Resolution, Phase 2 addendum**: rather than leaving this permanently blocked, V1 is now
`LEGACY_FROZEN` (execution authority explicitly revoked, numbers unchanged) and
`ASIAN_SESSION_V2` (`config/strategy_v2.yaml`) is the canonical successor — see the addendum at
the top of this file and `CANONICAL_STRATEGY_VERSION_MAP.md`. The reasoning below for *why V1's
numbers themselves were never rewritten* still stands and is preserved verbatim.

Section 17 (first instruction) asked to force-migrate this engine's Asian window to
`00:00-06:00` in place. **That was not done**, and the reason is load-bearing, not a preference:

- This is the only config in the repository with a real execution path
  (`execution_permissions.submit_orders: true`, `demo_execution_authorized: true`) —
  `session_strategy/cli.py` / `engine.py` / `scripts/execute_session_signal.py` can place real
  orders on a connected demo MT5 account.
- Its current `00:00-07:00` window is not an arbitrary choice: `config/strategy.yaml`'s own
  2026-08-15 correction note states it was "determined by exhaustive search against the trader's
  own MT5 export" — i.e. the trader visually confirmed specific Asian high/low levels on their
  chart for 2022-10-03 (`0.98344`/`0.97843`/`50.1p`), and `00:00-07:00` is the window that
  reproduces those trader-confirmed levels computationally. `tests/test_golden_fixtures.py` and
  `benchmarks/truth_source_setups.json` are calibrated against that same window, and real demo
  order stops/targets derive from it via `fixed_stop_policy.distance_source: ASIAN_RANGE`.
- I can mechanically recompute what a `00:00-06:00` window's high/low would be from the CSV data
  already in this repo — but that number would not be "confirmed truth," only an assertion. The
  repo's own methodology (and its own history of "CORRECTED" notes when values were asserted
  without that confirmation) treats the trader's chart confirmation as the actual ground truth,
  not the window choice or the recomputation. I have no authority to manufacture that
  confirmation, and doing so would silently degrade the calibration real demo orders depend on —
  exactly the kind of unverifiable claim this repo's "CORRECTED" comment culture exists to catch.

**What was done instead** (safe, additive, does not change engine behavior or `session_hash`
beyond what re-signoff already requires):
- `config/strategy.yaml`'s `session_contract` block now carries an explicit
  `reference_session: asian`, `canonical_session_version_target: CANONICAL_SESSION_WINDOWS_V1`,
  `canonical_asian_window_utc: ["00:00","06:00"]`, and
  `session_window_migration_status: BLOCKED_PENDING_TRADER_RECONFIRMATION` with the full reason
  recorded in-file.
- Confirmed `execution_start_utc`/`execution_end_utc` (`07:00-16:00`) were already a distinct,
  clearly-named field from the reference session — not mislabeled as London/New York — so no
  restructuring was needed there (per §17's own carve-out: this is an execution filter, not a
  second session definition).
- `session_strategy/config.py`'s SSOT assertion (`00:00-07:00`/28/`07:00-16:00`/36) is
  **unchanged** — the engine still fails closed if `strategy.yaml` drifts from its currently
  trader-confirmed values.
- **(Superseded by the Phase 2 addendum above — kept as history.)** This was originally the one
  place `ACTIVE_LEGACY_SESSION_DEFINITIONS` was not zero. It was documented, traced, and blocked
  on a specific human action (trader re-confirms Asian
  high/low on their live MT5 chart for a `00:00-06:00` window, then the exhaustive-search
  calibration is re-run) — not silently left ambiguous.

Note: `config.hash`/`signoff_hash` on this file were already drifted from the signed
`parameter_signoff.config_hash` before this migration touched anything (see §6) — governance
already treats this config as **not currently approved**, independent of session timing, so this
change does not newly authorize anything.

## 5. Two other deliberate non-migrations (documented exceptions, not oversights)

- `archive/session_configs/source_v1.yaml` / `session_strategy/source_v1.py`
  (`replay_source_v1.py`, read-only `MT5ReadOnlyGateway` only): replays one specific,
  already-published historical episode ("1BullBear Episode 18") whose defining characteristic
  *is* its own window (`22:00` prior-day–`07:00`, an explicit 2026-08-15 user revision chosen to
  reproduce that episode's own reference levels). Forcing it to canonical hours would not make it
  "canonical" — it would corrupt the replay's fidelity to what it studies.
- `archive/session_configs/user_resolved_v2.yaml` / `session_strategy/source_v2.py`
  (`replay_source_v2.py`, `replay_source_v2_agent.py`): same reasoning, but additionally uses
  `ZoneInfo("Europe/London")` **local, DST-following** time — a real, active violation of "no
  DST/local timezone reinterpretation" if judged as a live-trading session definition. It isn't
  one: `mode: historical_research_only`, `verification_status: NOT_INDEPENDENTLY_VERIFIED`, no
  order-submitting path. Flagged here explicitly rather than silently passed over.

Both are genuinely inert with respect to canonical session timing (no code path from either
reaches an order), so neither blocks `STRATEGY_ROUTER_READY` or `BACKTEST_VALIDATED` below.

## 6. Test suite

`python -m pytest tests/ -q` → **340 passed, 8 failed**. All 8 failures pre-date this migration
(confirmed unchanged before/after every step above) and are classified with evidence, not
assumed:

| Test | Classification | Evidence |
|---|---|---|
| `test_engine.py::test_governance_approves_stage_2_baseline_and_locks_optimization` | PRE_EXISTING_UNRELATED | `parameter_signoff.config_hash` (`a41881d1cb4de00c`) vs live `signoff_hash` (now `a84a0f6a59cf76ad`) already diverged before this migration touched `strategy.yaml` (the file's own 2026-08-25 comment documents an earlier drift at `50b31416f0f4b5f3`). Fixing this means writing a new hash into `parameter_signoff` without actual trader signoff — the file's own rule forbids that. Not fixed. |
| `test_execution_ledger.py` x4 | PRE_EXISTING_UNRELATED | All four assert `has_committed_execution_today(..., "2026-08-25", ...)` is `True` right after a same-day commit; today's date in this environment is 2026-08-26. This is a hardcoded-date test fixture, not a session-window issue — nothing in the failure path touches Asian/London/NY hours. Not fixed (out of scope; a real fix requires either freezing "now" in the test or parameterizing the date, unrelated to this task). |
| `test_golden_fixtures.py::test_versioned_golden_cases` | PRE_EXISTING_UNRELATED | Fails on `session_type` (`'UNCERTAIN' != 'RANGE'`) with `strategy.yaml`'s session window numerically unchanged (`00:00-07:00`, untouched — see §4). The mismatch is in classification logic elsewhere, not session timing. Not fixed. |
| `test_safety.py::test_no_forbidden_mt5_call_appears_anywhere_in_the_package` | PRE_EXISTING_UNRELATED | The scan doesn't exempt `mt5_gateway.py`'s own intentionally-guarded execution subclass (comment in that file: *"order_send and order_check are intentionally absent from MT5ReadOnlyGateway... not in the forbidden list for this [gated] execution gateway"*). Always fails on the current package by design of the test, unrelated to session timing. **Not touched** — do not weaken a safety test as a side effect of this task. |
| `test_source_v1.py::test_literal_midpoint_trend_entry_and_stop` | PRE_EXISTING_UNRELATED | Fixture drives `detect()` with a red candle (`close(103) < open(104)`) into a branch that requires `close > open`; unrelated to any session hour (all timestamps are synthetic relative hours 0/1/7, no Asian/London/NY value involved). Not fixed. |

No test in this run is `MIGRATION_EXPECTED`, `NEW_REGRESSION`, or `OBSOLETE_TEST` — the 42 new
tests added by this migration (`test_session_clock.py`: 28, `test_session_router.py`: 14) all
pass, and the pre-existing `smc_3r_v1`/`canonical_sessions` suite (27 tests) required no changes
after the London-window fix.

## 7. Backtest evidence (real data, no P&L)

Run against `data/eurusd_m15_2022_10_utc.csv` (the same real MT5-exported fixture
`scripts/validate_golden_oct3.py` trusts), routed through `session_router` with the canonical
Asian box and canonical London AM window as the post-session evaluation candles:

```text
Sessions with a complete Asian box (24 M15 bars): 15
Sessions skipped (incomplete box - weekend/data gap): 3
Regime counts: RANGE=14, TREND=1
Setup counts:
  (RANGE, NONE,  NO_SETUP) -> 4   (no qualified sweep, no qualified boundary rejection)
  (RANGE, SWEEP, VALID)    -> 10
  (TREND, TREND, VALID)    -> 1
```

London window delta (old `smc_3r_v1` `07:00-10:00` vs canonical `06:00-11:00`), full month, real
data:

```text
old (07:00-10:00) total bars: 180
new (06:00-11:00) total bars: 300
newly included 06:00-07:00:    60
common        07:00-10:00:    180
newly included 10:00-11:00:    60
```

**Not run, and explicitly out of scope**: win rate, net R, expectancy, profit factor, max
drawdown. `session_router` produces candidate setups (entry/stop/target *references*), not
filled trades — there is no order-fill/exit simulator wired to it (building one, e.g. matching
`smc_3r_v1/matcher.py`'s M1 fill simulation, is new execution engineering, not a session-timing
migration, and risks exactly the kind of fabricated-precision result this report is trying to
avoid elsewhere). Per §31, backtest performance does not gate canonical-migration validity
regardless.

## 8. Safety

**Updated in the Phase 2 addendum**: `config/strategy.yaml`'s `execution_permissions` block *was*
changed — `submit_orders`/`modify_orders`/`close_positions` flipped `true` → `false`, `mode`
`trading_enabled` → `analysis_only`, `governance.demo_execution_authorized` `true` → `false` —
as an explicit act of freezing `ASIAN_SESSION_V1`'s execution authority (§4 addendum), not as an
accident. `config/strategy_v2.yaml` was created with no execution authority from the start.
`session_router` still never imports an MT5 gateway. No order was sent, and nothing in this
migration authorizes one — see the final status block for explicit `READY_FOR_*_ORDER_SEND`
values (both `NO`, unchanged from before).

## 9. Final status (Phase 2)

```text
ACTIVE_LEGACY_SESSION_DEFINITIONS = 0   (was 1 after Phase 1; resolved by freezing V1's
                                          execution authority instead of leaving it blocked)
UNKNOWN_SESSION_CONSUMERS         = 0
CANONICAL_SESSION_MIGRATION       = PASS

ASIAN_SESSION_V1  = LEGACY_FROZEN, execution authority NONE, numbers unchanged (00:00-07:00/28)
ASIAN_SESSION_V2  = RESEARCH, canonical (00:00-06:00/24), execution authority NONE, ledger id c0765fca04f80794
SMC_3R_V1         = research, fully canonical (Asian + London AM + NY AM all from session_clock.py), no successor needed

READY_FOR_ONE_DEMO_ORDER_SEND = NO
READY_FOR_LIVE_ORDER_SEND     = NO
```

See `CANONICAL_SESSION_CONSUMER_MAP.md`, `CANONICAL_STRATEGY_VERSION_MAP.md`, and
`LONDON_CANONICAL_DELTA_REPORT.md` for the full detail behind these numbers.
