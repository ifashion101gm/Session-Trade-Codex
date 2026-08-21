# Agent skills manifest — M15 session trading

Applied 2026-08-16. The two-tier split is adopted: **Tier A the grader** (prompt +
arithmetic, one session, one plan) and **Tier B the engine** (code, date ranges,
fills, sweeps). Tier A is a strict subset of Tier B and is the reference
implementation B must agree with on any single session.

Status audited against the codebase, not asserted.

---

## ⚠ CONFLICT — A6 contradicts a signed trader ruling

The manifest specifies:

> **A6** — *"Apply as veto on SWEEP/TREND, selector on RANGE. **Emit NO TRADE**."*
> Fails as: *"The dead-branch defect."*
> **B9** — *"NO-TRADE fired count."*
> **Build order 2** — *"Verify B9's NO-TRADE count is non-zero."*

The trader ruled earlier the same day:

> **[TRADER] 2026-08-16 — "On this strategy the NO-TRADE branch can never fire."**

The diagram carries three terminal boxes and no fourth. `SESSION_FLOW_V1_SPEC.md`
§1 records the ruling and retracts the agent document's *"Mismatch → NO TRADE"* and
*"Bias filter is mandatory"* as glosses, in the same class as the retracted "middle
portion" wording in §4-B.

**Resolution — A6 is amended, not implemented as written:**

| Manifest | Amended |
|---|---|
| bias = veto on SWEEP/TREND | **selector everywhere; no veto** |
| emit NO TRADE on mismatch | **no NO-TRADE terminal exists** |
| B9 counts NO-TRADE fired | **B9 counts direction-source attribution instead** |
| build step 2: NO-TRADE count non-zero | **build step 2: NO-TRADE count is zero by design** |

**What survives from A6 and is not negotiable:** bias must be **exogenous**. The
engine currently derives it from `close_location` of the very session it grades
(`session_flow.py:64`). That remains `[UNSIGNED]` and is a real gap.

### Two different dead branches — do not conflate them

| | Branch | Status |
|---|---|---|
| Manifest's "dead-branch defect" | NO-TRADE never fires | **correct by design** — trader ruling |
| `ENGINE_FIX_SPEC.md` **FIX 0** | **RANGE SETUP never fires** — 0 of 1030 trades | **genuine defect, blocker** |

FIX 0 is the real dead branch: `swept = body < session_high` is trivially true, so
SWEEP is taken every time and one of the diagram's three terminals is unreachable.

---

## TIER A — the grader

| # | Skill | Status | Evidence / gap |
|---|---|---|---|
| **A1** | M15 data intake | ⚠️ **partial** | `build_dataset.integrity()` checks duplicate stamps and OHLC violations. **No 900-second spacing check, no mid-session gap check, no timeframe assertion.** Grep for `900` returns nothing. |
| **A2** | Session boxing | ✅ | `SF.V.window()` + `LEGS`; DST resolved per-bar in `fetch_mt5_year.py` and verified empirically by the hourly-range profile. Completeness enforced via `len(ref) < 8`. |
| **A3** | Session geometry | ✅ | `SF.levels()` — top, bottom, range, open, close, midpoint. |
| **A4** | Range/trend classifier | ⚠️ **must declare** | `efficiency_ratio ≤ 0.35`. Source supplies **no test** (§4-B retraction). Engine does not name the test in its output. → FIX 3 grid. |
| **A5** | Sweep detection | ❌ **defective** | Vacuous test; single-sided (bias picks the side, so *"away from the swept side"* never runs). → **FIX 0 + FIX 1**. |
| **A6** | Bias intake + gating | ❌ **endogenous** | `bias = close_location(graded session)`. Must become an input. Veto/NO-TRADE portions **withdrawn** per ruling. |
| **A7** | Risk arithmetic | ⚠️ **partial** | `R = 0.25 × range`, `SL = e ∓ R`, `TP = e ± 5R` — all verified to floating-point equality on real sessions. **No tick-size rounding**: grep for `round`/`tick_size` in `session_flow.py` returns nothing. |
| **A8** | Rolling grader | ✅ | Asia→London, London→NY, same tree, `LEGS` constant. |
| **A9** | Output discipline | ⚠️ **partial** | `engine_report.py` emits a desk report, not the fixed block. Carries the analysis-only disclaimer. |
| **A10** | Refusal / guardrails | ⚠️ **partial** | `tests/test_safety.py` exists; no timeframe refusal, no indicator refusal, no invented-bias refusal. |

**3 of 10 complete.** The manifest's own note holds: A1–A3, A5, A7, A8 are pure
determinism and belong in tool calls; A9 and A10 are the only ones that need a
language model.

## TIER B — the engine

| # | Skill | Status | Evidence / gap |
|---|---|---|---|
| **B1** | Historical data pipeline | ✅ | `fetch_mt5_year.py` — DST per bar, empirical offset verification, sha256 manifests, drift check in CI. Holiday/low-liquidity treatment **not recorded**. |
| **B2** | Bias service | ❌ **missing** | No bias series exists. 7 candidates tested; best t=0.87 vs a 2.69 threshold. |
| **B3** | Order simulation | ⚠️ **partial** | Limit fills modelled; spread from the master column; slippage parameterised. **Gap-through not handled** — a limit gapped past fills at its own price. |
| **B4** | Intrabar sequencing | ✅ | `STOP_FIRST` uniform, `TARGET_FIRST` bound computed every run, collision audit reports both (7 of 1030, worth +14.5R). |
| **B5** | Partial-fill accounting | ✅ | 75% booked at the management level, 25% runner, R blended: `banked + 5 × 0.25`. |
| **B6** | Trail engine | ❌ **missing** | Three files print *"then trail"*; `simulate()` sets `sl = e`. **TREND's number is not the strategy's number until this exists.** |
| **B7** | Parameter registry | ❌ **missing** | Unsigned choices are argparse flags with defaults, not registered, not stamped on results. |
| **B8** | Grid runner | ❌ **missing** | Sweeps run ad hoc; no config-hash-keyed cells. |
| **B9** | Metrics + attribution | ✅ | By symbol, leg, setup, setup×leg, month with cumulative; chronological drawdown; cost drag. **Amend: NO-TRADE count replaced by direction-source attribution.** |
| **B10** | Result ledger | ✅ | `scripts/strategy_version.py` + `versions/ledger.json`. `a6188c364c63f39f` lives there, rejected, 16 hypotheses, Bonferroni |t| > 2.96. |
| **B11** | Sensitivity reading | ⚠️ **pre-registered** | Protocol written in `ENGINE_FIX_SPEC.md` FIX 3 — sign stable → identified, report median; sign flips → publish interval with flip points. Not yet code. |
| **B12** | Lookahead audit | ❌ **missing** | 13 test files, **none tests lookahead**. The manifest calls this the single most likely source of fake edge, and it is the one with no coverage at all. |

**6 of 12 complete.**

---

## Out of scope — confirmed

Multi-timeframe · indicators (EMA/RSI/volume) · FVG, order blocks, structure shifts ·
news filters · position sizing · discovery outside the tree · conviction or
probability language · **live broker execution**.

The last one is already project policy: MT5 is granted read-only, `Algo Trading` is
off, and no script imports an order function. The manifest's reasoning — separate
system, separate failure modes, do not fuse — is adopted verbatim.

---

## Build order — amended

```
1  A1-A3, A5, A7   deterministic geometry + FIX 0.   unit-test against hand-worked sessions
                   A1 needs the 900s check; A7 needs tick rounding; A5 is the blocker
2  A6 + B2         bias EXOGENOUS.
                   AMENDED: no NO-TRADE branch to bring live (trader ruling).
                   verification becomes: direction is attributable to a declared
                   source on every trade, and NO-TRADE count is ZERO by design
3  B6              the trail. TREND is the only positive bucket and its
                   management is wrong, so its number is not yet the strategy's
4  B12             lookahead audit, BEFORE any further result is believed
5  B7 -> B8 -> B11 declare, sweep, read. only now is A4 measurable
6  A9, A10         output and refusal, wrapping the whole thing
```

**Steps 1 and 3 are the open defects. Step 5 is the open question.**

The manifest put FIX 0 inside step 1 without naming it; it is called out here
because A5 is not a partial implementation — it is a fork wired to a constant, and
every bucket statistic recorded so far is a measurement of unreachable code.

### One correction to the manifest's own sequencing

It places B12 (lookahead) at step 4. **The audit should be written now and run
continuously**, not reached in sequence — it is cheap, it has zero coverage today,
and every result produced between here and step 4 would otherwise be unaudited.

---

## Version handling

None of this amends `a6188c364c63f39f`, which is `rejected` and whose ledger entry
stands. Each skill landing that changes the rules produces a **new** id with its own
hypothesis count. `data/sealed/` stays shut until the registry (B7) is frozen.
