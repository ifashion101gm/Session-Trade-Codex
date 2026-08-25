# Project status — 25 August 2026

```
CURRENT_MILESTONE:  DEMO_EXECUTION_INFRASTRUCTURE_VALIDATED_V1
STRATEGY:           SESSION_SIMPLE_V1 (FROZEN)

SESSION_SIMPLE_V1
────────────────────────────────────
Strategy rules              FROZEN
Setup routing                FROZEN
Direction / entry / SL      FROZEN
TP = fixed 5R (tp2_5r)      FROZEN
Risk = 0.5%                 FROZEN
Max trades = 1              FROZEN
Management = NONE           FROZEN

DEMO EXECUTION INFRASTRUCTURE
────────────────────────────────────
Signal → Intent             PASS
Risk sizing                 PASS
Request construction        PASS
Duplicate ledger gate       PASS
DEMO account hard gate      PASS
order_check                 PASS
order_send                  PASS
Pending-order confirmation  PASS
SL reconciliation           PASS
TP reconciliation           PASS

STRATEGY END-TO-END
────────────────────────────────────
Genuine natural signal              NOT YET PROVEN
Natural order lifecycle             NOT YET PROVEN
Natural fill/exit reconciliation    NOT YET PROVEN

FORWARD_TEST_INFRASTRUCTURE_READY = YES
NATURAL_SIGNAL_E2E_VALIDATED      = NO
LIVE_READY                        = NO

NEXT_EXECUTION_MILESTONE: ONE_GENUINE_DEMO_SIGNAL_E2E (Phase C — occurs naturally on
the next real signal; does not block other work, see SessionBoxes_V1 below)

TESTS: 260 passed, 4 known documented failures (KNOWN_TEST_FAILURES.md), 0 new regressions

Frozen execution controls (do not weaken before Phase C):
  DEMO only · ALLOW_ORDER_SUBMISSION gate · ALLOW_ONE_DEMO_ORDER gate · explicit --confirm
  · order_check before send · persistent ledger duplicate check · one real send per
  authorized run · LIVE blocked

Known accepted limitation: the persistent execution ledger is the durable authority: the
check (execution_already_committed) and the write (mark_send_requested) are not yet atomic
across simultaneous independent processes. Accepted for controlled single-process DEMO
forward testing; must be solved before multi-process or LIVE execution. Not fixed now —
not a reason to touch the proven send path before the first natural signal.

Do not modify SESSION_SIMPLE_V1 or the execution layer again before Phase C unless a
genuine defect is discovered. New work proceeds on SessionBoxes_V1 (MQL5 indicator,
strategy/execution-authority-free) as a fully separate track — see below.
```

---

**Read this first.** Every other top-level document in this folder (`README.md`,
`PROJECT_CHARTER.md`, `USER_MANUAL.md`, `MT5_MCP_SETUP.md`) still describes **`SESSION_FLOW_V1`**
as the active, automated-execution contract. That description is **stale** — `SESSION_FLOW_V1`
failed its Stage 2 backtest verdict on 2026-08-16/17 (see below) and the project reverted to a
different, more conservative contract before adding a new research track. Where any other document
disagrees with this file, **this file wins**. This audit found no top-level doc had been updated to
reflect that pivot.

---

## What is actually live right now

| | |
|---|---|
| Executable, demo-authorized contract | **`ASIAN_SESSION_V1`** — `config/strategy.yaml` |
| Config hash (signed off) | `a41881d1cb4de00c`, approved `EXECUTION_LAYER_REMEDIATION_2026_08_22` |
| Trading mode | `demo` — `live_execution_authorized: false` |
| Asian reference window | `00:00–07:00 UTC`, 28 closed M15 candles (corrected 2026-08-15; **not** 22:00–07:00/36 as older docs still say) |
| Execution window | `07:00–16:00 UTC` |
| Required server / account guard | `VTMarkets-Demo`, `require_demo_account: true` |
| Currently trading? | **No.** No process was connected/executing at the time of this audit (2026-08-25). Last verified MT5 read: account `***746` (demo), balance/equity 1,000.00 USD, 0 open positions, 0 pending orders. A follow-up live re-check failed with `IPC timeout` — restart the MT5 terminal if this persists. |

`session_strategy/` also contains an execution layer (`execution/executor.py`, `models.py`,
`validator.py`, `request_builder.py`, `risk_supervisor.py`) added 2026-08-22 (commits `44ebc68`,
`42d816d`) that is *capable* of submitting/modifying/closing demo orders under
`ASIAN_SESSION_V1` — this is a real change from the original read-only-only design the older docs
still describe. It has never been run unattended in production; nothing is currently scheduled to
invoke it automatically.

## Full strategy inventory (audited 2026-08-25, simplified)

14 strategy identities exist across `config/*.yaml`, the ledger, and (as of this update) one
external MT5 terminal artifact. Grouped by lineage/purpose and arranged by proximity to
execution — **exactly one group can place an order.**

| Group | Members | Status |
|---|---|---|
| **1 · LIVE** | `ASIAN_SESSION_V1` (`config/strategy.yaml`) | **Demo-authorized — the only strategy in this repo that can place an order.** Live-account execution disabled. |
| **2 · Rejected lineage** | `SESSION_FLOW_V1` (`a6188c364c63f39f`) → `SESSION_FLOW_V1_FIX1` (`7a9c682af3d10fbe`) | The trader's flowchart implemented literally, then patched once. Both dead ends: original **failed Stage 2** (767 trades, +0.038R/trade, fails 3/4 gates); the fix attempt is *worse* (813 trades, **-32.3R**, PF 0.955) and was left unresolved in `research` stage — a loose end this audit surfaced. Analysis-only. |
| **3 · Historical comparator** | `SESSION_FLOW_V2_SIMPLE` (`config/session_flow_v2.yaml`) | Validated ER-only router, kept as a reference baseline. Not live, not in active development. |
| **4 · Active research (blocked)** | `SESSION_STRATEGY_V2_RESEARCH` / "SESSION_V2" (`config/session_strategy_v2_research.yaml`) | The one track still being actively worked. `RESEARCH_CONTRACT_NOT_EXECUTION_AUTHORITY` — blocked on an unresolved Trend/Range regime classifier and missing M1 data. |
| **5 · Unverified source transcripts** | `SESSION_SOURCE_V1`, `SESSION_USER_RESOLVED_V2`, `SESSION_USER_RESOLVED_V2_AGENT` (`config/source_v1.yaml`, `user_resolved_v2.yaml`, `source_v2_agent.yaml`) | Three parallel attempts to transcribe the same 1BullBear Ep.18 source into a contract, all pre-dating `SESSION_FLOW_V1` and all self-flagged `NOT_INDEPENDENTLY_VERIFIED` / `BLOCKED_FROM_EXECUTION`. Superseded by `SESSION_FLOW_V1`'s later literal transcription (group 2); kept for provenance only. |
| **6 · SSPF v2.3 research line** | `SSPF_V2_3_RESEARCH` → `_REFINED_RESEARCH` → `_PRODUCTION_CANDIDATE` (all in one file, `config/no_trade_research.yaml`) | A separate ATR/DOM-based research line, unrelated to the session-box lineage above. All three variants set `execution.submit_orders/modify_orders/close_positions: false`; even the "production candidate" is only `APPROVED_FOR_EXTENDED_READ_ONLY_BACKTEST`. |
| **7 · Standalone experiments** | `SESSION_SWEEP_ENTRY_EXPERIMENT` (`config/sweep_entry_experiment.yaml`), `ST04_07_EXECUTION_ATTRIBUTION_V1` (`c121748f69283b55`, registered 2026-08-25) | Small, deliberately side-by-side studies that don't replace anything — one on sweep-entry variants, one on execution-fill attribution for Entry-2 signals. Both `RESEARCH_ONLY`, neither has a promoted result. |
| **8 · Ungoverned** ⚠️ | `mt5_range_bar_live.py` (repo root, untracked) | Not in `config/` at all — no `strategy_version.py` registration, no lifecycle gates, no spec. A synthetic range-bar momentum executor that **can** call `mt5.order_send` on the demo account (magic `108801`) if run directly. Every other group above is blocked by its own config; this one is only blocked by nobody having run it — the one real governance gap found in this audit. |
| **9 · External terminal artifact** | `R8_OBM_V1` (`7728ae9d414865d7`, registered 2026-08-25) | A compiled MQL5 EA (magic `8101501`) running **inside the MT5 terminal itself**, not in this repo — source/binary/journal live in the terminal's MQL5 data folder. Currently signal-only (`InpAllowDemoTrading=false`, verified live), 0 trades. Related to the trader's own external `ST-01 RANGE8 MOMENTUM → REJECT V1` research finding. **Validation also found the terminal was briefly attached to a REAL account on 2026-08-25** while this EA was loaded — its own hard-coded real-account block correctly prevented any order, but this is the first evidence any component near this project touched a live account. See `R8_OBM_V1_SPEC.md`. |

## Test suite (2026-08-25)

`python -m pytest tests/ -q` — **228 passed, 3 failed**:

- `test_golden_fixtures.py::test_versioned_golden_cases` — classifier now returns `UNCERTAIN` where a golden case expects `RANGE`.
- `test_safety.py::test_no_forbidden_mt5_call_appears_anywhere_in_the_package` — **fails**, because `mt5_gateway.py` now legitimately contains `order_send`/`order_check` for the 2026-08-22 execution layer. This is the test that used to *prove* the "analysis only, no order-mutating call" claim in `README.md`; that claim is no longer provably true and the test was never updated to match the intended read-only/execution gateway split.
- `test_source_v1.py::test_literal_midpoint_trend_entry_and_stop` — legacy v1 module, `detect()` returns `None` on a case expecting a trend entry.

None of these failures are reflected in any other top-level doc's status tables.

## ASIAN_SESSION_V1 execution wiring — built 2026-08-25

Previously, `session_strategy/execution/executor.py` (`DemoExecutor`) existed with proper layered
safety gates but was **never wired to anything** — the only reference to it anywhere outside its
own module was its test file. `sspf.py analyze` only ever produced a manual ticket; there was no
path from "an accepted signal exists" to "an order reaches the broker."

**Added `scripts/execute_session_signal.py`** — a manual-trigger command, by trader decision
(2026-08-25): run by hand per symbol, not scheduled or continuously polling. Reuses the exact same
`analyze()` pipeline as `sspf.py analyze` (same gates, same journal recording), and only if the
result is accepted does it build a `TradeIntent` and hand it to `DemoExecutor`.

**Deliberately narrow scope**: submits a single order with the correct entry/stop and a take-profit
at the **5R ceiling** (`tp2_5r`) only. It does **not** automate the strategy's real management
sequence (75% close at 4R, move stop to breakeven, run remainder to 5R) — `TradeIntent`/`RequestBuilder`
only support one stop and one target each, and building real partial-close automation was explicitly
deferred. The 4R step remains manual, exactly as `USER_MANUAL.md`'s `monitor` command already assumed.

**Two independent safety switches**, not one: (1) the script's own `--confirm` flag — without it,
always dry-run, no `order_check`/`order_send` call is even attempted; (2) `DemoExecutor`'s own
composite gate, which independently requires the `ALLOW_ORDER_SUBMISSION` environment variable to be
truthy or it fails closed with `SUBMIT_PERMISSION_DENIED`. Both tested 2026-08-25 (dry-run only,
against live EURUSD/GBPUSD analyses — both correctly returned `NOT_ATTEMPTED` with no signal accepted
at test time; the `--confirm` + order-submission path has not yet been exercised against a live
accepted signal).

### Hardening sequence, 14 steps, applied 2026-08-25 (steps 1-7 of 14)

A trader-specified sequence for turning the script above into something trustworthy before it ever
submits a real order. Status:

| # | Step | Status |
|---|---|---|
| 1 | Test an artificially accepted `StrategyResult` | ✅ `tests/test_execute_session_signal.py`, no MT5 needed |
| 2 | Verify exact `TradeIntent` mapping | ✅ field-by-field assertions, including the deliberate `tp2_5r` (not `tp1_4r`) choice |
| 3 | Deterministic `signal_id` | ✅ `signal_id()` — hash of strategy/symbol/session-date/setup/direction; stable across re-analysis, distinct across genuinely different signals |
| 4 | Duplicate-send protection | ✅ `already_sent()` — scans open positions AND today's deal history for this symbol's magic number before any broker call; MT5's ~31-char comment field can't hold a full signal_id, so this checks the broker's own record instead |
| 5 | `--check` mode | ✅ added — runs validation + risk sizing + a **real** `order_check` against the live broker, no `order_send` |
| 6 | Real Windows DEMO `order_check` | ⚠️ Built and mock-tested (`dry_broker_check()`, 2 tests verifying it calls `order_check` and surfaces retcode/comment, and that it stops before `order_check` if risk sizing fails) — **not yet exercised against a live accepted signal**. The 07:00–16:00 UTC execution window closed before a real signal appeared today. |
| 7 | Capture broker retcode/comment/request | ✅ `dry_broker_check()` returns all three in its result dict |
| 8 | One tiny controlled DEMO `order_send` | ✅ **Done, later same day** — via a clearly-labeled synthetic test harness (`scripts/test_demo_execution_harness.py`), not a natural signal; see "Execution infrastructure validated" below |
| 9 | Reconcile order/deal/position | ✅ `reconcile_position()` — independently re-queries the broker rather than trusting the retcode; see below |
| 10 | Restart/retry idempotency | ⚠️ Partial — the durable ledger check (`execution_already_committed()`) is proven; a genuine kill-and-restart-mid-send test has not been run |
| 11 | Real 4R → 75% partial | ❌ Not done — deliberately out of scope for the current contract |
| 12 | Runner SL → breakeven | ❌ Not done |
| 13 | Close remaining 25% at 5R | ❌ Not done |
| 14 | Forward-test on demo | ❌ Not started — blocked on Phase C below |

### Execution infrastructure validated — later 2026-08-25

**Two real bugs found and fixed, not cosmetic:**
1. `RequestBuilder.build()` was building every order as a market BUY regardless of `intent.direction`/`entry_type` (and using the wrong MT5 dict key, `"order_type"` instead of `"type"`, which likely would have dropped the field entirely). Would have sent the wrong side/type of order for any SHORT or LIMIT intent — found and fixed before any live test, not discovered live.
2. Session quota was gated on `journal.trades_this_session()` (any printed ticket, including dry runs), not on whether an order was actually sent. This had already silently consumed today's one real EURUSD signal's quota via an earlier routine `sspf.py analyze` call, before `execute_session_signal.py` existed. Fixed by gating on the execution ledger (`has_committed_execution_today()`) instead.

**Proven live against the real broker** (`scripts/test_demo_execution_harness.py`, magic `999999`, tagged `TEST_EXEC_NO_SIGNAL` — never counted toward strategy statistics): `order_check` PASS both directions, one `order_send` (retcode `10009`/DONE), broker created a real pending LIMIT order with entry/SL/TP matching the request exactly (verified by independent re-query, not by trusting the retcode), then cancelled cleanly. Correction to the terminology used when this was first reported: a pending LIMIT order is a confirmed **order**, not a confirmed **position** — those stay distinct states (`PENDING_ORDER_CONFIRMED` vs `POSITION_CONFIRMED` in the ledger) since a fill can still turn into `FILLED → POSITION_OPEN → POSITION_CLOSED` or `CANCELLED/EXPIRED/REJECTED` later.

**Status, precisely** (broken into two axes — do not conflate them):

```
EXECUTION INFRASTRUCTURE                        STRATEGY END-TO-END
────────────────────────                        ────────────────────────
Signal → Intent                    PASS          Natural strategy signal
Risk sizing                        PASS            → intent → risk → order_check
Request construction               PASS            → order_send → broker ack
Duplicate controls                 PASS            → fill/no-fill → exit
Real DEMO account verification     PASS            → journal reconciliation
Real order_check                   PASS                                    NOT YET PROVEN
Real order_send                    PASS
Pending-order broker confirmation  PASS          FORWARD_TEST_INFRASTRUCTURE_READY = YES
SL/TP reconciliation               PASS          NATURAL_SIGNAL_E2E_VALIDATED      = NO
                                                  LIVE_READY                        = NO
Freeze label: DEMO_EXECUTION_INFRASTRUCTURE_VALIDATED_V1
```

**Architecture note — durable vs. in-process protection, clarified 2026-08-25**: `submit_one_order()`'s
module-level `_orders_sent_this_run` counter is **process-local only** — it protects against a bug
sending two orders within one script invocation, nothing more. It resets on every process start and
provides zero protection across restarts or concurrent invocations. **The durable, cross-process
authority is `execution_already_committed()`**, checked *before* `submit_one_order()` is ever
called — it consults the SQLite execution ledger (survives restarts, `signal_id` is the primary key)
and the broker's own position/deal history. One known, undefended gap: there is a narrow window
between `execution_already_committed()` returning clear and `ledger.mark_send_requested()` actually
writing — two genuinely concurrent invocations for the same signal could both pass the check before
either writes. Not defended against today; acceptable for a manually-triggered, one-invocation-at-a-time
command, but would need a proper `INSERT ... WHERE NOT EXISTS`-style atomic claim before this could
ever run unattended or concurrently.

**Test suite, precisely classified**: **260 passed, 4 known failures, 0 new regressions** — see
`KNOWN_TEST_FAILURES.md`. Not simply "passing"; each of the 4 stays failing until it is corrected,
intentionally retired, or (for the golden-fixtures/safety/source_v1 three) independently addressed,
per that file's classification. `pytest tests/test_execute_session_signal.py
tests/test_execution_ledger.py tests/test_reconciliation.py tests/test_execution_gates.py` — the
execution-specific suite — is 100% green (61/61).

### Phase C — next: a genuine natural signal, not another synthetic test

Do not build more execution features before this. Next trading-window opportunity:
`sspf.py analyze`/`execute_session_signal.py --check` must originate the signal itself — no
manually-constructed entry price, no test harness. Full lifecycle target:
`SIGNAL → INTENT → VALIDATED → CHECKED → SENT → ORDER_CONFIRMED → PENDING → (FILLED → POSITION_OPEN
→ POSITION_CLOSED) | (CANCELLED/EXPIRED/REJECTED)`. Log one full reconciliation record (signal
identity, sized volume, pre-send tick, request vs. broker-confirmed price/SL/TP, fill details, exit
reason, realized R) proving semantic continuity end to end. Only after that does the project move
from `DEMO_EXECUTION_INFRASTRUCTURE_VALIDATED_V1` to `DEMO_FORWARD_TEST_ACTIVE`. Not doing yet:
real accounts, higher submission quotas, concurrent orders, partial exits/BE/trailing, or further
refactoring of the now-proven send path.

**Regression found and fixed while running the full suite after this work**: `config/strategy.yaml`'s
`account_guard` fix (above, earlier 2026-08-25) had broken 5 previously-passing tests in
`tests/test_engine.py` — their fixtures hardcoded the old placeholder server (`VTMarkets-Demo`) and
login suffix (`985`), which no longer matched the corrected real values. Fixed the fixtures to use
the real account (`VantageMarkets-Demo`, login `25972746`/suffix `746`) instead of reverting the
config. Test suite is back to exactly the pre-existing 3 known failures
(`test_golden_fixtures`, `test_safety`, `test_source_v1`) plus the expected, real
`test_governance_approves_stage_2_baseline_and_locks_optimization` failure — that one is intentional:
it detects the same signoff-hash drift documented above and should keep failing until you actually
re-approve the config. **241 passed, 4 failed** as of this update (was 228/3 before this session's
work; +14 for the new test file, +1 legitimately-failing governance test).

## MT5 demo account guard — validated and fixed 2026-08-25

`account_guard.required_server` was `VTMarkets-Demo` and `fallback_account_suffix` was `985`;
the actual connected demo account is server `VantageMarkets-Demo`, login ending `746`. Since
`session_strategy/engine.py` does an exact string match on server name, `G1_ENVIRONMENT` failed
on every single run regardless of setup quality — confirmed via `python sspf.py readiness`
(`DEMO_ACCOUNT: passed: false`) before the fix. **Corrected** — `readiness` now reports
`DEMO_ACCOUNT: passed: true`. `SSPF_ALLOWED_LOGINS` is still unset, so account identity is only
weakly verified by suffix; set it for an exact match.

This edit changed the config, so `PARAMETERS_SIGNED_OFF` now correctly reports
`"trader approval for active config is missing"` — `signoff_hash`
(`session_strategy/config.py:86-92`) is computed live over the whole config excluding the
signoff block itself and legitimately no longer matches the 2026-08-22 recorded approval. This
is the check working as designed. **Re-signoff by the trader is required** before this config
counts as approved again. (Correction to an earlier claim in this project's chat history: this
hash check was never a no-op self-comparison — it does detect real drift, and did not need a
code fix.)

Separately, `sspf.py readiness`/`sspf.py health` self-identify as the "SSPF v2.2 read-only MT5
assistant" — a pre-execution-layer Stage-1 tool. Its `CODE_READ_ONLY` and `EXPERT_TRADING_DISABLED`
checks require no order-mutation permissions and algo trading off, which will never pass now that
the 2026-08-22 execution layer intentionally allows order mutation for demo execution. This tool
needs a rewrite or retirement for the current design before its `NOT_READY` verdict means
anything beyond those two structurally-obsolete checks.

## Other known drift

- `requirements.txt` lists `MetaTrader5` twice — flagged as unresolved cleanup in the 2026-08-22
  Execution Layer Remediation plan and still unfixed.
- `ACTIVE_STATUS.md` is an auto-generated MT5 account snapshot, not a narrative status doc — do not
  read it as project status; it only tells you the account's current balance/positions.
- Everything under `outputs/` predates the 2026-08-15 corrections and the 2026-08-22/23 pivots; none
  of it measures the currently-live `ASIAN_SESSION_V1` contract or the `SESSION_V2` research track.

## Data

Three FX datasets, 1,440 M15 bars each, 2022-10-02 21:00 .. 2022-10-21 20:45 UTC, offset +3.
`data/README.md` has the column contract. A sealed out-of-sample period (`data/sealed/`, May–Aug
2026, 4 symbols) exists and is unopened — see `ROADMAP.md`.

## What to do next

1. **Reconcile the doc set with reality.** `README.md`, `PROJECT_CHARTER.md`, `USER_MANUAL.md`, and
   `MT5_MCP_SETUP.md` all still center the project on `SESSION_FLOW_V1` with full automated
   execution; none mentions the `SESSION_V2` research track or its execution block. Bring them in
   line with this file or archive/rewrite them.
2. **Fix or intentionally retire the 3 failing tests** — in particular restore or replace the
   read-only-boundary safety test now that an execution gateway legitimately exists, so "no
   order-mutating call" claims are either true again or removed from the docs.
3. **Resolve the `SESSION_V2` regime classifier** — the blocking item for that research track.
4. **Deduplicate `requirements.txt`.**
5. **Decide the status of `mt5_range_bar_live.py`** — commit it under an explicit contract with its
   own governance, or remove it from the working tree if it was a throwaway experiment.

---

Analysis and (demo-only, non-automated) execution capability coexist in this codebase today. Nothing
in this project is authorized for live-account execution. Passing every gate means the configured
rules passed — nothing more.
