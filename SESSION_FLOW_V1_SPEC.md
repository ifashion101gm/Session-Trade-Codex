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
| **[UNSIGNED]** | Diagram silent, no benchmark forces it. **Requires the trader's decision.** |

Anything the engine does that carries none of these tags is a defect.

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

A sweep is a breach of a session boundary that closes back inside:

```
short : candle.high > high  and  candle.close < high
long  : candle.low  < low   and  candle.close > low

entry = sweep candle body  =  max(open, close) short / min(open, close) long
SL    = entry ± R
TP1   = the opposite session boundary   -> close 75%, stop to breakeven
TP2   = entry ∓ 5R
```

No minimum breach depth, no rejection-quality test, no requirement that the candle opened
inside, and no structural check on the stop. The diagram states none of these.

**Bias gates the eligible side.**  **[BENCHMARK]** — a bearish session may only sell a sweep of
the high; a bullish session may only buy a sweep of the low. This is not in the diagram. It is
forced by `eurusd-2022-10-03-asian-to-london-short-sweep`: on that session a long sweep of the
low qualifies at 14:00Z, an hour before the confirmed 15:15Z short. Without the bias gate the
engine returns a trade the trader's own confirmed truth does not contain.

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

## 5. Sessions and legs

The diagram is written for one reference session feeding one execution session. The project runs
two legs:

```
LEG 1   reference ASIAN  00:00-07:00 UTC   ->  execution LONDON   07:00-16:00 UTC
LEG 2   reference LONDON 07:00-12:00 UTC   ->  execution NEW YORK 12:00-18:00 UTC
```

Windows and candle counts are operational configuration, not strategy. Leg 1's Asian window is
`00:00-07:00 / 28 bars`, determined empirically — only that window reproduces the confirmed-truth
levels for 2022-10-03. See `STRATEGY_SPEC.md` §10.

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
