# Stage 1 — Recommendation Correctness (ASIAN_SESSION_V1)

Strategy: **ASIAN_SESSION_V1 v1.0** · Last verified **2026-08-15**

> The project migrated from SSPF v2.2 to ASIAN_SESSION_V1 on 2026-08-11. Qualification restarts:
> the session window, classification metric, entry model, partial target and risk fraction all
> changed, so no prior evidence carries over.

Stage 1 asks one question: **does the tool recommend correctly, according to the trader's own
strategy rules?** It does not ask whether the strategy is profitable — that is Stage 2.

Closing Stage 1 is the gate to beginning day trading with the hybrid workflow.

---

## Completed

- Dedicated local project is present.
- The runtime is strictly read-only; no MT5 order mutation methods are exposed, and this is
  enforced by `tests/test_safety.py`.
- Expected demo account suffix `985` and server `VTMarkets-Demo` are fail-closed environment
  gates.
- MT5 connection is healthy and the expected demo account/server were verified.
- Broker minimum/maximum volume, volume step, tick size, and minimum stop distance are read
  directly from MT5 and included by `python sspf.py health`.
- Session is configured as 22:00–07:00 UTC with exactly 36 closed M15 candles, followed by a
  bounded 07:00–16:00 UTC execution window. Window/count consistency is enforced at config load.
- Broker UTC offset is derived per run from a cross-symbol consensus, so the system is
  DST-safe and free of hard-coded offsets.
- Risk is configured at 0.5% of equity per trade, 2% daily, 15% maximum drawdown, one trade per
  symbol per session.
- Contract and generated tickets identify ASIAN_SESSION_V1 v1.0.
- Weekday automation is active for read-only shadow analysis (definitions live outside the
  project — finding A10).
- Automated test suite passes — **124 tests**, covering midnight crossing, missing and duplicated
  candles, both sweep directions, structural stop failure, boundary touch without rejection,
  trend confirmation and cancellation, 4R/5R arithmetic, risk gates, and repeat-run determinism.
- **The trader's strategy is transcribed as the source of truth** (`STRATEGY_SPEC.md` §0) and the
  engine is verified against it rule by rule **by execution** — see §6 of that document.

---

## Exit criteria — what must be true before day trading begins

| # | Criterion | Status | Blocker |
|---|---|---|---|
| S1.1 | Every rule in `STRATEGY_SPEC.md` §0 conforms | ✅ **verified** | — |
| S1.2 | No gate reports `PASS` without testing anything | ✅ **pass** | `G10_STRUCTURAL_STOP` verified falsifiable |
| S1.3 | Conformance checker supports the current two-state artifact model | ✅ **implemented and tested** | fresh live artifact still required |
| S1.4 | Artifacts remain verifiable after a config change | ✅ **implemented** | schema v2 embeds and validates its config snapshot |
| S1.5 | 20–30 tickets reconciled by hand against MT5, zero discrepancies | ⏳ **not started** | — |
| S1.6 | Order-capable MT5 tools disabled in the operating environment | ✅ **met locally** | code is read-only; MT5 Algo Trading is off |
| S1.7 | Provisional parameters signed off (Q3) | ✅ **approved** | baseline fingerprint `0f2e89f3a44fca01` |
| S1.8 | Journal reconciliation correct, so risk gates are trustworthy in live use | ✅ **implemented and tested** | includes broker suffix matching and date-scoped risk |

**Stage 1 status: NOT MET.** The technical blockers and baseline approval are closed. The only
remaining gate is 20 fresh manual reconciliations with zero discrepancies. `python sspf.py
readiness` reports this directly.

### Remaining order of work

1. Generate a clean current-config evidence set and record 20 manual MT5 reconciliations.
2. Run `python sspf.py readiness`; proceed only when every check passes.

### Completed 2026-08-11

- **Migrated to ASIAN_SESSION_V1.** New session window, classification metric, three setup
  detectors, entry-at-close model, 4R/5R targets, 0.5% risk, and stable reason codes.
- **Config validation** now rejects unknown or missing keys and cross-checks candle counts
  against the configured windows.
- **Read-only boundary** asserted at connect time and scanned across the whole package.
- **Journal reconciliation** partially repaired: unmatched counting fixed, open risk date-scoped.
- Test suite expanded to **124 tests**.
- Config hash: **`2530b751134fbf6e`**; sign-off fingerprint **`0f2e89f3a44fca01`**
  (supersedes `6683a3625e51eb09`, `fddb7465a73fd724`, and `92279f3d42d32fc3`).

---

## Note on existing artifacts

Every artifact in `outputs/` predates ASIAN_SESSION_V1 and was produced under SSPF v2.2 across
several configuration hashes. None can serve as Stage 1 evidence: the session window, the
classification metric, the entry model, the partial target and the risk fraction have all changed.
Start a clean evidence set once the provisional parameters are signed off.

---

## Safety state

The project remains demo/shadow only until Stage 1 closes. Passing Stage 1 authorises **manual
day trading with human verification of every order** — nothing automated, and no claim about
profitability. That question belongs to Stage 2, which cannot yet be run because no backtest
engine exists (finding A27).
