# Roadmap — from here to a verdict

**Written 2026-08-15.** Current state is in `STATUS.md`. This file is the sequence, and
the order matters more than the individual steps.

---

## Where the project actually is

The two-stage structure from `PROJECT_CHARTER.md` still governs:

```
STAGE 1  does the tool apply the rules correctly?   ->  7 of 8 criteria met
   |                                                    S1.5 not started
   v
DAY TRADING begins
   |
   v
STAGE 2  does the strategy have an edge?            ->  3 of 4 thresholds met
                                                        n too small, CI spans zero
```

**Both stages are one short step from closing, and neither can close yet.**

| | Blocker | Cost to clear |
|---|---|---|
| Stage 1 | S1.5 — 20 hand-reconciled tickets, zero discrepancies | ~2 weeks of live running |
| Stage 2 | n=63, CI `[-0.149, +1.010]`; max drawdown 11.071R > 10R limit | ~1 more month of history |

---

## The rule that orders everything below

> **Sign the open decisions before collecting more evidence.**

Four decisions in `SESSION_FLOW_V1_SPEC.md` §4 and §5.3a are unsigned. Every number
produced from here inherits whichever reading is left in place. If they are signed *after*
seeing more results, the project repeats exactly the failure that produced nine
contradictory folders in `outputs/` — and `§1.1`'s predeclared research grid exists to
prevent it.

**This is step 1, and it costs an hour.**

---

## Step 1 — Sign the four decisions

| # | Decision | Recommended | Why |
|---|---|---|---|
| **§4-A** | "BIAS TREND" | `close_location >= 0.50` | The only reading consistent with the confirmed 2022-10-03 benchmark. `sign(close − open)` selects a trade the benchmark does not contain. |
| **§4-B** | "IS RANGE SESSION?" | `efficiency_ratio <= 0.35` | Now measured across three symbols: 0.25→0.45 gives +0.418 / +0.281 / **+0.431** / +0.415 / +0.281. Flat enough that the choice is not load-bearing — which is the argument for freezing it, not for tuning it. |
| **§4-C** | "Trail" | defer — keep the runner at breakeven to 5R | Undefined in the diagram. Deferring is honest; inventing a trail rule is not. Record it as deferred, not as decided. |
| **§5.3a** | Leg 2 reference window | `07:00–12:00` | Inherited from the trader's own prior V2 workflow. Now supported: leg 2 nets +7.525R across three symbols on this window. |

Record each in the spec with a date and a `[TRADER]` tag. Then **do not change them** until
a version bump, per `STRATEGY_SPEC.md` §11.

---

## Step 2 — Close Stage 1 (conformance)

Only S1.5 remains: **20 tickets reconciled by hand against MT5, zero discrepancies.**

Two things must hold first, and both are now true:

- the config is frozen — `00:00-07:00 / 28 bars` corrected 2026-08-15
- the rules are signed — step 1

Then run the desk properly:

```powershell
python scripts/engine_report.py --date <today>        # 07:00 UTC and 12:00 UTC
```

For each accepted plan: open the chart, verify the six values, record the match. Twenty
clean reconciliations under one unchanged config hash closes Stage 1.

**Expect this to take two to three weeks** — 80% of plans fill, two legs a day, but only
some produce a checkable ticket.

**Add first:** a falsifiability test per gate. `STAGE1_QUALIFICATION.md` S1.2 is marked ✅
on the strength of one gate. Every gate needs an input that makes it **FAIL**, or it is not
a gate. This is the cheapest remaining work in the project and it is the layer that catches
interlocks that never fire.

---

## Step 3 — Reach a Stage 2 verdict

### 3a · Sample

```
have    63 trades   3 symbols x 15 days
need   ~114 trades  for the 95% CI to exclude zero at +0.431R and sd 2.346
```

| Action | Adds | Running total |
|---|---|---|
| XAUUSD (`XAUUSD.crp`) Oct 2022 | ~20 | ~83 |
| All four symbols, one more month | ~85 | ~168 |

**Export a second month — and do not look at it yet.** See 3c.

### 3b · Resolve the drawdown breach

`max drawdown 11.071R` against a 10R limit is the only failing Stage-2 threshold. It is a
new failure — 4.063R on EURUSD alone — so it grew with the sample and may keep growing.

Three legitimate responses, in order of preference:

1. **Measure it properly first.** Drawdown on a pooled, unordered trade list is not the
   drawdown a trader experiences. Recompute chronologically, with the two legs and all
   symbols interleaved as they actually occurred.
2. **Accept and document** if the true figure sits near the limit — the threshold was set
   before any evidence existed.
3. **Change the threshold** only as a deliberate, dated amendment to `config/lifecycle.json`,
   never quietly.

**Do not respond by adding a filter.** That is a new strategy version and restarts everything.

### 3c · Hold back an out-of-sample period

Everything so far — all 63 trades — is in-sample. The thresholds were chosen while looking
at these fifteen days.

```
DEVELOPMENT   Oct 2022         signed rules, all tuning, all inspection
SEALED        a later month    exported, never opened until step 1 is signed
```

Export it, build it, **and do not run the backtest on it** until the rules are frozen. That
single act of restraint is worth more than any additional in-sample result.

### 3d · Run the battery

`.claude/skills/robustness-validation` is installed in this repo. The tests that apply now
and need no new data:

| Test | Purpose |
|---|---|
| #3 parameter surface | already partly done — the ER sweep. Extend to the buffers. |
| #8 leave-one-out | done for symbols; repeat by date and by setup |
| #10 multiple testing | **disclose that nine variants preceded this one** |
| #6 cost stress | done — robust to 2 pips |
| #11 data variants | the EIGHTCAP/VT question, still unrecorded on the benchmarks |

Finish with the skill's three-way verdict: **Rejected · Needs more evidence · Research
candidate.** Today it is the third.

---

## Step 4 — Only then, live

`PROJECT_CHARTER.md` §5.2 is explicit and worth re-reading before this point:

> Day trading before Stage 2 means trading a strategy whose edge has not yet been measured.
> That is the trader's decision to make; this document records it so it is a choice rather
> than an oversight.

If day trading starts before Stage 2 returns a verdict, that is a legitimate choice — but
record it as one, keep it on demo, and let the journal accumulate forward evidence in
parallel.

---

## Housekeeping — small, cheap, do them whenever

- **Delete or fix `test_source_v1.py::test_literal_midpoint_trend_entry_and_stop`.** One red
  test in a 127-test suite trains you to ignore red.
- **Stamp the feed on every benchmark.** `truth_source_setups.json` has no `source` field;
  the chart appears to be EIGHTCAP, the fixture is VT Markets.
- **Push to a remote.** `.git` inside OneDrive is one sync conflict from losing the history.
- **Re-confirm the 2022-10-03 benchmark `outcome`.** It was unreachable under the old
  contract; under the corrected one the 5R target *is* hit. It may now simply be correct.

---

## What would make this fail honestly

Worth naming in advance, so it is recognisable:

- **The sealed month comes back negative.** Then the answer is Rejected, and the fifteen
  days were noise. This is the most likely single outcome and the whole point of sealing it.
- **The drawdown keeps growing with n.** A strategy with 29% win rate and a 5R target has
  long losing runs by construction; the limit may be unreachable rather than the strategy
  unviable.
- **Live fills diverge from the backtest.** All entries are resting limits, so partial fills
  and gaps matter. S1.5's twenty reconciliations are what surface this.

A documented "no" produced cheaply is a good outcome. `PROJECT_CHARTER.md` §5.4 already says
so.

---

## Sequence, compressed

```
1  sign §4-A, §4-B, §4-C, §5.3a                          ~1 hour     ← do this first
2  falsifiability test per gate                          ~1 day
3  export XAUUSD Oct 2022, rerun pooled                  ~30 min
4  export a second month, SEAL IT                        ~30 min
5  recompute drawdown chronologically                    ~1 hour
6  run the desk daily, collect 20 reconciliations        2-3 weeks
7  Stage 1 closes
8  open the sealed month, run the battery                ~1 day
9  Stage 2 verdict: Rejected / Needs evidence / Candidate
```

Steps 1–5 are a day's work and unblock everything. Step 6 is the calendar cost and cannot
be shortened.
