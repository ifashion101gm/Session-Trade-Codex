# LONDON_CANONICAL_DELTA_REPORT.md

Differential analysis, old vs new London AM window, required by
`CANONICAL_SESSION_MIGRATION_REPORT.md` before treating `smc_3r_v1`'s London-window fix as
correctness-neutral. Real data (`data/eurusd_m15_2022_10_utc.csv`, EURUSD, Oct 2022), computed
via `session_router.build_reference_box` / `classify` — not simulated, not P&L.

```text
old (smc_3r_v1, pre-fix): 07:00-10:00 UTC, 12 x M15
new (canonical)         : 06:00-11:00 UTC, 20 x M15
```

Aggregate (full month, all M15 bars in each window, from
`CANONICAL_SESSION_MIGRATION_REPORT.md` §7):

```text
old total bars: 180   new total bars: 300
newly included 06:00-07:00: 60   common 07:00-10:00: 180   newly included 10:00-11:00: 60
```

Per-session box comparison (dates with a complete window on both sides; 15 of 18 calendar dates
in the month — 3 skipped for incomplete data, not fabricated):

| date | old_bars | new_bars | old_high | new_high | old_low | new_low | old_range | new_range | old_mid | new_mid | old_er | new_er | old_regime | new_regime |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-10-03 | 12 | 20 | 0.98273 | 0.98289 | 0.97526 | 0.97526 | 0.00747 | 0.00763 | 0.97900 | 0.97908 | 0.365 | 0.300 | RANGE | RANGE |
| 2022-10-04 | 12 | 20 | 0.98959 | 0.99039 | 0.98527 | 0.98377 | 0.00432 | 0.00662 | 0.98743 | 0.98708 | 0.104 | 0.348 | RANGE | RANGE |
| 2022-10-05 | 12 | 20 | 0.99783 | 0.99949 | 0.99212 | 0.99112 | 0.00571 | 0.00837 | 0.99497 | 0.99530 | 0.549 | 0.257 | **TREND** | **RANGE** |
| 2022-10-06 | 12 | 20 | 0.99207 | 0.99228 | 0.98750 | 0.98741 | 0.00457 | 0.00487 | 0.98979 | 0.98985 | 0.086 | 0.269 | RANGE | RANGE |
| 2022-10-07 | 12 | 20 | 0.98168 | 0.98168 | 0.97815 | 0.97657 | 0.00353 | 0.00511 | 0.97991 | 0.97913 | 0.335 | 0.034 | RANGE | RANGE |
| 2022-10-10 | 12 | 20 | 0.97333 | 0.97337 | 0.96819 | 0.96819 | 0.00514 | 0.00518 | 0.97076 | 0.97078 | 0.142 | 0.190 | RANGE | RANGE |
| 2022-10-11 | 12 | 20 | 0.97249 | 0.97249 | 0.96893 | 0.96748 | 0.00356 | 0.00501 | 0.97071 | 0.96998 | 0.093 | 0.232 | RANGE | RANGE |
| 2022-10-12 | 12 | 20 | 0.97263 | 0.97331 | 0.96956 | 0.96956 | 0.00307 | 0.00375 | 0.97110 | 0.97144 | 0.164 | 0.046 | RANGE | RANGE |
| 2022-10-13 | 12 | 20 | 0.97442 | 0.97442 | 0.96854 | 0.96854 | 0.00588 | 0.00588 | 0.97148 | 0.97148 | 0.443 | 0.214 | **TREND** | **RANGE** |
| 2022-10-14 | 12 | 20 | 0.97879 | 0.97972 | 0.97188 | 0.97188 | 0.00691 | 0.00784 | 0.97534 | 0.97580 | 0.558 | 0.248 | **TREND** | **RANGE** |
| 2022-10-17 | 12 | 20 | 0.97576 | 0.97707 | 0.97201 | 0.97201 | 0.00375 | 0.00506 | 0.97389 | 0.97454 | 0.263 | 0.023 | RANGE | RANGE |
| 2022-10-18 | 12 | 20 | 0.98738 | 0.98738 | 0.98246 | 0.98127 | 0.00492 | 0.00611 | 0.98492 | 0.98433 | 0.261 | 0.244 | RANGE | RANGE |
| 2022-10-19 | 12 | 20 | 0.98394 | 0.98411 | 0.98054 | 0.97809 | 0.00340 | 0.00602 | 0.98224 | 0.98110 | 0.046 | 0.394 | RANGE | RANGE |
| 2022-10-20 | 12 | 20 | 0.97947 | 0.98073 | 0.97716 | 0.97716 | 0.00231 | 0.00357 | 0.97832 | 0.97894 | 0.150 | 0.213 | RANGE | RANGE |
| 2022-10-21 | 12 | 20 | 0.98025 | 0.98025 | 0.97353 | 0.97323 | 0.00672 | 0.00702 | 0.97689 | 0.97674 | 0.288 | 0.196 | RANGE | RANGE |

## Reading this

- **3 of 15 sessions flip regime** (2022-10-05, 10-13, 10-14), all **TREND → RANGE** under the
  wider canonical window. In each case ER dropped below 0.40 once the extra 06:00-07:00 and
  10:00-11:00 bars were included in the path-length/displacement calculation — a wider box
  gives more room for retracement, which this classifier's formula treats as lower efficiency.
- No RANGE→TREND flips occurred in this sample.
- High/low/range/mid shift on every date (expected — different bars, different extremes) but
  regime is unchanged on 12 of 15.
- **This is not evidence that canonical is "worse" or "better."** Per
  `CANONICAL_SESSION_MIGRATION_REPORT.md` §7 and the owner's explicit instruction ("do not use
  the old London P&L as evidence for the new window... backtest performance does not gate
  canonical-migration validity"), no old-window result is used to justify keeping or reverting
  the canonical window, and no P&L was computed for either side.

## New York AM

No differential to report: every NY-consuming active file already used `12:00-15:00` UTC before
this migration (see `CANONICAL_SESSION_CONSUMER_MAP.md` — `smc_3r_v1` was the only active NY
consumer, and it was correct already; nothing else in the repo defines an active NY window).
