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
| 3 | 2022-10-05 | **31.1p** | BULL | TREND | LONG | — | — | — | — | ✅ |
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

**Recorded: 5 of 30.**

## Notes taken from the charts, not computed

- **#1 · 2022-10-03 London** — reference range annotated `A = 50.2`. Short: stop band above,
  target below. Full levels from `truth_source_setups.json`.
- **#2 · 2022-10-04 London** — reference range annotated `A = 43.2`. Long: target box above,
  stop box below. Label shows `Risk/Reward Ratio 5.00`. Entry, stop and target prices not
  legible at the supplied resolution.
- **#3 · 2022-10-05 London** — reference range annotated `A = 31.1`. Trader states **TREND,
  LONG**. Target box above, stop box below. A `Target` label sits at the top of the target box
  and an `Open PNL` label with a `Risk/Reward Ratio` sits at the entry; prices not legible at
  the supplied resolution.
- **#16 · 2022-10-03 New York** — from `truth_source_setups.json`, `USER_CONFIRMED_TRUTH`.
- **#17 · 2022-10-04 New York** — trader states **BULL, TREND**. Long: target box above, stop
  box below. Chart shows both the Asian box (`A = 43.2`) and the London box, with two position
  tools — the London entry and this New York entry. Reference range label and price levels not
  legible at the supplied resolution.

## What to capture per chart

Reference range · bias · setup · direction · entry · stop · target · result. The **reference
range** and the **entry price** are the two that matter most — the range identifies the
session window, the entry identifies the rule.

---

## Candidates from Codex backtest artifacts

Extracted from `outputs/*/backtest_results.json`. **These are engine output from a
superseded contract** (execution-window sweep plus fifteen constants absent from the
diagram) — not trader charts. Recorded here as candidates only. Where a date carries
more than one record, different variant folders disagreed and the trader must rule.


### London entry — reference ASIAN

| # | Date | Setup | Dir | Entry | Outcome | R | status |
|---|---|---|---|---|---|---|---|
| 1 | 2022-10-03 | RANGE | SHORT | 0.97843 | STOP_LOSS | -1.036 | **2 CONFLICTING** |
| 1 | 2022-10-03 | SWEEP | SHORT | 0.98342 | END_WINDOW | +1.038 |  |
| 2 | 2022-10-04 | RANGE | LONG | 0.98720 | STOP_LOSS | -1.032 | single |
| 3 | 2022-10-05 | RANGE | LONG | 0.99592 | STOP_LOSS | -1.059 | single |
| 4 | 2022-10-06 | RANGE | SHORT | 0.98930 | STOP_LOSS | -1.012 | single |
| 5 | 2022-10-07 | RANGE | SHORT | 0.98118 | TP5_HIT | +4.200 | single |
| 6 | 2022-10-10 | RANGE | SHORT | 0.97159 | STOP_LOSS | -1.070 | single |
| 7 | 2022-10-11 | SWEEP | SHORT | 0.97130 | STOP_LOSS | -1.048 | **2 CONFLICTING** |
| 7 | 2022-10-11 | RANGE | SHORT | 0.97228 | STOP_LOSS | -1.050 |  |
| 8 | 2022-10-12 | RANGE | LONG | 0.96826 | STOP_LOSS | -1.054 | **2 CONFLICTING** |
| 8 | 2022-10-12 | SWEEP | LONG | 0.96735 | UNFILLED | — |  |
| 9 | 2022-10-13 | TREND | LONG | 0.97054 | TP5_HIT | +4.178 | **2 CONFLICTING** |
| 9 | 2022-10-13 | TREND | SHORT | 0.97054 | STOP_LOSS | -1.084 |  |
| 10 | 2022-10-14 | SWEEP | LONG | 0.97624 | STOP_LOSS | -1.056 | **2 CONFLICTING** |
| 10 | 2022-10-14 | SWEEP | LONG | 0.97353 | STOP_LOSS | -1.060 |  |
| 11 | 2022-10-17 | — | — | — | — | — | **no Codex record** |
| 12 | 2022-10-18 | SWEEP | SHORT | 0.98627 | STOP_LOSS | -1.057 | single |
| 13 | 2022-10-19 | SWEEP | LONG | 0.98212 | STOP_LOSS | -1.058 | single |
| 14 | 2022-10-20 | TREND | LONG | 0.97743 | TP5_HIT | +4.205 | single |
| 15 | 2022-10-21 | RANGE | SHORT | 0.97835 | STOP_LOSS | -1.124 | **3 CONFLICTING** |
| 15 | 2022-10-21 | RANGE | SHORT | 0.97618 | TP5_HIT | +4.153 |  |
| 15 | 2022-10-21 | SWEEP | LONG | 0.97661 | TP5_HIT | +3.531 |  |


### New York entry — reference LONDON

| # | Date | Setup | Dir | Entry | Outcome | R | status |
|---|---|---|---|---|---|---|---|
| 16 | 2022-10-03 | SWEEP | SHORT | 0.98181 | STOP_LOSS | -1.037 | single |
| 17 | 2022-10-04 | RANGE | LONG | 0.99039 | TP5_HIT | +4.201 | single |
| 18 | 2022-10-05 | RANGE | SHORT | 0.98995 | STOP_LOSS | -1.051 | single |
| 19 | 2022-10-06 | RANGE | SHORT | 0.98580 | END_WINDOW | +3.963 | single |
| 20 | 2022-10-07 | RANGE | SHORT | 0.97815 | TP5_HIT | +4.227 | single |
| 21 | 2022-10-10 | SWEEP | SHORT | 0.97121 | END_WINDOW | +0.669 | single |
| 22 | 2022-10-11 | RANGE | LONG | 0.97381 | STOP_LOSS | -1.057 | **2 CONFLICTING** |
| 22 | 2022-10-11 | RANGE | SHORT | 0.97381 | STOP_LOSS | -1.057 |  |
| 23 | 2022-10-12 | SWEEP | LONG | 0.97039 | STOP_LOSS | -1.088 | **3 CONFLICTING** |
| 23 | 2022-10-12 | RANGE | LONG | 0.96956 | STOP_LOSS | -1.091 |  |
| 23 | 2022-10-12 | TREND | LONG | 0.97110 | STOP_LOSS | -1.091 |  |
| 24 | 2022-10-13 | TREND | LONG | 0.97192 | TP5_HIT | +4.209 | single |
| 25 | 2022-10-14 | — | — | — | — | — | **no Codex record** |
| 26 | 2022-10-17 | RANGE | LONG | 0.97707 | TP5_HIT | +4.199 | single |
| 27 | 2022-10-18 | — | — | — | — | — | **no Codex record** |
| 28 | 2022-10-19 | SWEEP | LONG | 0.97620 | END_WINDOW | +0.489 | **2 CONFLICTING** |
| 28 | 2022-10-19 | TREND | SHORT | 0.97993 | END_WINDOW | +1.277 |  |
| 29 | 2022-10-20 | SWEEP | SHORT | 0.98267 | STOP_LOSS | -1.049 | single |
| 30 | 2022-10-21 | TREND | SHORT | 0.97674 | UNFILLED | — | **3 CONFLICTING** |
| 30 | 2022-10-21 | RANGE | SHORT | 0.97323 | STOP_LOSS | -1.057 |  |
| 30 | 2022-10-21 | RANGE | SHORT | 0.98025 | STOP_LOSS | -1.040 |  |


**Coverage: 27 of 30 slots have at least one Codex record. 10 carry conflicting records. 3 have none.**
