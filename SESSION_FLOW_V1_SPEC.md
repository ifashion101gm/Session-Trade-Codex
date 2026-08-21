# SESSION_FLOW_V1 — Strategy Specification

Strategy ID: **`SESSION_FLOW_V1`** · Contract version: **1.0-draft** · Spec date: **2026-08-15**
Config hash: **not yet assigned**

**Source of truth: the trader's Session Trading Strategy diagram.**
Source: *Episode 18 — Asian Session Trading*, 1BullBear,
`youtube.com/watch?v=3LmDFTwG2AM`

This contract implements the diagram and nothing else. Supersedes `ASIAN_SESSION_V1`
(`2530b751134fbf6e`): every filter that contract accumulated has been removed. Evidence
gathered under it **does not transfer** — see `STRATEGY_SPEC.md` §11.

> **DRAFT — NOT EXECUTABLE.** **Three** decisions in §4 are unsigned (4-A, 4-B, 4-C), plus
> §5.3a and §5.5. Until they are signed the engine must refuse to load this contract.
>
> **The active engine is additionally BLOCKED on `ENGINE_FIX_SPEC.md` FIX 0** — the sweep
> test is vacuous, so `RANGE SETUP` is unreachable (0 of 1030 trades). Version
> `a6188c364c63f39f` is **rejected**; see `STRATEGY_LEDGER.md`.

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

### 0.0a-i Timezone-offset hypothesis — TESTED AND REFUTED  **2026-08-16**

A review proposed that the `-1.000R` log was an artifact: *"broker time misinterpreted
as pure UTC, shifting London bars to 15:00 UTC"*, and that the sweep really occurred
at the London open. Three checkable claims, all tested against
`data/eurusd_m15_2022_10.master.csv`:

**1 · The offset is already correct, and the review's own test proves it.**
It recommends *"ensure the Asian window lines up exactly with the blue box (A = 50.2)."*
It does: **50.1p measured against 50.2p annotated.** A wrong offset would move the box.
The match is the proof.

**2 · "36-bar Asian construction window (00:00–07:00 UTC)" is arithmetically impossible.**
00:00–07:00 at M15 is **28 bars**. 36 bars is 9 hours — the **superseded 22:00–07:00
window**. The review is reasoning from a retired spec.

**3 · There is no sweep at the London open.**

```
London opens 07:00Z at 0.97979  —  36.5 pips BELOW the Asian high 0.98344
price then FALLS: 09:45Z low 0.97526
first bar whose high exceeds the Asian high:  15:00Z   (0.98369)
```

No bar between 07:00 and 15:00 trades above 0.98344. A sweep of that boundary at the
London open did not occur on this series.

**Conclusion.** The chart being described is not this date, instrument or feed —
§0.0a possibilities 1 and 2 remain live and are now the *likeliest* explanations. The
benchmark's status is **unchanged**: `outcome` UNVERIFIED.

**It has NOT been upgraded to VERIFIED TRUTH.** Upgrading a benchmark on the strength
of a diagnosis the data refutes is the precise failure §0.0a exists to prevent.

**Note on §0.0b.** This does not disturb the case for Reading C, which rests on
**benchmark #2** (`london-to-new-york`, 14:15Z NY bar, setup + entry + outcome all
reproduced only under the execution-window reading). That evidence is independent of
benchmark #1.

---

### 0.0a-ii The chart image, read structurally — it favours Reading A  **2026-08-16**

The chart was supplied. It shows a tall candle piercing the box top and closing back
inside, at the box's **right edge**, with a yellow stop band above it and a large
target box below.

**Where the entry sits relative to the box is the discriminator, and it does not need
legible digits:**

```
box top (Asian high)          0.98344
Reading A entry               0.98256   17.6% of the range BELOW the top  -> visibly inside
benchmark record entry        0.98342    0.4% below the top               -> would sit ON the line
```

On the image the `Open PNL` label sits clearly **inside** the box, well below its top
edge. That is Reading A's geometry, not the recorded `0.98342`.

**Two further consistencies with Reading A:**

- the stop band is drawn **above the spike's wick** — Reading A's stop is `0.98381`,
  above the 0.98344 high
- the trade is shown **in profit, heading down toward the target**. Reading A replays
  as **+3.723R** (TP1 at 09:30Z, 5R at 09:45Z). The execution-window reading replays
  as **−1R**. A winning chart is consistent with Reading A and not with the alternative.

**Which candle is it?** The 05:45Z bar — `O 0.98103  H 0.98344  L 0.98079  C 0.98256`.
A tall candle with an upper wick closing back down. It sits at the right edge of the
box, exactly where the image shows it.

**The unresolved wrinkle.** Under a 00:00–07:00 box the 05:45 candle *makes* the high,
so it cannot pierce it — yet the image shows the spike above the box line. Only a box
ending at **05:45** makes it a genuine pierce, and that box measures **44.1p**, not the
annotated 50.2. Either the box top is drawn at the body/close rather than the wick, or
the rendering gap is smaller than it appears.

**Label arithmetic does not close either.** `R:R 5.15` with a `61.8` pip target implies
R = 12.0p and a 48.0p range — matching neither 50.2 nor 44.1. Pixel-level reading of
five-decimal prices at this resolution is not reliable and no field is being changed on
it.

**Status unchanged — `outcome` remains UNVERIFIED.** But the balance has shifted: the
image is *more* consistent with the current §2.1 reference-session reading than with
the execution-window reading it was offered to support. **Benchmark #2 is unaffected**
and remains the only non-circular evidence in §0.0b.

---

### 0.0a-ii The chart image, read structurally — it favours Reading A  **2026-08-16**

The chart was supplied. It shows a tall candle piercing the box top and closing back
inside at the box's **right edge**, a yellow stop band above it, and a large target
box below.

**Where the entry sits relative to the box is the discriminator, and it needs no
legible digits:**

```
box top (Asian high)     0.98344
Reading A entry          0.98256   17.6% of the range BELOW the top -> visibly inside
benchmark record entry   0.98342    0.4% below the top              -> would sit ON the line
```

On the image the `Open PNL` label sits clearly **inside** the box, well below its top
edge. That is Reading A's geometry, not the recorded `0.98342`.

**Two further consistencies with Reading A:**

- the stop band is drawn **above the spike's wick** — Reading A's stop is `0.98381`,
  above the 0.98344 high
- the trade is shown **in profit, heading toward the target**. Reading A replays as
  **+3.723R** (TP1 09:30Z, 5R 09:45Z); the execution-window reading replays as
  **−1R**. A winning chart is consistent with A and not with the alternative.

**The candle is the 05:45Z bar** — `O 0.98103  H 0.98344  L 0.98079  C 0.98256`. Tall,
upper wick, closes back down, sitting at the right edge of the box exactly where the
image shows it.

**Unresolved wrinkle.** Under a 00:00–07:00 box the 05:45 candle *makes* the high, so
it cannot pierce it — yet the image shows the spike above the box line. Only a box
ending at **05:45** makes it a true pierce, and that box measures **44.1p**, not the
annotated 50.2. Either the box top is drawn at the body rather than the wick, or the
rendering gap is smaller than it looks.

**Label arithmetic does not close either.** `R:R 5.15` with a `61.8`-pip target implies
R = 12.0p and a 48.0p range — matching neither 50.2 nor 44.1. Five-decimal prices are
not reliably readable at this resolution and no field is being changed on them.

**Status unchanged — `outcome` remains UNVERIFIED.** But the balance has shifted: the
image is *more* consistent with the current §2.1 reference-session reading than with
the execution-window reading it was offered to support. **Benchmark #2 is unaffected**
and remains the only non-circular evidence in §0.0b.

---

### 0.0b-R RESOLVED — Reading A confirmed by the trader  **2026-08-17**

The trader supplied the Oct-3 London chart from the source video and stated:
**"this entry is same, no need to refine."**

```
engine (Reading A, 05:45Z Asian candle body)   0.98256   17.6% of range below the box top
record (Reading B/C, 15:15Z London candle)     0.98342    0.4% below the top -> ON the line
```

On the chart the `Open PNL` label sits **clearly inside the box**, well below its top
edge. That is Reading A's geometry. Combined with the trader's statement, **§2.1
stands as written: the sweep is read in the REFERENCE session.**

**The chart's own labels also resolve §0.0a.** `Risk/Reward Ratio 5.15` with a `64.0`
pip target implies R = 12.43p against the contract's 12.525p, putting the target
1.4 pips **beyond** 5R:

```
contract 5R  62.6 pips        chart target  64.0 pips = 5.11R
```

A dragged-target artifact, not a rule difference — which is §0.0a **possibility #3**,
*"5.0 R is the target's label, not the realised result"*, now confirmed. The recorded
`+5R` means **the target was reached**; the realised blended figure is `+3.723R`
because 75% banks earlier at the opposite boundary. Both are correct descriptions of
the same trade.

**Consequences**

- §2.1 reference-session sweep: **confirmed**, no change
- §5.3 twice-daily static desk: **retained** — Reading A requires no intraday watching
- `benchmarks/truth_source_setups.json` entry `0.98342` is **superseded**; it was
  engine-reproduced under the pre-correction contract, never trader-confirmed
- §0.0a `outcome` status upgrades from UNVERIFIED to **VERIFIED — target reached**

**Benchmark #2 — resolved the same day, and it overturns the record.** The trader
supplied the Oct-3 **New York** chart and states: **TREND setup, SHORT, result a miss.**

```
                        setup   dir     entry      result
TRADER (video)          TREND   SHORT   —          miss
ENGINE (Reading A)      TREND   SHORT   0.97900    STOP -1.000R
old benchmark record    SWEEP   SHORT   0.98181    STOP_LOSS
```

The engine matches the trader on setup and direction. **The stored record does not** —
it says SWEEP where the trader says TREND. Like benchmark #1, its entry was
engine-reproduced under the pre-correction contract and was never trader-confirmed.

**`truth_source_setups.json` benchmark #2 is SUPERSEDED.** Per its own schema rule —
*"source/feed disagreement must be retained, never overwritten"* — the old row stays
with a superseded flag rather than being edited.

**§0.0b is therefore fully closed. Reading A matches the trader on BOTH Oct-3 legs.**
§2.1 (reference-session sweep) and §5.3 (twice-daily static desk) both stand. No
refinement required.

### Conformance scope  **[TRADER] — 2026-08-17**

> *"The engine only needs to calculate and produce trend (from range or trend),
> short (up trend or down trend)."*

**Conformance against the source video is scored on the CLASSIFICATION, not on price
levels:**

| Scored | Not scored |
|---|---|
| range-or-trend (§4-B) | entry / stop / target prices |
| bull-or-bear direction (§4-A) | fill timing |
| swept-or-not, when range (§2.1) | realised R |

Prices remain derived quantities — `entry` follows from the setup, `stop` is 25% of
range, `target` is 5R — so a correct classification determines them. A price mismatch
with a correct classification is a feed or reading difference, not a rule defect.

---

### 0.0b UNRESOLVED — three [TRADER] rulings that cannot all hold  **2026-08-16**
> **Superseded 2026-08-17 for benchmark #1 — see §0.0b-R above.** Retained because
> benchmark #2 remains unexplained under the confirmed reading.


An architectural review re-opened the sweep reading. The conflict is real and only the
trader can settle it.

| | Ruling | Tag |
|---|---|---|
| **§0.0** | the benchmark is truth; refine the strategy to match it | `[TRADER]` |
| **§2.1** | the sweep is read in the **reference** session | `[TRADER]` 2026-08-15 |
| **§5.3** | the engine runs **twice a day**, never continuously | `[TRADER]` |

**They are mutually inconsistent on the 2022-10-03 benchmark.** Its confirmed entry
`0.98342` is the body of the **15:15Z candle — a London bar**. Under §2.1 the engine
reads the Asian session and returns `0.98256`, from the 05:45Z bar:

```
benchmark entry (15:15Z LONDON body)   0.98342
corrected engine (05:45Z ASIAN body)   0.98256
gap                                       8.6 pips
```

**§0.0a is stale.** Its claim that *"the engine reproduces the entry exactly — 10/10
fields"* was written about the **pre-correction** contract. Under §2.1 as corrected,
the entry field does **not** reproduce. §0.0 is therefore violated by §2.1.

### This is also the root of FIX 0

`ENGINE_FIX_SPEC.md` FIX 0 records that `RANGE SETUP` is unreachable because
`swept = body < session_high` is trivially true. **That is not a coding defect. It is
what the §2.1 reading forces.** The Session Top *is* the session's highest high, so
nothing inside the session can pierce beyond it — the sweep test is self-referential
by construction, and any implementation of it degenerates.

Under an execution-window reading the test is well-posed: London price can genuinely
pierce the Asian high and close back inside, and a session where that never happens
stays `RANGE`. **The dead branch and the sweep reading are one question, not two.**

### Options — not to be resolved by the engine

| | Reading | Keeps | Breaks |
|---|---|---|---|
| **A** | reference-session sweep *(current)* | §2.1, §5.3 | §0.0; `RANGE` unreachable |
| **B** | execution-window sweep *(pre-correction)* | §0.0, `RANGE` live | §5.3 — requires watching |
| **C** | **hybrid**: freeze RANGE/TREND limits at the reference close; monitor only for SWEEP during execution | §0.0, `RANGE` live | §5.3 partially — one watched condition |

**Do not adopt B or C on the strength of the benchmark alone.** §0.0a already records
that this benchmark's **`outcome` is UNVERIFIED** — its 5R is unreachable from its own
entry, with four unresolved explanations including *wrong date*, *different feed*, and
*"5.0 R is the target's label, not the realised result."* A workflow change justified
by a record that may itself be mislabelled would repeat the error §0.0a exists to
prevent.

**Sequence: confirm the benchmark first, then choose the reading.**

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

> ### [TRADER] RULING — 2026-08-16 · there is no NO-TRADE terminal
>
> **"On this strategy the NO-TRADE branch can never fire."**
>
> The tree has exactly three terminal boxes and no fourth. **Every graded session
> produces a plan.** `BIAS TREND` is therefore a direction **selector**, never a veto.
>
> **Retracted with this ruling:** the agent document's *"Mismatch → NO TRADE"* and
> its §7 *"Bias filter is mandatory."* Neither is in the frame. Same class of error
> as the "middle portion" gloss in §4-B — reviewer wording promoted to source.
>
> **Consequence.** The 12-month result (1030 trades, −0.114R/trade) was recorded with
> a scope note saying it measured an unfiltered superset. **That note is void** —
> there is no filter to omit, and the engine took the trade count the strategy takes.

Three decisions, in order:

1. **Bull or bear?**  → §4-A **[UNSIGNED]** — selector only, per the ruling above
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

### 2.4 A swept range session terminates at SWEEP, never RANGE  **[TRADER] — signed 2026-08-16**

Query raised: on `RANGE?=YES` + `SWEEP?=YES`, is the entry the sweep candle body or
the session top/bottom?

**Answer: the sweep candle body — SWEEP SETUP.** Confirmed against the video
walkthrough. It matches the frame: `SWEEP DURING SESSION?` sits under the YES arm of
`IS RANGE SESSION?`, and its own YES arm drops into `SWEEP SETUP`.

**Consequence: `RANGE SETUP` fires only on a range session with NO sweep.**

This is a **signed rule, not a parameter** — it does not enter the sensitivity grid.

**The engine already implements this branch order correctly** (`session_flow.py:79-93`).
The defect is not the tree; it is the sweep *test* that feeds it — see
`ENGINE_FIX_SPEC.md` FIX 0.

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

### 4-B · "IS RANGE SESSION?" — range or trend?  **[UNSIGNED — the diagram supplies NO test]**

> **RETRACTION, 2026-08-16.** Earlier drafts of this section and of the agent
> document carried *"open and close both sit inside the middle portion of the
> range"* as though it came from the source. **It does not.** The flowchart poses
> `IS RANGE SESSION?` and gives no definition at all. That wording was a gloss
> written by a reviewer and then treated as source — exactly the drift the
> provenance tags exist to stop.
>
> Consequence: the efficiency ratio is an interpretation, and so is the gloss.
> Rejecting the gloss across five bands rejected one interpretation in favour of
> another, not the source. **Any single test is an undeclared free parameter
> sitting on the tree's only fork**, silently deciding which bucket every session
> lands in. See `ENGINE_FIX_SPEC.md` FIX 3 for the six-candidate grid and the
> pre-registered identified / not-identified protocol.

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

### 5.5 OPEN — the reference window may end at 06:00, not 07:00  **[UNSIGNED]**

Recorded 2026-08-15 from two trader charts.

| Chart | Annotation | Engine @ 07:00 end | Engine @ 06:00 end |
|---|---|---|---|
| 2022-10-03 | `A = 50.2` | 50.1p ✅ | 50.1p ✅ |
| 2022-10-04 | `A = 43.2` | **66.0p ❌** | **43.0p ✅** |

An exhaustive window search confirms this is the end time, not the start: **every** window
ending at 06:00 gives Oct 3 = 50.1p and Oct 4 = 43.0p; **every** window ending at 07:00 gives
Oct 4 = 66.0p. The start time cannot be determined from these two days, because both
extremes fall inside 02:00–06:00.

**Consequences if adopted.** On 2022-10-04 the whole plan changes:

```
00:00-07:00   H 0.98720  L 0.98060  66.0p   ER 0.561 -> TREND    TREND LONG  @ 0.98390
00:00-06:00   H 0.98490  L 0.98060  43.0p   ER 0.242 -> RANGE    SWEEP LONG  @ 0.98099
```

Different range, different classification, different setup, different entry. Oct 3 is
unaffected — its extremes are made before 06:00, so both windows give the same levels, which
is why the original correction to 00:00–07:00 was not caught by the golden case.

**Not adopted yet. Two open problems:**

1. **The residual.** 43.0 vs 43.2 and 50.1 vs 50.2 are each 0.1–0.2 pip out. That is within
   plausible feed difference, but it is not an exact match, and two data points is thin.
2. **The chart appears filled; the engine says UNFILLED under both windows.** A buy limit at
   0.98099 (06:00 reading) or 0.98390 (07:00 reading) is never reached — London's low is
   0.98527. Neither window explains a filled long on 2022-10-04.

**Resolution needs a third chart** with a legible reference range, ideally on a day whose
06:00 and 07:00 ranges differ. Until then the contract stays on `00:00–07:00 / 28 bars` and
this section records the discrepancy rather than acting on it.

### 5.3b Leg-2 reference window — **SIGNED 2026-08-16** · `07:00–12:00 / 20 bars` · **[BENCHMARK]**

Previously carried from `SESSION_TRADING_SOURCE_WORKFLOW_V2` by inheritance and marked
**[UNSIGNED]**. It is now signed on benchmark evidence and promoted from `[UNSIGNED]` to
`[BENCHMARK]`.

**The evidence.** The 2022-10-06 trader chart (`benchmarks/SOURCE_ENTRIES.md` #19) carries
`Target 0.98544` with its own `34.8` pip distance label, implying an entry of `0.98892`.
Every candidate leg-2 window from 05:00–12:00 through 11:00–14:00 was scored against it:

```
  06:00-13:00   28 bars   67.2p   TREND SHORT   0.98892   0.00 pip
  07:00-12:00   20 bars   62.7p   TREND SHORT   0.98894   0.15 pip
  07:00-13:00   24 bars   65.1p   TREND SHORT   0.98881   1.05 pip
  06:00-12:00   24 bars   64.8p   TREND SHORT   0.98904   1.20 pip
  08:00-12:00   16 bars   55.1p   TREND SHORT   0.98856   3.65 pip
  09:00-12:00   12 bars   44.6p   TREND SHORT   0.98803   8.90 pip
```

Only two windows land inside one pip. **`07:00–12:00` is chosen over `06:00–13:00`** on two
grounds that outrank a 0.15-pip residual:

1. **`06:00–13:00` overlaps leg 1.** The leg-1 reference is `00:00–07:00`, confirmed
   independently by two benchmarks — Oct 3 (`A = 50.2` vs 50.1p) and Oct 6 (`A = 33.3` vs
   33.3p). A leg-2 reference starting at 06:00 would re-consume an hour already inside leg 1's
   locked range, which no reading of the diagram supports.
2. **`06:00–13:00` moves the desk clock.** §5.3 is **[TRADER]**-signed: run 2 is at **12:00
   UTC**. A window closing at 13:00 would put the run an hour later and contradict a
   higher-provenance rule.

A 0.15-pip residual is well inside the resolution at which the chart label was read. The
0.00-pip fit of `06:00–13:00` is recorded as the runner-up, not discarded — if a future
benchmark separates them, this decision is re-openable at a version bump.

**What this does NOT resolve.** The same Oct-6 chart implies a stop of roughly **7.0 pips**,
where `stop = 25% of range` gives **15.7p** on this window — and **16.8p** on the runner-up.
The window is therefore *not* the cause of the stop discrepancy. That belongs to the sizing
rule and is tracked separately; see §4-C and the note on #19.

### 5.6 Ticket guidance — place promptly  **[TRADER] — 2026-08-17**

**This is ticket content, not engine behaviour.** The system produces a ticket; the
trader places the order. Nothing here changes what the engine computes.

Every ticket carries a placement recommendation:

```
PLACEMENT     : place this order as soon as possible after the reference close.
                The plan is complete at 07:00 / 12:00 UTC — waiting for
                confirmation, a retest, or a second signal is not part of the
                strategy and costs fills.
```

**What it is not.** It is not an instruction to enter at market. The order price is
the setup's own level from §2 — sweep candle body, session boundary, or midpoint —
and it rests there until filled or until the execution window closes.

Measured on the Oct-2022 fixture, why prompt placement matters:

```
price already beyond the entry when the order is placed   0 of 30
fills on the very first bar                               7 of 30   23%
fills within one hour                                    11 of 30   37%
never fills                                               6 of 30   20%
```

Nothing is ever missed by being *late* to a level price has already passed — that
case does not occur. But 23% fill on the first bar of the execution session, so a
ticket acted on late loses those outright.

Unfilled at the window close is `EXPIRED_UNFILLED` — a **miss**, not a skip, and not
a NO-TRADE (§1 ruling).

### 5.4 Window provenance

The three-decision logic and the setups are **[DIAGRAM]**. The clock is not: session boundaries
and candle counts are operational configuration. Leg 1's `00:00–07:00 / 28 bars` was determined
empirically — only that window reproduces the confirmed-truth levels for 2022-10-03
(`STRATEGY_SPEC.md` §10). Leg 2's `07:00–12:00 / 20 bars` is **signed as of 2026-08-16**; see
§5.3b.

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
