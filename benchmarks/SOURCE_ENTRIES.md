# Source-strategy reference entries — EURUSD, Oct 2022

The trader's own charted entries. **This file records what the charts show. Nothing here is
computed by the engine.** It is the reference set the engine is measured against.

Target: **30 entries** — 15 trading days × 2 (London entry, New York entry).

Feed: chart appears to be **EIGHTCAP**. Project fixture is VT Markets. Record the feed on
each row when known.

---

## London entry — references the Asian range

| # | Date | Ref range | Bias | Setup | Dir | Entry | Stop | Target | Result | Chart |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022-10-03 | **50.2p** | BEAR | SWEEP | SHORT | 0.98342 | 0.9846725 | 0.9771575 | 5R | ✅ |
| 2 | 2022-10-04 | **43.2p** | BULL | — | LONG | — | — | — | R:R 5.00 | ✅ |
| 3 | 2022-10-05 | | | | | | | | | |
| 4 | 2022-10-06 | | | | | | | | | |
| 5 | 2022-10-07 | | | | | | | | | |
| 6 | 2022-10-10 | | | | | | | | | |
| 7 | 2022-10-11 | | | | | | | | | |
| 8 | 2022-10-12 | | | | | | | | | |
| 9 | 2022-10-13 | | | | | | | | | |
| 10 | 2022-10-14 | | | | | | | | | |
| 11 | 2022-10-17 | | | | | | | | | |
| 12 | 2022-10-18 | | | | | | | | | |
| 13 | 2022-10-19 | | | | | | | | | |
| 14 | 2022-10-20 | | | | | | | | | |
| 15 | 2022-10-21 | | | | | | | | | |

## New York entry — references the London range

| # | Date | Ref range | Bias | Setup | Dir | Entry | Stop | Target | Result | Chart |
|---|---|---|---|---|---|---|---|---|---|---|
| 16 | 2022-10-03 | 74.7p | BEAR | SWEEP | SHORT | 0.98181 | 0.9836775 | 0.9724725 | STOP_LOSS | ✅ |
| 17 | 2022-10-04 | | BULL | TREND | LONG | — | — | — | — | ✅ |
| 18 | 2022-10-05 | | | | | | | | | |
| 19 | 2022-10-06 | | | | | | | | | |
| 20 | 2022-10-07 | | | | | | | | | |
| 21 | 2022-10-10 | | | | | | | | | |
| 22 | 2022-10-11 | | | | | | | | | |
| 23 | 2022-10-12 | | | | | | | | | |
| 24 | 2022-10-13 | | | | | | | | | |
| 25 | 2022-10-14 | | | | | | | | | |
| 26 | 2022-10-17 | | | | | | | | | |
| 27 | 2022-10-18 | | | | | | | | | |
| 28 | 2022-10-19 | | | | | | | | | |
| 29 | 2022-10-20 | | | | | | | | | |
| 30 | 2022-10-21 | | | | | | | | | |

---

**Recorded: 4 of 30.**

## Notes taken from the charts, not computed

- **#1 · 2022-10-03 London** — reference range annotated `A = 50.2`. Short: stop band above,
  target below. Full levels from `truth_source_setups.json`.
- **#2 · 2022-10-04 London** — reference range annotated `A = 43.2`. Long: target box above,
  stop box below. Label shows `Risk/Reward Ratio 5.00`. Entry, stop and target prices not
  legible at the supplied resolution.
- **#16 · 2022-10-03 New York** — from `truth_source_setups.json`, `USER_CONFIRMED_TRUTH`.
- **#17 · 2022-10-04 New York** — trader states **BULL, TREND**. Long: target box above, stop
  box below. Chart shows both the Asian box (`A = 43.2`) and the London box, with two position
  tools — the London entry and this New York entry. Reference range label and price levels not
  legible at the supplied resolution.

## What to capture per chart

Reference range · bias · setup · direction · entry · stop · target · result. The **reference
range** and the **entry price** are the two that matter most — the range identifies the
session window, the entry identifies the rule.
