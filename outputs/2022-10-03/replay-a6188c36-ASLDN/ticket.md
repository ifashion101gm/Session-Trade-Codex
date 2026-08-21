# SESSION_FLOW_V1 Trade Analysis Ticket — **HISTORICAL REPLAY**

> **THIS IS NOT A DESK TICKET.** It is a reconstruction of what the engine would
> have issued at the 2022-10-03 Asian close, generated 2026-08-16 from a stored
> fixture. No account was queried; no order existed. It cannot be used for S1.5
> reconciliation, which requires a live ticket matched to an MT5 ticket number.

- Status: **PLAN_ISSUED** (replay)
- Analysis ID: `replay-a6188c36-ASLDN`
- Strategy version: `a6188c364c63f39f` — **REJECTED** (see `STRATEGY_LEDGER.md`)
- Reference close (UTC): 2022-10-03T07:00:00Z
- Symbol: EURUSD · M15
- Data: `data/eurusd_m15_2022_10.master.csv` · sha256 `d9c1549b8f0a9bf8`
- Broker offset: UTC+3 (VT Markets, pre-30-Oct changeover)
- Feed: VT Markets. **The trader's chart appears to be EIGHTCAP.**

## Reference session — Asian, 00:00–07:00 UTC, 28 bars

| | |
|---|---|
| High | **0.98344** |
| Low | **0.97843** |
| Range | **50.1 pips** |
| Open / Close | 0.97932 / 0.97976 |

## The three questions

```
1  bull or bear?    close_location 0.2655  <  0.50   ->  BEAR
2  range or trend?  efficiency_ratio 0.0878 <= 0.35  ->  RANGE SESSION
3  swept?           candle 05:45Z made the session high
                    O 0.98103  H 0.98344  L 0.98079  C 0.98256
                    body high max(o,c) = 0.98256 < high 0.98344  ->  SWEPT

   BIAS=BEAR -> RANGE?=YES -> SWEEP?=YES  ->  SWEEP SETUP
```

## Plan — resting limit, fixed at the reference close

| | Price | R |
|---|---|---|
| **Entry** — sweep candle body | **0.98256** | 0.00 |
| **Stop** — 25% of range | **0.98381** | 1.00 |
| **TP1** — opposite boundary, close 75% + breakeven | **0.97843** | 3.30 |
| **TP2** — 5R | **0.97630** | 5.00 |

`R = 12.525 pips = 0.25 × 50.1`

Direction **SHORT**. One trade, London session 07:00–16:00 UTC. Nothing watched intraday.

## Gate evaluation

- PASS — `G0_BROKER_CLOCK`: offset UTC+3 confirmed by exhaustive window search
- PASS — `G2_DATA_INTEGRITY`: 28 of 28 expected M15 bars
- PASS — `G3_UNIVERSE`: EURUSD
- PASS — `G4_SESSION_DATA`: reference levels reproduce the confirmed-truth record
- **N/A — `G1_ENVIRONMENT`**: no account queried. Replay only.

## Replay outcome — VT Markets fixture

```
08:30Z   FILL       high 0.98273 >= 0.98256
09:30Z   TP1        75% closed at 3.297R -> banked +2.473R, stop to breakeven
09:45Z   TP2 (5R)   remaining 25% -> +1.250R
                                     ----------
                                      +3.723R
```

Spread on the fill bar: **0 points**.

## Benchmark disagreement — unresolved

`benchmarks/truth_source_setups.json` records this trade as `USER_CONFIRMED_TRUTH`
with **entry 0.98342** and `outcome TP5_HIT (+5R)`. This ticket says **0.98256**.

| | benchmark | this ticket |
|---|---|---|
| entry | 0.98342 | 0.98256 |
| basis | body of the **15:15Z** candle — a London bar | body of the **05:45Z** candle — the Asian bar that made the high |
| outcome | +5R | +3.723R |

The 8.6-pip gap is the pre-correction reading: the old contract scanned the
**execution** window for the sweep, so it found a London candle. The corrected
contract reads the sweep in the **reference** session (§2.1, 2026-08-15), which is
the ruling the trader gave.

`SESSION_FLOW_V1_SPEC.md` §0.0a establishes that the benchmark's recorded **+5R is
unreachable from its own recorded entry** on this data — the 5R target sits 16.4
pips beyond where price went. Its *entry* fields are verified; its `outcome` is
**UNVERIFIED**. Do not treat the +5R as a target this ticket failed to meet.

---

Analysis only. Levels are proposals, not automated signals. Nothing in this project
places, modifies or cancels an order.
