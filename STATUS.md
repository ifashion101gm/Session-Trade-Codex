# Project status — 15 August 2026

**Read this first.** Most other documents in this folder predate the corrections made today
and describe superseded contracts. Where they disagree with this file, this file wins.

---

## Active contract

**`SESSION_FLOW_V1`** — the trader's Session Trading Strategy diagram
(*Episode 18 — Asian Session Trading*, 1BullBear), implemented and nothing else.

Spec: **`SESSION_FLOW_V1_SPEC.md`** · Engine: **`scripts/session_flow.py`**

Superseded, retained for their analysis only:

| Contract | Status |
|---|---|
| `ASIAN_SESSION_V1` (`2530b751134fbf6e`) | superseded — `STRATEGY_SPEC.md` carries a banner |
| SSPF v2.2 (`fddb7465a73fd724`, `92279f3d42d32fc3`) | superseded |
| `SESSION_TRADING_SOURCE_WORKFLOW_V2` | superseded |

---

## The strategy in one screen

```
RUN 1  07:00 UTC   Asian complete   ->  plan for LONDON     reads the Asian range only
RUN 2  12:00 UTC   London complete  ->  plan for NEW YORK   reads the London range only

Three questions, all answered from the completed reference session:
  1  bull or bear?      close_location >= 0.50 -> BULL, else BEAR
  2  range or trend?    efficiency_ratio <= 0.35 -> RANGE, else TREND
  3  swept?             did the candle that MADE the relevant extreme close its
                        BODY back inside?   bear -> the high · bull -> the low

  SWEEP  entry = that candle's body edge
  RANGE  entry = the session boundary
  TREND  entry = the midpoint

  all three: stop = 25% of range · target = 5R
  management: SWEEP/RANGE  75% at the opposite boundary, then breakeven
              TREND        75% at 4R, then trail (unsigned)
```

Every entry is a **resting limit fixed at the reference close**. Nothing is watched
intraday. Two entries per symbol per day, maximum.

---

## Corrections made 2026-08-15

| # | What changed | Why |
|---|---|---|
| 1 | **The sweep is read in the REFERENCE session, not the execution window** | The trader's ruling: all three questions are answered at the reference close. Scanning the execution window made question 3 unanswerable at 07:00 and contradicted the desk workflow. |
| 2 | **Asian window 22:00–07:00 / 36 bars → 00:00–07:00 / 28 bars** | Exhaustive search against the trader's MT5 export: only 00:00–07:00 reproduces the confirmed-truth levels for 2022-10-03. Under the old window the contract rejected its own golden case at `G4_SESSION_DATA`. |
| 3 | **`config/strategy.yaml` brought into line** | `session_start_utc: "00:00"`, `session_candles: 28`. Execution stays 07:00–16:00 / 36. **This changes the config hash and starts a new evidence set.** |
| 4 | **All accumulated filters removed** | Not in the diagram: sweep buffer, stop buffer, touch tolerance, rejection quality, structural-stop rejection, midpoint zone, confirmation candle, opposite-quartile cancellation, the `UNCERTAIN` state. |
| 5 | **A market-fill fallback was added and then removed** | It was invented, not sourced. It moved the 15-day result by +6.25R. `REVIEW_RESPONSE.md` §2.3 had already rejected market entry. |
| 6 | **Provenance tagging introduced** | Every rule carries `[DIAGRAM]`, `[BENCHMARK]`, `[TRADER]` or `[UNSIGNED]`. An untagged rule is a defect. |

### Effect of correction 1 on the golden case

```
                     old (execution scan)      new (reference sweep)
entry                0.98342                   0.98256
filled               15:00Z                    08:30Z
5R target            missed by 16.4 pips       HIT at 09:45Z
result               -1.000R                   +3.723R
```

---

## Current evidence

`scripts/backtest_session_flow.py` — EURUSD M15, 2–21 Oct 2022, costs from the master
CSV spread column, 0.2p slippage, `STOP_FIRST`.

```
ALL              24 trades   net +8.761R   +0.365R/trade   win 25%

  leg A->L       13          +14.666R      +1.128R         38%
  leg L->NY      11           -5.905R      -0.537R          9%

  SWEEP           6          +10.591R      +1.765R         50%
  TREND          18           -1.830R      -0.102R         17%

  SWEEP A->L      4          +12.618R      +3.155R         75%   <- carries everything
```

```
95% CI on net R/trade   [-0.619, +1.349]   ** SPANS ZERO **
profit factor            1.478
max drawdown             4.063R
cost drag                0.019R per trade  (immaterial)
```

**Against `config/lifecycle.json` Stage-2 thresholds: 3 of 4 pass. The failure is
`trades >= 50` (have 24), and it is the one that matters.**

**Verdict: research candidate — needs more evidence.** In-sample, one instrument,
fifteen days, four trades carrying the result.

### Stress

| Test | Result |
|---|---|
| Slippage 0.2 → 2.0 pips | +0.365R → +0.203R per trade — **robust** |
| ER threshold 0.25 → 0.45 | +0.115R → +0.425R → +0.243R — **sharp peak, not robust** |

The ER sensitivity is why §4-B must be signed before more numbers accumulate.

---

## Open decisions — the contract cannot execute until these are signed

| # | Decision | Current | Worth |
|---|---|---|---|
| **§4-A** | "BIAS TREND" — `close_location` or `sign(close − open)` | `close_location` (only reading the benchmark permits) | ~7R over 15 days |
| **§4-B** | "IS RANGE SESSION?" — formula and threshold | `ER <= 0.35`, inherited, never sourced from the diagram | ~0.3R/trade across ±0.05 |
| **§4-C** | "Trail" for the TREND runner | held at breakeven | unmeasured |
| **§5.3a** | Leg 2 reference window | 07:00–12:00, inherited from V2 | unmeasured |

---

## Known defects

**The 2022-10-03 benchmark's `outcome` is UNVERIFIED.** Its *entry* fields are verified —
the engine reproduces them exactly. The recorded `+5R` was unreachable under the old
contract; under the corrected one the 5R target **is** hit, so this may now resolve. The
benchmark file is annotated; re-confirm before using `outcome` as a gate.

**No benchmark records its feed.** The trader's chart appears to be EIGHTCAP; the fixture
is VT Markets. Outcomes must not be transferred between brokers.

**`get_account_info` returns `"account_type": "real"` for a demo login.** Verified against
the MT5 title bar (`Demo Account - Hedge`, login 1144985, VTMarkets-Demo). The field is
unusable as a live-account interlock; the interlock is the trader's own eyes.

**`test_source_v1.py::test_literal_midpoint_trend_entry_and_stop` fails.** Legacy v1
module. 126 of 127 tests pass; a permanently-red suite trains people to ignore red.

**Every artifact in `outputs/` predates all of this.** Nine Oct-2022 variants, all
measuring the execution-window sweep plus fifteen constants that appear nowhere in the
diagram. None is a measurement of the current contract.

---

## Data

One dataset. `data/README.md` has the column contract.

```
eurusd_m15_2022_10   1,440 M15 bars   2022-10-02 21:00 .. 2022-10-21 20:45 UTC   offset +3
  master  d9c1549b8f0a9bf8
  _utc    658199e50c2846b8
  _audit  be7502f34eb83a24
```

`scripts/verify_datasets.py` runs as a pre-commit hook and in CI; it exits non-zero on drift.

**Next: GBPUSD, USDJPY, XAUUSD (`XAUUSD.crp`) for the same period** — see
`EXPORT_INSTRUCTIONS.md`. That takes the sample from 24 to roughly 100 trades and answers
whether `SWEEP A→L` is real or four lucky days.

---

## Scripts

| Script | Purpose |
|---|---|
| `session_flow.py` | **canonical engine** — plans and replays, both legs |
| `engine_report.py` | desk report at a reference close |
| `backtest_session_flow.py` | costed backtest, pools every dataset |
| `build_dataset.py` | master + views + manifest from an MT5 export |
| `verify_datasets.py` | drift check, exits non-zero |
| `validate_golden_oct3.py` | golden-case conformance |
| `run_cascade.py`, `run_flowchart.py` | earlier readings, retained for comparison |

---

## What to do next

See **[`ROADMAP.md`](ROADMAP.md)** for the full sequence and the reasoning.

In short:

1. **Sign §4-A and §4-B.** Every number produced from here inherits whichever reading is
   left in place, and §4-B moves the result by more than the result itself.
2. **Export the three symbols.** Sample to ~100, Stage-2 trade count likely passes.
3. **Fix or delete the failing v1 test.**
4. **Hold back a date range for genuine out-of-sample.** Everything so far is the same
   fifteen days with thresholds chosen while looking at them.

---

Analysis only. Nothing in this project places, modifies or cancels an order. Passing every
gate means the configured rules passed — nothing more.
