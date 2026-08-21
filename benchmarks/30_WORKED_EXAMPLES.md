# 30 worked examples — EURUSD M15, 3–21 Oct 2022

Version **`7a9c682af3d10fbe`** (`SESSION_FLOW_V1_FIX1`) · regenerated 2026-08-17
Data `data/eurusd_m15_2022_10.master.csv` (`d9c1549b8f0a9bf8`)

Supersedes the set generated under `a6188c364c63f39f`. Two rules changed:

| Fix | Change |
|---|---|
| **FIX 0** | `rejection_ratio >= 0.05` decides swept vs not. Previously `body < high`, trivially true, so RANGE was unreachable. |
| **FIX 1** | Sweeps detected on **both** sides; direction comes from the **swept side**, not from bias. Bias is a selector for RANGE only. |

`dir_source` records where direction came from — `swept_side` or `bias_selector`.
Three sessions sweep both extremes; the tie-break takes the **later** one, `[UNSIGNED]`.

> Engine output, not trader charts. `benchmarks/oracle_30.csv` holds the video
> comparison. Gross R — costs are applied in `backtest_session_flow.py`.

| # | date | leg | bias | setup | dir | range p | entry | stop | target | dir source | result | R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 10-03 | A->L | BEAR | SWEEP | SHORT | 50.1 | 0.98256 | 0.98381 | 0.97630 | swept_side | TP5_HIT | +3.723 |
| 02 | 10-03 | L->NY | BEAR | TREND | SHORT | 74.7 | 0.97900 | 0.98086 | 0.96966 | — | STOP_LOSS | -1.000 |
| 03 | 10-04 | A->L | BULL | TREND | LONG | 66.0 | 0.98390 | 0.98225 | 0.99215 | — | UNFILLED | +0.000 |
| 04 | 10-04 | L->NY | BULL | TREND | LONG | 51.2 | 0.98783 | 0.98655 | 0.99423 | — | UNFILLED | +0.000 |
| 05 | 10-05 | A->L | BULL | SWEEP | SHORT | 35.7 | 0.99923 | 1.00012 | 0.99477 | swept_side | UNFILLED | +0.000 |
| 06 | 10-05 | L->NY | BEAR | TREND | SHORT | 78.8 | 0.99389 | 0.99586 | 0.98404 | — | UNFILLED | +0.000 |
| 07 | 10-06 | A->L | BEAR | TREND | SHORT | 33.3 | 0.99096 | 0.99180 | 0.98680 | — | STOP_LOSS | -1.000 |
| 08 | 10-06 | L->NY | BEAR | TREND | SHORT | 62.7 | 0.98894 | 0.99050 | 0.98110 | — | UNFILLED | +0.000 |
| 09 | 10-07 | A->L | BEAR | SWEEP | LONG | 46.1 | 0.97705 | 0.97590 | 0.98281 | swept_side | STOP_LOSS | -1.000 |
| 10 | 10-07 | L->NY | BEAR | SWEEP | SHORT | 35.3 | 0.98142 | 0.98230 | 0.97701 | swept_side | UNFILLED | +0.000 |
| 11 | 10-10 | A->L | BEAR | TREND | SHORT | 37.4 | 0.97346 | 0.97440 | 0.96878 | — | TP5_HIT | +4.250 |
| 12 | 10-10 | L->NY | BEAR | TREND | SHORT | 51.4 | 0.97076 | 0.97205 | 0.96434 | — | STOP_LOSS | -1.000 |
| 13 | 10-11 | A->L | BEAR | TREND | SHORT | 52.2 | 0.96967 | 0.97098 | 0.96315 | — | STOP_LOSS | -1.000 |
| 14 | 10-11 | L->NY | BULL | TREND | LONG | 48.8 | 0.97137 | 0.97015 | 0.97747 | — | STOP_LOSS | -1.000 |
| 15 | 10-12 | A->L | BULL | TREND | LONG | 51.7 | 0.97084 | 0.96955 | 0.97731 | — | STOP_LOSS | -1.000 |
| 16 | 10-12 | L->NY | BEAR | TREND | SHORT | 30.7 | 0.97110 | 0.97186 | 0.96726 | — | TP5_HIT | +4.250 |
| 17 | 10-13 | A->L | BEAR | TREND | SHORT | 33.4 | 0.97054 | 0.97137 | 0.96636 | — | STOP_LOSS | -1.000 |
| 18 | 10-13 | L->NY | BULL | TREND | LONG | 67.7 | 0.97192 | 0.97023 | 0.98039 | — | STOP_LOSS | -1.000 |
| 19 | 10-14 | A->L | BULL | TREND | LONG | 46.5 | 0.97850 | 0.97733 | 0.98431 | — | STOP_LOSS | -1.000 |
| 20 | 10-14 | L->NY | BEAR | TREND | SHORT | 78.8 | 0.97485 | 0.97682 | 0.96500 | — | STOP_LOSS | -1.000 |
| 21 | 10-17 | A->L | BEAR | SWEEP | SHORT | 25.3 | 0.97521 | 0.97584 | 0.97205 | swept_side | TP5_HIT | +5.000 |
| 22 | 10-17 | L->NY | BEAR | SWEEP | SHORT | 50.6 | 0.97677 | 0.97803 | 0.97045 | swept_side | STOP_LOSS | -1.000 |
| 23 | 10-18 | A->L | BULL | TREND | LONG | 49.4 | 0.98479 | 0.98356 | 0.99097 | — | STOP_LOSS | -1.000 |
| 24 | 10-18 | L->NY | BEAR | TREND | SHORT | 61.1 | 0.98433 | 0.98585 | 0.97669 | — | STOP_LOSS | -1.000 |
| 25 | 10-19 | A->L | BEAR | TREND | SHORT | 46.5 | 0.98436 | 0.98553 | 0.97855 | — | UNFILLED | +0.000 |
| 26 | 10-19 | L->NY | BEAR | TREND | SHORT | 80.2 | 0.97993 | 0.98194 | 0.96990 | — | STOP_LOSS | -1.000 |
| 27 | 10-20 | A->L | BULL | TREND | LONG | 39.8 | 0.97743 | 0.97644 | 0.98240 | — | TP5_HIT | +5.000 |
| 28 | 10-20 | L->NY | BULL | TREND | LONG | 57.3 | 0.98003 | 0.97859 | 0.98719 | — | STOP_LOSS | -1.000 |
| 29 | 10-21 | A->L | BEAR | TREND | SHORT | 21.7 | 0.97727 | 0.97781 | 0.97455 | — | STOP_LOSS | -1.000 |
| 30 | 10-21 | L->NY | BEAR | SWEEP | LONG | 70.2 | 0.97410 | 0.97235 | 0.98287 | swept_side | STOP_LOSS | -1.000 |

**30 examples · +4.223R gross**
