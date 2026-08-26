# ACTIVE_STRATEGY_ARCHITECTURE.md

How a completed reference session becomes a candidate setup in this repository, as of the
2026-08-26 canonical-session force migration (`CANONICAL_SESSION_MIGRATION_REPORT.md`).

```text
              CANONICAL SESSION SERVICE
         (session_clock.py, config/canonical_sessions.yaml)
                          |
        Asian 00:00-06:00 | London AM 06:00-11:00 | NY AM 12:00-15:00
                          v
              COMPLETED REFERENCE BOX
     (session_router/reference_box.py -- open/high/low/close/
      range/mid/path_length/displacement/ER/bar_count/complete)
                          v
                TREND / RANGE  (session_router/classifier.py, ER_ONLY_V2, threshold 0.40)
               /                        \
           TREND                        RANGE
             |                            |
        Entry 1 (TREND)              Sweep? (Entry 2, strict penetration)
   session_router/setups.py               |
   entry_1_trend                    YES ------- NO
                                      |            |
                                  Entry 2       Entry 3 (RANGE)
                                  SWEEP         boundary rejection
                                                (may be NO_SETUP)
                          |
                    SetupDecision
       (candidate only -- contract_status =
        RESEARCH_CANDIDATE_NOT_EXECUTION_AUTHORITY)
                          v
                  Risk / execution gates
              (NOT implemented by session_router --
               see "What this is not," below)
                          v
                         MT5
```

## Layer boundaries (do not collapse these)

- **MARKET SESSION** — a fixed UTC clock (`config/canonical_sessions.yaml`). Answers only "which
  candles belong to Asian/London AM/New York AM." Never redefined to chase a profitable
  sub-window; never DST- or local-timezone-adjusted.
- **STRATEGY SETUP** — `session_router`'s classifier + Entry 1/2/3. Answers "given a completed
  box, is there a candidate trade." Consumes the market session; never redefines it.
- **EXECUTION WINDOW** — a separate, explicitly-named concept (e.g. `config/strategy.yaml`'s
  `execution_start_utc`/`execution_end_utc`, or a future
  `smc_3r_execution_window`-style filter) for *when this strategy is allowed to act*, distinct
  from what the market session *is*. A narrower research-discovered profitable window belongs
  here, never as a rewrite of the session clock.
- **BROKER EXECUTION** — MT5 order placement. Fully separate from all of the above; nothing in
  `session_router` or `session_clock.py` imports an MT5 gateway.

## What actually runs where today

| Component | Layer | Status |
|---|---|---|
| `session_clock.py` | Market session | Canonical, authoritative for `smc_3r_v1` and `session_router` |
| `smc_3r_v1/*` | Market session (Asian, London AM, NY AM) + SMC-specific setup logic (sweep/displacement/CHoCH/FVG) | Research; consumes `session_clock.py`; `SMC_3R_V1_SPEC.md` |
| `session_router/*` | Strategy setup (classifier + Entry 1/2/3, this doc's diagram) | Research; new in this migration; consumes `session_clock.py` |
| `config/strategy.yaml` (`ASIAN_SESSION_V1`) | Market session (own, trader-confirmed, frozen non-canonical) + setup logic + execution + MT5 | `LEGACY_FROZEN`: `mode: analysis_only`, execution authority explicitly revoked 2026-08-26. Governance signoff already stale independent of this migration. Not deleted — golden fixtures depend on its exact window. |
| `config/strategy_v2.yaml` + `session_strategy/*` (`ASIAN_SESSION_V2`) | Market session (canonical) + same signed setup logic + execution (unused) | Research, canonical `00:00-06:00`, no execution authority (never had one). Shares `session_strategy/engine.py` with V1; `session_strategy/config.py`'s `_SESSION_CONTRACT_REGISTRY` enforces each version's frozen numbers independently. Ledger id `c0765fca04f80794`. |
| `archive/session_configs/*` | Historical market-session definitions | Archived, not consumed by any active decision |

## What this is not

`session_router` is a **candidate-setup generator**, not a trading system. It does not:
- simulate fills, exits, or P&L (no matcher — see migration report §7),
- talk to MT5 or any broker,
- get to authorize an order by existing or by its tests passing.

Producing a `VALID` `SetupDecision` means "the signed rule fired," nothing more.
`READY_FOR_ONE_DEMO_ORDER_SEND` and `READY_FOR_LIVE_ORDER_SEND` are governed entirely by
`config/strategy.yaml`'s own governance block and are unaffected by this document.
