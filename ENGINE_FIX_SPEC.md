# Engine fix spec — 16 August 2026

Applying the review against `scripts/session_flow.py`, which the reviewer did not
have. Four of their items confirmed. **A fifth was found that outranks all of them.**

Target: `plan()`, `scripts/session_flow.py:67–93`. Current version
`a6188c364c63f39f` (rejected).

---

## FIX 0 — RANGE SETUP is unreachable. The tree has a dead branch. **[BLOCKER]**

```
Aug 2025 - Apr 2026, 1030 trades:   TREND 660   SWEEP 370   RANGE 0   (0.00%)
Oct 2022,              63 trades:   TREND  41   SWEEP  22   RANGE 0   (0.00%)
```

One of the diagram's three terminal buckets has never fired. Not rare — **never**.

### Why

```python
ext   = lv["hi"] if bear else lv["lo"]                    # the session extreme
sw    = [b for b in ref if (b["h"] if bear else b["l"]) == ext][-1]
body  = max(sw["o"], sw["c"]) if bear else min(sw["o"], sw["c"])
swept = (body < ext) if bear else (body > ext)            # <-- vacuous
```

`ext` is the highest high **in the graded session**. `body` is the body edge of the
candle that made it. A body edge is below its own wick high unless the candle closed
exactly at its high. So `swept` is true for essentially every session, `SWEEP` is
taken every time, and `RANGE` is unreachable code.

### The real ambiguity underneath

The source defines a sweep as a candle whose wick *"pierces beyond the Session Top
or Session Bottom"* and whose body *"closes back inside the range."* But the Session
Top **is** the highest high of the session. **Nothing inside the session can pierce
beyond it.** The definition is self-referential when the sweep is read in the graded
session — which is the reading the trader signed and the diagram's "DURING SESSION"
supports.

The current code resolves this by silently weakening "pierces beyond the top" to
"body is inside the top", which is trivially satisfied. That is not an
implementation of the rule; it is the rule deleted.

### Candidate readings — none may be adopted silently

| # | Reading | RANGE reachable? |
|---|---|---|
| S1 | Sweep is of an **internal** level: prior swing high/low formed earlier in the session | yes |
| S2 | Sweep is of the **previous session's** top/bottom, breached during this one | yes |
| S3 | Sweep requires the extreme candle's **wick:body ratio** to exceed θ — a rejection test | yes, via θ |
| S4 | Sweep is of the **body-defined** range: wick beyond `max(o,c)` of all bars, body back inside | yes |
| S5 | Sweep is detected in the **execution** window (the pre-correction reading) | yes, but unknowable at the reference close — contradicts §5.3 |

**Protocol: same as FIX 3.** Sweep all five, report the distribution. If the
SWEEP/RANGE split is stable in sign across them, the fork is identified. If it is
not, the source does not determine it and the result must be published as an
interval.

**This blocks everything else.** Fixes 1–4 tune a classifier whose only fork is
currently a constant.

---

## FIX 1 — bias. **Substantially withdrawn on a trader ruling**

> ### [TRADER] RULING — 2026-08-16
> **"On this strategy the NO-TRADE branch can never fire."**
>
> There is no fourth terminal. The diagram carries three boxes — SWEEP, RANGE,
> TREND — and no NO-TRADE. Every graded session produces a plan.

### What this retracts

**`Mismatch → NO TRADE` was a second gloss.** The typed agent document states
*"Check the setup direction against BIAS TREND. Mismatch → NO TRADE"* and repeats it
in §7 as *"Bias filter is mandatory."* **That is not in the frame.** It is the same
class of error as "middle portion" — reviewer wording promoted to source. Both are
now retracted.

**Bias is a direction SELECTOR, not a veto.** With no NO-TRADE terminal it cannot
reject anything; it can only choose a side. The review's veto/selector split
therefore collapses: bias is a selector in all three buckets, which is what the
engine already does.

**The `resolved_at ≤ session.start` assertion is withdrawn as a hard-fail.** It was
specified to stop a *filter* being derived from the thing it filters. A selector is
different: the trade is placed after the graded session closes, so a statistic of
that completed session is available information, not lookahead. `verify_no_lookahead`
already covers the real constraint — nothing may be read after the reference close.

### What survives, and it is not small

**Bias is still `[UNSIGNED]`.** The diagram shows `BIAS TREND` with an up and a down
chevron and says nothing about where the value comes from. `close_location ≥ 0.50` is
an interpretation with no more standing than the retracted ones. It belongs in the
FIX 3 grid as a swept parameter, not as a fixed rule.

**The engine never runs "trade away from the swept side."** This is a genuine defect
and independent of the ruling:

```python
ext = lv["hi"] if bear else lv["lo"]     # bias picks WHICH SIDE to hunt
sw  = [b for b in ref if ... == ext][-1] # a sweep is then found there by construction
```

The source discovers direction from *which side was swept*. The engine asserts the
side first. Required shape, now with no NO-TRADE anywhere:

```
1  detect sweeps on BOTH sides independently   -> {high_swept?, low_swept?}
2  one side swept   -> direction = away from it        (source rule)
   both swept       -> the later one                   [UNSIGNED - declare it]
   neither swept    -> RANGE SETUP, side chosen by bias (bias as selector)
3  no veto, no NO-TRADE terminal                       [TRADER, 2026-08-16]
```

### Consequence for the −117.683R — it hardens

The rejection of `a6188c364c63f39f` carried a scope note: *"this version omits the
BIAS TREND filter the source mandates, so it measures an unfiltered superset."*

**That note is void.** There is no filter to omit. The engine took the number of
trades the strategy takes, and the seven bias-filter backtests measured a mechanism
the strategy does not contain — their negative results neither support nor undermine
anything.

**The main escape hatch on the rejection is closed.** −0.114R/trade over 1030 trades
is a measurement of the strategy's own trade count, not of a superset. What remains
open is FIX 0 — the bucket *composition* is still wrong, because one of the three
terminals is unreachable.

---

## FIX 2 — trail. Four decisions, plus the runner-exit conflict

Current: `partial, banked, sl = True, pr * 0.75, e` — breakeven for all three
setups. The diagram says TREND trails. Confirmed gap.

| # | Decision | Default proposed | Status |
|---|---|---|---|
| T1 | Fractal swing width `N` | 2 (a swing needs 2 bars either side) | `[UNSIGNED]` |
| T2 | Confirmation lag | a swing at `i` is known at `i+N`, **never earlier** | **structural** |
| T3 | Ratchet | monotonic — stop only moves toward profit | **structural** |
| T4 | Breakeven floor | stop never retreats past entry after the partial | `[UNSIGNED]` |

**T2 is the one that manufactures edge if it is got wrong.** A swing low at bar `i`
is not identifiable until bar `i+N` has closed. Trailing to it at bar `i` uses
information that did not exist.

```python
def trail_stop(bars, i, N, cur, long):
    j = i - N                                  # only swings confirmed by now
    if j < N: return cur
    w = bars[j-N : j+N+1]
    if long and bars[j].low  == min(b.low  for b in w): return max(cur, bars[j].low)
    if not long and bars[j].high == max(b.high for b in w): return min(cur, bars[j].high)
    return cur
```

### Runner exit — genuinely ambiguous, both go in the grid

The table says `TARGET: 5x Risk to Reward` **and** `MANAGEMENT: Close 75% at 4R and
Trail`. A trailed runner and a fixed 5R target are different exits.

- **T-cap** — runner exits at 5R or the trail, whichever first *(current behaviour, capped)*
- **T-open** — runner has no target; it exits only on the trail

**Pre-registered reading, recorded before measurement:** if TREND's edge survives
only under `T-open`, that is a finding about the interpretation, not about the
strategy, and must be reported as such.

---

## FIX 3 — the range test. The gloss is retracted

`SESSION_FLOW_V1_SPEC.md` §4-B and the agent doc carried *"open and close both sit
inside the middle portion of the range"* as though it were the diagram. **It is not
in the diagram.** The frame poses `IS RANGE SESSION?` and supplies no test.

Marked `[UNSIGNED — gloss, not source]`. My rejection of it across five bands
rejected one interpretation in favour of another, not the source, and the ledger has
been corrected to say so.

**Any single test is an undeclared free parameter on the tree's only fork.** It
silently determines which bucket every session lands in.

| # | Candidate | θ |
|---|---|---|
| R1 | efficiency ratio `|c−o| / range ≤ θ` | 0.20 … 0.50 *(incumbent, θ=0.35)* |
| R2 | open and close both within middle `θ` of range | 0.30 … 0.80 *(the retracted gloss)* |
| R3 | `|close − open| / range ≤ θ` — net travel | 0.10 … 0.50 |
| R4 | close_location within `0.5 ± θ` | 0.10 … 0.40 |
| R5 | range / ATR(n) ≤ θ — compression | 0.5 … 1.5 |
| R6 | both halves of the box visited after the first `k` bars | k = 4 … 16 |

**Protocol, pre-registered:**

```
sign stable across all six x theta   ->  IDENTIFIED. report the median.
sign flips                           ->  NOT IDENTIFIED BY THE SOURCE.
                                         publish as an interval, name the flip points.
```

---

## FIX 4 — `Sweep candle body` is a two-price object

Confirmed. Current engine:

```python
body = max(sw["o"], sw["c"]) if bear else min(sw["o"], sw["c"])
```

The body edge **nearest the swept extreme** — one of at least four readings, chosen
without declaration.

| # | Reading | Effect on entry |
|---|---|---|
| B1 | body edge toward the extreme *(current)* | worst fill, highest fill rate |
| B2 | body edge away from the extreme | best fill, lowest fill rate |
| B3 | the candle's `close` | between |
| B4 | body midpoint `(o+c)/2` | between |

This trades directly against the 456 unfilled plans already recorded: B2 improves
every fill it gets and gets fewer. Declare it, sweep it, report it.

---

## Sequencing

```
FIX 0  dead RANGE branch      <- BLOCKER. the fork is a constant until this lands.
FIX 1  bias assertion + both-sided sweep detection
FIX 2  trail (T1-T4, T-cap / T-open)
FIX 4  sweep body reading           } 3 and 4 are only measurable once 0, 1, 2 land:
FIX 3  range test grid              } bias currently shares a statistic with the
                                      classifier, and TREND's management is broken
```

The review's sequencing (3 after 1 and 2) is right and FIX 0 sits ahead of all of
it — every bucket count above is currently a measurement of unreachable code.

## Version handling

None of this amends `a6188c364c63f39f`. That version is `rejected` and its ledger
entry stands with its results. Each fix produces a **new** id, its own hypothesis
count and its own evidence, per `STRATEGY_LEDGER.md`.

**Declared parameter count after these fixes: at least 4** (sweep reading, range
test, θ, trail width) plus the runner-exit interpretation. Every one enters the
hypothesis register **before** its result is known. `data/sealed/` stays shut until
they are frozen.
