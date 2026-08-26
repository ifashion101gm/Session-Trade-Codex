# CANONICAL_SESSION_CONSUMER_MAP.md

Every file found (via `grep` for session-defining keywords, then import/caller tracing — not
assumed from text matches alone) to hold or reference an Asian/London/New York session boundary,
as of the 2026-08-26 force migration. "Direct" = defines/reads hours itself; "Indirect" = calls
something that does.

| File | Consumer type | Current definition | Canonical? | Active? | Direct/Indirect | Migration required? | Historical? | Execution impact |
|---|---|---|---|---|---|---|---|---|
| `config/canonical_sessions.yaml` | Contract source | Asian 00:00-06:00, London 06:00-11:00, NY 12:00-15:00 | — (is canonical) | Yes | — | — (new) | No | None (data only) |
| `session_clock.py` | Canonical loader/validator | reads above | Yes | Yes | Direct | — (new) | No | None (fails closed only) |
| `smc_3r_v1/canonical_sessions.py` | Shim over `session_clock.py` | reads above | Yes | Yes | Direct | Done | No | None (research, no MT5) |
| `smc_3r_v1/reference_levels.py` | Asian box builder | 00:00-06:00 (via shim) | Yes | Yes | Indirect | Done | No | None (research) |
| `smc_3r_v1/smc_state_machine.py` | London AM + NY AM window | 06:00-11:00, 12:00-15:00 (via shim) | Yes | Yes | Indirect | Done (was 07:00-10:00, fixed) | No | None (research) |
| `session_router/*` (new) | Classifier + reference box + Entry 1/2/3 + router | reads `session_clock.py` via `canonical_session_version` field, symbol-level windows passed by caller | Yes | Yes | Direct (version tag) / caller-supplied windows | Done (new) | No | None — `contract_status` explicitly non-executing |
| `config/strategy.yaml` (`ASIAN_SESSION_V1`) | Live/demo engine config | 00:00-07:00, 28 M15 | No (frozen, documented exception) | Yes (loadable) but **LEGACY_FROZEN, execution authority NONE** | Direct | Done — frozen + execution revoked, not renumbered | Yes (frozen) | Was the only order-submitting path; now `submit_orders: false` |
| `session_strategy/config.py` `_SESSION_CONTRACT_REGISTRY["ASIAN_SESSION_V1"]` | SSOT validator entry | 00:00-07:00, 28, 07:00-16:00, 36 | No (frozen, matches V1 exactly) | Yes | Direct | Done — isolated to a registry entry, V1's assertion byte-identical to before | Yes (frozen) | Fails closed if `strategy.yaml` drifts from this |
| `config/strategy_v2.yaml` (`ASIAN_SESSION_V2`, new) | Research engine config | 00:00-06:00, 24 M15 (canonical) | Yes | Yes (loadable), execution authority NONE | Direct | Done (new) | No | No execution path (`mode: analysis_only`, all permissions false) |
| `session_strategy/config.py` `_SESSION_CONTRACT_REGISTRY["ASIAN_SESSION_V2"]` | SSOT validator entry | 00:00-06:00, 24, 06:00-15:00, 36 | Yes | Yes | Direct | Done (new) | No | Fails closed if `strategy_v2.yaml` drifts from this |
| `session_strategy/engine.py` | Pure-function session-bounds calculator | generic (`config.session_start_utc`/`session_end_utc`, whichever config is loaded) | Yes (parametric) | Yes | Direct (of whatever config is passed) | None needed — never hardcoded an hour | No | Same code path serves both V1 and V2 |
| `config/no_trade_research.yaml` | Backtest-lifecycle overlay | `entry_window_end_utc`/`position_hold_end_utc` — an execution/holding-period filter, **not** a market-session definition | N/A (not a session def) | Yes | Direct (of its own execution-window fields) | None — already correctly scoped, inherits its Asian reference from whichever `session_strategy` config it's run against | No | None by itself |
| `session_strategy/session_contract.py` | Generic dataclass (`start_utc`, `end_utc` fields) | parametric, no hardcoded hours | N/A | Yes | — | None needed | No | None |
| `.claude/skills/session-box-drawing/SKILL.md`, `.agents/` copy | Agent skill | Was generic ("obtain the missing contract"), now explicitly points at `config/canonical_sessions.yaml` / `session_clock.get_session_bounds()` | Yes | Yes | Direct (pointer) | Done | No | None |
| Other `.claude`/`.agents` skills (`sweep-detection-range-v2`, `trend-range-classification`, etc.) | Agent skills | No embedded hours found | N/A | Yes | — | None | No | None |
| `archive/session_configs/session_flow_v2.yaml` | Research contract doc | Asian 00:00-08:00, London 07:00-12:00 | No | **No** (only consumer is its own schema test) | Direct | N/A — archived | Yes | None |
| `archive/session_configs/session_strategy_v2_research.yaml` | Research contract doc | Asian 00:00-07:00, London 07:00-12:00 | No | **No** (zero programmatic consumers) | Direct | N/A — archived | Yes | None |
| `archive/session_configs/source_v2_agent.yaml` | Research contract doc | Asian 00:00-08:00 (Europe/London local) | No | **No** (only consumer is its own schema test) | Direct | N/A — archived | Yes | None |
| `archive/session_configs/source_v1.yaml` + `session_strategy/source_v1.py` (`replay_source_v1.py`) | Historical episode replay | Asian 22:00 (prior day)-07:00 | No — **deliberate exception**, replays one specific published episode by design | Yes (code still runs) but read-only, no order path | Direct (yaml doc) / Direct (hardcoded in .py, matches yaml) | Not migrated — documented exception, see migration report §5 | Yes (yaml archived; .py stays, flagged) | None (`MT5ReadOnlyGateway` only) |
| `archive/session_configs/user_resolved_v2.yaml` + `session_strategy/source_v2.py` (`replay_source_v2.py`, `replay_source_v2_agent.py`) | Historical episode replay | Asian 00:00-08:00, **Europe/London local, DST-following** | No — **deliberate exception**, same reasoning as source_v1, flagged additionally for DST/local-time use | Yes (code still runs) but read-only, no order path | Direct (yaml doc, now archived) / Direct (hardcoded ZoneInfo in .py) | Not migrated — documented exception, see migration report §5 | Yes (yaml archived; .py stays, flagged) | None (no order-submitting path found) |

## Totals

```text
Active session-defining files (excluding archive/):        9   (canonical_sessions.yaml, session_clock.py,
                                                                 smc_3r_v1 x3, session_router x1 (version tag),
                                                                 strategy.yaml, strategy_v2.yaml, config.py registry)
Active files fully canonical:                                7
Active files frozen with documented exception (not renumbered): 2 (strategy.yaml/ASIAN_SESSION_V1 registry entry;
                                                                     source_v1.py/source_v2.py, read-only replay only)
Historical/archived files:                                   5  (archive/session_configs/*.yaml)
Unknown consumers:                                            0  (every row traced by grep + import check)
```

`ACTIVE_LEGACY_SESSION_DEFINITIONS` (files with real execution capability that still assert a
non-canonical window): **0** — `config/strategy.yaml` retains its non-canonical numbers for
historical reproducibility, but its execution authority has been explicitly revoked
(`mode: analysis_only`, `submit_orders/modify_orders/close_positions: false`), so it is no
longer an *active competing session authority* in the sense of §2 ("everything else must consume
canonical or be archived/historical/non-active") — it is frozen, not silently coexisting.
`source_v1.py`/`source_v2.py` have no order-submitting path at all (`MT5ReadOnlyGateway` only),
so neither counts against this total either.
