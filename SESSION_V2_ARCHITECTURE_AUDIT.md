# SESSION V2 Architecture Audit

Date: 2026-08-23
Authority: `SESSION STRATEGY V2 UPGRADE AGENT PROMPT`
Status: **AUDIT_COMPLETE / IMPLEMENTATION_IN_PROGRESS**

## Authority reconciliation

The attached owner ruling supersedes the previous `SESSION_FLOW_V2_SIMPLE` routing
authority where they conflict. In particular, `ER_ONLY_V2` at `0.40` is retained as
a research comparator but is no longer authoritative for the upgraded strategy.
The existing V2 router and its 90-box population remain reproducible historical
evidence, not evidence for the upgraded contract.

| Area | Existing repository state | V2 upgrade disposition |
| --- | --- | --- |
| Reference boxes | `FrozenSession` and `SessionLeg` exist | KEEP; add canonical reference names and facts |
| Regime | `ER_ONLY_V2` is machine-authoritative | RESEARCH_ONLY; no authoritative regime classifier yet |
| Sweep | Completed-box causal scanner exists, but is too permissive for the supplied ruling | RESEARCH_ONLY until strict-level qualification is validated |
| Trend bias | Several incompatible legacy proxies | RESEARCH candidate only; no silent promotion |
| Trend entry | Legacy engines calculate midpoint variants | KEEP midpoint geometry separate from bias/regime |
| Range entry | Signed specification exists, implementation pending | IMPLEMENT as a downstream contract component |
| Risk | Duplicated legacy calculations | CONSOLIDATE pure 25% / 4R / 5R geometry |
| Fill | M15 simulators and retired Cowork M1 primitives exist | M1-authoritative result unavailable; do not claim fills |
| Safety | Read-only gateway and order-send blocking tests exist | PRESERVE; no authorization changes |

## Canonical functional map

| Required capability | Current location | Status |
| --- | --- | --- |
| MT5 data reader | `session_strategy/mt5_gateway.py` | `EXECUTION_ENV / READ_ONLY` |
| Session calculator | `session_strategy/session_contract.py` | `VALIDATED foundation` |
| Regime features | scattered legacy level functions | `MISSING; added by V2 research layer` |
| Regime classifier | `classify_trend_range` | `RESEARCH_ONLY after upgrade` |
| Trend bias | legacy engine and research scripts | `RESEARCH` |
| Strict Sweep detector | `classify_sweep` | `RESEARCH; validation required` |
| Trend setup | legacy `engine.py` | `RESEARCH / contract incomplete` |
| Range setup | `RANGE_SETUP_V2_SPEC.md` | `CONTRACT_LOCKED / implementation pending` |
| Risk and targets | duplicated engine/script logic | `CONTRACT_LOCKED geometry; consolidate` |
| Fill validator | `cowork_execution_v2.py` | `RESEARCH / M1 data unavailable` |
| Outcome evaluator | legacy backtest scripts | `RESEARCH; not authoritative` |
| Trade journal | `session_strategy/journal.py` | `EXECUTION_ENV / analysis only` |
| Backtest analyst | `scripts/backtest_*.py` | `LEGACY / research only` |
| Risk supervisor | `session_strategy/execution/risk_supervisor.py` | `EXECUTION_ENV / preserve` |

## Data and reconstruction audit

- Primary supplied M15 sources exist for EURUSD, GBPUSD, and USDJPY October 2022.
- `benchmarks/oracle_30.csv` contains the required 30 labelled reconstruction
  cases: 16 Trend cases and 14 Range-regime cases, split into 4 Sweep and 10
  plain Range setups.
- The existing 90-box study uses three symbols and two legs. Its `8 / 81 / 1`
  routing counts are not comparable to the required EURUSD 30-case reconstruction.
- Workspace inventory found no authoritative M1 Bid/Ask dataset. M15-only results
  must therefore expose `AMBIGUOUS`, `MISSED`, or `EXECUTION_UNAVAILABLE` rather
  than claiming broker-realistic fills.

## Safety audit

- `MT5ReadOnlyGateway` is the package MT5 boundary.
- Package tests reject mutating MT5 methods and scan for forbidden `mt5.*` calls.
- No V2 upgrade change may add `order_send`, `order_check`, scheduling, or live/demo
  order authorization.
- Current account report shows no open positions and no pending orders; this is
  operational context, not strategy evidence.

## Required gaps before authoritative execution

1. Select and validate a deterministic Trend/Range regime rule without using the
   October outcomes to optimize it.
2. Close the Trend Bias contract and validate its reason codes against the labelled
   cases and unseen data.
3. Validate the strict Sweep detector and reconcile its four expected EURUSD cases.
4. Implement the Range fallback without importing legacy touch tolerances.
5. Separate signal intent from M1 fill, and obtain authoritative Bid/Ask data before
   claiming executable results.
6. Keep the October labels as reconciliation targets; never hard-code them in the
   strategy engine.
