# SESSION_FLOW_V1 — Strategy Specification

Strategy ID: **`SESSION_FLOW_V1`** · Contract version: **1.0-draft** · Spec date: **2026-08-15**
Config hash: **not yet assigned**

**Source of truth: the trader's Session Trading Strategy diagram.**
Source: *Episode 18 — Asian Session Trading*, 1BullBear,
`youtube.com/watch?v=3LmDFTwG2AM`

This contract implements the diagram and nothing else. Supersedes `ASIAN_SESSION_V1`
(`2530b751134fbf6e`): every filter that contract accumulated has been removed. Evidence
gathered under it **does not transfer** — see `STRATEGY_SPEC.md` §11.

> **DRAFT — NOT EXECUTABLE.** Two decisions in §4 are unsigned. Until they are signed the
> engine must refuse to load this contract.

---

## 0. Provenance — every rule is tagged

No rule enters this contract without a source. Three tags, and only three:

| Tag | Meaning |
|---|---|
| **[DIAGRAM]** | Stated in the diagram. Not open to interpretation. |
| **[BENCHMARK]** | Not in the diagram; forced by `benchmarks/truth_source_setups.json`. |
| **[TRADER]** | Not in the diagram; stated directly by the trader and dated. |
| **[UNSIGNED]** | Diagram silent, no benchmark forces it. **Requires the trader's decision.** |

Anything the engine does that carries none of these tags is a defect.

---

## 0.0 Benchmark primacy  **[TRADER]**

Recorded 2026-08-15 on the trader's instruction.

> **The trader's worked example entries are the single source of truth. The engine must
> reproduce them. Where it does not, the strategy is refined — not the example.**

This outranks §0's provenance tags. A rule that is `[DIAGRAM]`-sourced but produces a
different entry from a confirmed example is wrong and must change.

**Scope — and it is not unlimited.** A benchmark fixes what the *strategy* must decide:
setup, direction, entry, stop, targets, and the session levels they derive from. It cannot
fix what *price* subsequently did. No rule change can make the market trade at a price it
never traded at. When a benchmark's recorded outcome is unreachable from its own recorded
entry on the trader's own data, the defect is in the benchmark record or the data — not in
the strategy — and it must be resolved before that benchmark can gate anything.

### 0.0a Status of the 2022-10-03 benchmark

`eurusd-2022-10-03-asian-to-london-short-sweep` · `USER_CONFIRMED_TRUTH` · records
`outcome: TP5_HIT, target_r: 5.0`.

**The engine reproduces the entry exactly — 10/10 fields.** Session high, low, range,
classification, setup, direction, signal time, entry, stop, both targets. There is nothing to
refine in the decision path.

**The recorded outcome is not reachable from the recorded entry.** Verified against
`data/eurusd_m15_2022_10.master.csv`, the trader's own MT5 export:

```
Asian high 0.98344   low 0.97843   range 50.1p   R = 12.525p   5R = 62.6p

a 5R short on 3 Oct required entry by ................ 08:30 UTC
the first candle to exceed the Asian high is at ...... 15:00 UTC
                                                       ---------
                                                       6h 30m too late
```

Every London bar was tested as a hypothetical short entry. Only 08:15Z and 08:30Z reach 5R,
and at those times price is 13–16 pips *below* the Asian high — no sweep of that boundary has
occurred or can occur. After the 15:00Z sweep the lowest price is 0.97881; the 5R target is
0.97716, **16.4 pips further than price went**, and the stop is taken on 4 Oct at 05:45Z.

**Therefore no refinement of the sweep rule can satisfy this benchmark.** Not the breach
depth, not the reclaim test, not the rejection-quality filter, not the entry model, not the
bias gate. The gap is not in the rules; the price series does not contain the move.

**Resolution required before this benchmark may gate the contract.** One of:

| # | Possibility | How to confirm |
|---|---|---|
| 1 | The chart is a **different date**. Only 3 Oct matches `A = 50.2` (50.1p) across the fixture, but the fixture is one instrument over 15 days. | read the date off the chart |
| 2 | The chart is a **different instrument or feed** whose 3 Oct differs materially after 09:45. | read the symbol and broker off the chart |
| 3 | **`5.0 R` is the target's label, not the realised result.** TradingView prints the R-multiple of wherever the target is dragged, filled or not. | check whether the position closed at the target or elsewhere |
| 4 | The **export is incomplete** in the London/NY portion. The Asian portion matches the chart to 0.1 pip, so any gap is after 07:00. | compare the 09:00–16:00 bars against the chart |

Until one is confirmed, `outcome` on this benchmark is **UNVERIFIED** and only its *entry*
fields are usable as a gate. The entry fields pass today.

---

## 0.1 The shape of a trading day  **[TRADER]**

Two entries per symbol per day, no more. Each runs the diagram once, against exactly one range:

```
   ASIAN  00:00-07:00        LONDON  07:00-16:00        NEW YORK  12:00-18:00
   └── builds the range ──>  entry 1 reads it
                             └── builds the range ────>  entry 2 reads it
```

**The London entry checks the Asian range and nothing else. The New York entry checks the
London range and nothing else.** Full statement in §5.

---

## 1. The decision tree  **[DIAGRAM]**

```
                       BIAS TREND   (bull / bear)
                              │
                    IS RANGE SESSION?
                    ┌─────────┴─────────┐
                  yes                   no
                    │                    │
          SWEEP DURING SESSION?          │
           ┌────────┴────────┐           │
         yes                no           │
           │                 │           │
      SWEEP SETUP      RANGE SETUP   TREND SETUP
```

Three decisions, in order:

1. **Bull or bear?**  → §4-A **[UNSIGNED]**
2. **Range or trend?**  → §4-B **[UNSIGNED]**
3. **If range: swept or not swept?**  → §2.1 **[DIAGRAM]**

---

## 2. The three setups  **[DIAGRAM]**

| | SWEEP | RANGE | TREND |
|---|---|---|---|
| **Entry** | sweep candle body | session top / bottom | middle of the range |
| **Stop loss** | 25% of range | 25% of range | 25% of range |
| **Target** | 5× risk to reward | 5× risk to reward | 5× risk to reward |
| **Management** | close 75% at session range, then breakeven | close 75% at session range, then breakeven | close 75% at 4R, then trail |

Levels, all derived from the reference session:

```
high, low               from the reference session's closed M15 bars
range   = high - low
R       = 0.25 x range          the stop distance for all three setups
midpoint = low + 0.50 x range
```

### 2.1 SWEEP — "sweep during session?"  **[DIAGRAM]**

> **CORRECTED 2026-08-15.** "During session" means the **REFERENCE** session, not the execution
> session. Earlier drafts scanned the execution window; that made the question unanswerable at
> the reference close and contradicted the desk workflow (§5.3). The trader's ruling: all three
> questions are answered from the completed reference session.

The question is whether the session's own extreme was **rejected** — did the candle that made it
close its body back inside the range?

```
bias BEAR -> examine the candle that made the session HIGH
bias BULL -> examine the candle that made the session LOW

body = max(open, close) bear / min(open, close) bull
swept  if  body < high   (bear)   /   body > low   (bull)
```

If the body sits back inside, the extreme was a wick — liquidity taken and rejected. If the body
reaches the extreme, price held there into the close and there was no rejection.

```
SWEEP    entry = that candle's body edge
         SL    = entry ± R
         TP1   = the opposite session boundary  -> close 75%, stop to breakeven
         TP2   = entry ∓ 5R
```

**Bias selects which extreme is examined** **[BENCHMARK]** — a bearish session looks at the high,
a bullish session at the low. Not stated in the diagram; required to make the question single-valued.

**Everything is fixed at the reference close.** The entry is a resting limit. Nothing is watched.

#### Verified against the golden case

```
2022-10-03  ASIAN 00:00-07:00   high 0.98344  low 0.97843  range 50.1p  R 12.525p
            bias close_loc 0.265 -> BEAR      ER 0.088 -> RANGE
            extreme made 05:45Z   O 0.98103  H 0.98344  L 0.98079  C 0.98256
            body 0.98256 < high 0.98344      -> SWEPT

            entry 0.98256   stop 0.9838125   TP1 0.97843 (3.30R)   TP2 0.9762975
            filled 08:30Z · TP1 09:30Z · TP5 09:45Z · +3.723R blended
```

The 5R target **is reached**, at 09:45Z. Under the previous execution-window reading the same day
returned −1.000R with the target missed by 16.4 pips. This reading reproduces the trader's
example; that one could not.

### 2.2 RANGE — "session top / bottom"  **[DIAGRAM]**

Range session, no sweep. A limit order at the session boundary:

```
bull bias : BUY LIMIT at the session low        bear bias : SELL LIMIT at the session high
SL  = entry ± R      TP1 = opposite boundary (exactly 4R)      TP2 = entry ∓ 5R
```

Bias picks the side  **[BENCHMARK]** — same argument as §2.1; the diagram names both boundaries
and does not say which. No rejection candle is required; the diagram shows none.

### 2.3 TREND — "middle of the range"  **[DIAGRAM]**

Trend session. A limit order at the midpoint, in the bias direction:

```
entry = midpoint      SL = entry ± R      TP1 = entry ∓ 4R  -> close 75%, then TRAIL
                                          TP2 = entry ∓ 5R
```

**If price never trades at the midpoint the order does not fill.** There is no fallback entry.
The diagram supplies none, and one must not be invented — an earlier draft of this engine added a
market fill on the execution open, which changed the fifteen-day result by +6.25R and was removed.
`REVIEW_RESPONSE.md` §2.3 had already rejected market entry.

No midpoint *zone*, no confirmation candle, no opposite-quartile cancellation. The diagram shows
a single price.

---

## 3. What was removed from `ASIAN_SESSION_V1`

Every one of these is absent from the diagram:

| Removed | What it did |
|---|---|
| `sweep_buffer` 0.02 × range | required a minimum breach depth |
| `stop_buffer` 0.02 × range | structural stop validation |
| `touch_tolerance` 0.05 × range | boundary-touch tolerance |
| `rejection_quality` 0.50 | close had to sit in the far half of its own candle |
| structural-stop rejection | refused a trade whose fixed stop sat inside the sweep wick |
| "must open inside the boundary" | excluded re-entry candles |
| midpoint zone 45–55% + confirmation | required a confirmed retracement |
| opposite-quartile cancellation | killed a trend setup after a range break |
| the `UNCERTAIN` state | a fourth outcome the diagram does not draw |

**Known cost.** The structural-stop rejection was the only rule preventing a fixed 25% stop from
sitting inside the sweep candle's own wick. `STRATEGY_SPEC.md` §7 derives that case; on
2022-10-03 the confirmed sweep now stops out at −1.000R where the previous contract had a live
trade. Removing these rules is the trader's instruction and is recorded here, not argued with.

---

## 4. Decisions required before this contract may execute

### 4-A · "BIAS TREND" — bull or bear?  **[UNSIGNED]**

The diagram shows an up arrow and a down arrow. It gives no test. Two readings, and they disagree:

| Reading | Oct 3 Asian | Matches benchmark? |
|---|---|---|
| `close_location` — closed in the upper half = bull | loc 0.265 → **BEAR** | ✅ yes |
| `sign(close − open)` | +0.4 pips → **BULL** | ❌ selects a trade the benchmark lacks |

Because bias gates the eligible sweep side (§2.1), this decides the trade, not the label.
Measured across fifteen days: `close_location` +4.500R / 24 trades · `sign` +11.500R / 23 trades.
**The engine currently defaults to `close_location`** because it is the only reading consistent
with the confirmed truth. That is a benchmark constraint, not a sign-off.

### 4-B · "IS RANGE SESSION?" — range or trend?  **[UNSIGNED]**

The diagram shows a yes/no branch and gives no test. The engine currently uses
`efficiency_ratio = |close − open| ÷ range <= 0.35`, carried over from `ASIAN_SESSION_V1`, which
never sourced it from the diagram either. Both the **formula** and the **threshold** need the
trader's decision.

Note that a competing definition exists in this repo — earlier engines used *path efficiency*
(`net ÷ Σ|bar-to-bar|`). On 2022-10-04 the two disagree: 0.561 → TREND versus 0.272 → RANGE.

### 4-C · "Trail"  **[UNSIGNED]**

The trend management cell reads *"Close 75% at 4R and Trail."* Trailing must be arithmetic before
it can be code: trail on what, evaluated on which candle, and may it ever sit worse than
breakeven. Until this is signed, the runner is held at breakeven to 5R and the ticket says so.

---

## 5. Two entries per day. Each leg reads exactly one range.  **[TRADER]**

Recorded 2026-08-15 on the trader's instruction.

```
LONDON entry     ──reads──>  the ASIAN range      and nothing else
NEW YORK entry   ──reads──>  the LONDON range     and nothing else
```

**Maximum two entries per symbol per day — one per leg.**

| | Leg 1 | Leg 2 |
|---|---|---|
| Entry is taken during | **London** | **New York** |
| The only range it reads | **Asian** | **London** |
| Reference window (UTC) | `00:00 – 07:00` | `07:00 – 12:00` |
| Execution window (UTC) | `07:00 – 16:00` | `12:00 – 18:00` |
| Reference bars (M15) | 28 | 20 |

### 5.1 What each leg may not do

- **The London entry never reads the London range.** That range is still forming while the entry
  is live; using it would be look-ahead.
- **The New York entry never reads the Asian range.** The Asian levels are leg 1's business and
  are discarded when leg 2 begins.
- **No leg reads another leg's levels, setup, direction or result.** Each leg runs the diagram
  from scratch on its own reference session.
- **Neither leg is conditional on the other.** Leg 2 runs whether or not leg 1 traded, subject
  only to the desk-level risk gates in §7.

### 5.2 Consequence for the sweep

A sweep is always a breach of **the leg's own reference range**, detected during **the leg's own
execution window**:

| Leg | Boundary swept | Detected during |
|---|---|---|
| 1 | Asian high or Asian low | London, 07:00–16:00 |
| 2 | London high or London low | New York, 12:00–18:00 |

The sweep candle therefore sits **outside** the reference session in time — it happens after the
range is locked, not while it is being built. On a chart where the reference box is drawn
projected forward, the sweep candle will appear *under* the box; on a chart where the box stops
at the session close, it will appear to the right of it. Both are the same event.

### 5.3 Desk timing — the engine runs twice a day  **[TRADER]**

Recorded 2026-08-15 on the trader's instruction.

The engine is run **at the close of each reference session**, when that session's data is
complete. It is not run continuously through the execution window.

| Run | UTC | Myanmar | Input is complete | Output |
|---|---|---|---|---|
| **1** | **07:00** | 13:30 | Asian session, 28 closed M15 bars | the **London** entry plan |
| **2** | **12:00** | 18:30 | London session, 20 closed M15 bars | the **New York** entry plan |

At each run the reference range is final and immutable. The engine produces one plan — bias,
classification, setup, entry, stop, TP1, TP2 — and the trader places the order for the execution
session that follows.

### 5.3a Open question — when is a SWEEP entry knowable?  **[UNSIGNED]**

Two of the three setups are fully determined the moment the reference session closes, because
their entry is a level derived from the completed range:

| Setup | Entry | Known at the reference close? |
|---|---|---|
| RANGE | session top / bottom | **yes** — place the limit immediately |
| TREND | midpoint | **yes** — place the limit immediately |
| **SWEEP** | **sweep candle body** | **no** — see below |

A sweep is a breach of the reference boundary that closes back inside (§2.1). Under §5.2 that
breach happens during the **execution** window, so the sweep candle does not exist yet at the
reference close. Its body — and therefore the entry, the stop and both targets — cannot be
computed at run time.

**This is confirmed against the benchmark, not assumed.** For 2022-10-03:

```
Asian high 0.98344, made by the 05:45Z candle   O 0.98103  C 0.98256  -> body high 0.98256
confirmed-truth entry                                                     0.98342
  = body high of the 15:15Z candle — a LONDON candle, eight hours after the Asian close
```

The confirmed entry is not the body of any Asian candle. So a single 07:00 run cannot produce it.

Three ways to resolve this; the trader decides:

1. **Two-part run.** 07:00 produces the plan and the RANGE/TREND limit. If the session is RANGE,
   the desk then watches for a sweep during London and takes the sweep entry when it prints,
   superseding the range limit. The engine runs once; the sweep is a monitored trigger.
2. **Re-run on sweep.** The engine is re-run when a candle closes back inside the boundary, to
   compute the sweep ticket. More than two runs per day, but every ticket is engine-produced.
3. **Sweep is read inside the reference session.** "SWEEP DURING SESSION" refers to the reference
   session — the session's extreme was made by a candle that closed back inside, and that
   candle's body is the entry. Fully knowable at 07:00. **This contradicts the 2022-10-03
   benchmark**, whose entry is a London candle, so it cannot be adopted without re-deriving the
   benchmarks.

Until this is signed, `scripts/run_flowchart.py` scans the execution window for the sweep, which
matches the benchmark but not a strict two-runs-a-day desk.

### 5.4 Window provenance

The three-decision logic and the setups are **[DIAGRAM]**. The clock is not: session boundaries
and candle counts are operational configuration. Leg 1's `00:00–07:00 / 28 bars` was determined
empirically — only that window reproduces the confirmed-truth levels for 2022-10-03
(`STRATEGY_SPEC.md` §10). Leg 2's `07:00–12:00 / 20 bars` is carried from the trader's earlier
`SESSION_TRADING_SOURCE_WORKFLOW_V2` and is **[UNSIGNED]**.

---

## 6. Measured behaviour — EURUSD, 3–21 Oct 2022

Fixture `data/eurusd_m15_2022_10_utc.csv` (`sha256[:16] 658199e50c2846b8`), 15 weekdays,
2 legs = 30 leg-runs. Runner: `scripts/run_flowchart.py`.

```
24/30 leg-runs produced an entry (80%)      net +4.500R      mean +0.188R/trade
```

Oct 3–5 in detail:

| Date | Leg | Bias | Session | Setup | Dir | Entry | Stop | TP1 | TP2 | R |
|---|---|---|---|---|---|---|---|---|---|---|
| Oct 3 | A→L | BEAR | RANGE | SWEEP | SHORT | 0.98342 | 0.98467 | 0.97843 | 0.97716 | −1.000 |
| Oct 3 | L→NY | BEAR | TREND | TREND | SHORT | 0.97900 | 0.98086 | 0.97153 | 0.96966 | −1.000 |
| Oct 4 | A→L | BULL | TREND | — | | | | | | unfilled |
| Oct 4 | L→NY | BULL | TREND | — | | | | | | unfilled |
| Oct 5 | A→L | BULL | RANGE | RANGE | LONG | 0.99592 | 0.99503 | 0.99949 | 1.00038 | −1.000 |
| Oct 5 | L→NY | BEAR | TREND | — | | | | | | unfilled |

**These fifteen days are in-sample.** Every threshold in this repo was chosen while looking at
them. The figure is a shape check, not evidence. Nothing here has passed Stage 2.

---

## 7. Operational gates — unchanged, not strategy

Data integrity, demo-account environment, spread, volume bounds, daily risk, drawdown and the
execution window remain as `ASIAN_SESSION_V1` §2 defines them. They decide whether a signal may
be *acted on*, never what the signal is. The diagram governs the strategy; these govern the desk.

---

Analysis only. Levels are proposals, not automated signals. Verify every value against your own
chart before placing or managing an order manually. Passing every gate means the configured rules
passed — nothing more.
