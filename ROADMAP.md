# Roadmap — rewritten 2026-08-17

The previous roadmap was titled *"from here to a verdict."* **The verdict arrived on
16 August and it was negative.** Every step it listed as future work is now either
done or superseded. This file replaces it.

Current numbers: `STATUS.md`. Version history: `STRATEGY_LEDGER.md`.

---

## Where the project actually is

```
STAGE 1  does the tool apply the rules correctly?
         7 of 8 criteria met  ·  S1.5 NOT STARTED (0 of 20 reconciliations)
              |
              |   blocked: 164 tickets have produced 0 trades, so there is
              |   nothing to reconcile
              v
STAGE 2  does the strategy have an edge?
         VERDICT DELIVERED: no, as implemented
         a6188c364c63f39f  ·  rejected  ·  18 hypotheses  ·  Bonferroni |t| > 2.99
```

**The best configuration found**, 12 months, 3 FX symbols, gold excluded:

```
767 trades   +29.364R   +0.038R/trade   PF 1.045   DD 39.055R
95% CI [-0.112, +0.188]   t = 0.40 against a 2.99 threshold

PASS  trades >= 50
FAIL  expectancy >= 0.10R
FAIL  profit factor >= 1.20
FAIL  max drawdown <= 10R
```

Oct 2022's +27.124R over 63 trades — which passed all four gates — was noise. At
t=1.46 against 2.81 it never survived correction either.

## What the previous roadmap asked for, and what happened

| Old step | Status |
|---|---|
| 1 · Sign four decisions | **§5.3a signed** on benchmark evidence. Three remain: §4-A, §4-B, §4-C |
| 2 · Close Stage 1 (S1.5) | **Not started.** 164 tickets, 0 trades, 0 matches, 0 verifications |
| 3a · Reach ~114 trades | **Done — 1,030.** 4 symbols, 262 days |
| 3b · Recompute drawdown chronologically | **Done.** 11.071R was symbol-major; chronological is 6.330R. The breach was a measurement artifact |
| 3c · Seal an out-of-sample period | **Done.** `data/sealed/` — May–Aug 2026, 4 symbols, **unopened** |
| 3d · Run the battery | Partial. Cost stress, collision audit, leave-one-out done. Multiple-testing now enforced by the ledger |
| 4 · Go live | **Not reachable.** The verdict is negative |

Two things the old roadmap never anticipated, both found on the 16th:

- **FIX 0 — `RANGE SETUP` was unreachable.** `swept = body < session_high` is
  trivially true, so SWEEP fired 1,486/1,486 and one of three terminals was dead
  code. **Fixed** by `THETA_REJ = 0.05`; RANGE now fires ~27% of sessions.
- **A precision bug zeroed spread costs** on EURUSD and GBPUSD across 524 trades.
  First result read −43.204R; corrected, −117.683R.

---

## The gate that now orders everything

> **Is this strategy worth continuing to develop?**

That is a trader's decision, not an engineering one, and the honest inputs are:

**Against.** Nine months, four symbols, all in-sample, thresholds chosen while
looking at the data — and it still fails three of four gates. Gold loses before
costs. The CI spans zero at n=767.

**For.** Two structural defects mean **no clean measurement of the strategy has ever
been taken.** Every number above was produced by an engine with a dead branch, a
sweep test that never runs the source's own "away from the swept side" rule, and no
trail on the TREND runner. The sealed period is unspent.

**The cost of finding out is about a week of work**, not a month.

---

## If continuing — the sequence

### 0 · FIX 1 and B6, then re-baseline as a NEW version

Nothing below is interpretable until these land. `ENGINE_FIX_SPEC.md` has both.

**FIX 1 — sweep detection is single-sided.** `ext = lv["hi"] if bear else lv["lo"]`
means bias picks which side to hunt, so a sweep is found there by construction and
the source's *"trade away from the swept side"* has never executed. Detect both
sides independently; direction comes from which side was swept.

**B6 — the trail.** Three files print *"then trail"*; `simulate()` sets `sl = e`.
The diagram says *"close 75% at 4R and Trail."* TREND is 493 of 767 trades and the
year's best bucket at +0.076R — its management is wrong, so its number is not the
strategy's number.

Both change the rules, so both produce a **new version id** with a fresh hypothesis
count. `a6188c364c63f39f` stays rejected and unamended.

### 1 · B12 — the lookahead audit, written now and run every build

13 test files, none tests lookahead. `AGENT_SKILLS.md` calls it *"the single most
likely source of fake edge"* and it has zero coverage.

Cheapest sufficient form: **truncation invariance.** Grade a session with the full
dataset, then with every bar after the reference close deleted. The plans must be
byte-identical. ~20 lines, subsumes most of the rest.

### 2 · Sign §4-A, §4-B, §4-C

| | Decision | Note |
|---|---|---|
| §4-A | bias | `close_location` recommended; must become **exogenous** — the engine derives it from the session it grades |
| §4-B | range test | **the diagram supplies no test at all.** Efficiency ratio is an interpretation; so was the retracted "middle portion" gloss |
| §4-C | trail | the source defines it; choosing breakeven instead is a **deliberate deviation from `[DIAGRAM]`**, not a signature |

### 3 · B7 → B8 → B11 — declare, sweep, read

Nine parameters, six of which were invisible until the 16th. Register them, hash them
onto every result, sweep the grid, then apply the pre-registered reading: **sign
stable → identified, report the median; sign flips → not identified, publish the
interval with flip points named.**

### 4 · Open the sealed period — once

May–Aug 2026, four symbols. **Only after steps 0–3.** It can be spent once, and it is
the only unbiased evidence this project will ever have on this rule set.

### 5 · Stage 1, if and only if Stage 2 survives step 4

S1.5's twenty hand reconciliations cost two to three weeks of calendar time and
validate conformance of a rule set that is currently changing. Doing it now would
certify the wrong thing.

**And a prior question:** 164 tickets have produced **zero** trades — 132 `NO_TRADE`,
32 `EXPIRED`. Whether that is the gates working or the engine never reaching a
tradeable state must be answered before anyone waits two weeks for twenty tickets.

---

## If stopping

A documented "no" produced cheaply is a good outcome — `PROJECT_CHARTER.md` §5.4 says
so, and this one cost days rather than months. What the project already owns and keeps:

- a reproducible data pipeline with sha256 manifests and drift detection in CI
- a strategy ledger that catches multiple-testing retroactively
- a costed, chronologically-ordered backtester with a collision audit
- 30 generated worked examples usable as a regression suite
- the finding that **gold is unprofitable before costs** on this method

None of that is wasted if the strategy is abandoned.

---

## What would still make this fail honestly

- **The sealed period comes back negative.** The most likely single outcome and the
  whole point of sealing it.
- **FIX 1 and B6 do not move the number.** Then the two defects were not the reason,
  and the rejection stands on a clean measurement.
- **Bias turns out to be discretionary.** The source says *"supplied by the user; you
  never invent it."* If it cannot be written down, this cannot be backtested — and
  that is worth knowing explicitly rather than discovering in month three.

---

## Compressed

```
0  FIX 1 + B6, re-baseline as a new version id      ~2 days   <- nothing else counts first
1  B12 truncation-invariance test                   ~2 hours  <- write it now, out of order
2  sign 4-A, 4-B, 4-C                               ~1 hour
3  B7 -> B8 -> B11 declare, sweep, read             ~1 day
4  open data/sealed/ ONCE                           ~1 hour
5  Stage 1 / S1.5, only if 4 survives               2-3 weeks
```

Steps 0–4 are about a week. Step 5 is calendar time and cannot be shortened.

**Analysis only throughout.** Nothing in this project places, modifies or cancels an
order. MT5 stays read-only, `Allow algorithmic trading` stays off, and MTX is not
installed — see `MT5_MCP_SETUP.md`.
