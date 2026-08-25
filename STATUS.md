# Project status — 25 August 2026

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
