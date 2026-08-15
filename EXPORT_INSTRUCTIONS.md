# Adding the other three symbols

Everything downstream is ready. Export three CSVs from MT5, run two commands each,
and the backtest pools all four symbols automatically.

---

## 1. Export from MT5 — about two minutes per symbol

For each of **GBPUSD**, **USDJPY**, **XAUUSD**:

1. **Ctrl+U** → select the symbol → **Bars** tab
2. Period **M15**, range **2022.10.01 – 2022.10.22** → **Request**
3. **Export** → save the CSV anywhere convenient

> **Gold is `XAUUSD.crp` on your broker** (`PROJECT_CHARTER.md` Q4). Plain `XAUUSD`
> does not exist. Export whichever string Ctrl+U shows — the filename does not matter,
> only the `--stem` you pass in step 2.

If the Bars tab will not reach back to 2022, open an M15 chart for that symbol, scroll
left until October 2022 loads, then retry the export.

---

## 2. Build — one command per symbol

```powershell
python scripts/build_dataset.py build GBPUSD_M15_202210030000_202210212345.csv `
    --server-offset 3 --stem data/gbpusd_m15_2022_10

python scripts/build_dataset.py build USDJPY_M15_202210030000_202210212345.csv `
    --server-offset 3 --stem data/usdjpy_m15_2022_10

python scripts/build_dataset.py build XAUUSD_M15_202210030000_202210212345.csv `
    --server-offset 3 --stem data/xauusd_m15_2022_10
```

**`--server-offset 3`** for all three. October 2022 is before the 30 Oct DST changeover,
so VT Markets is UTC+3 throughout.

Each build writes a master, two views and a manifest, and refuses to write if any bar
fails `low <= open <= high` or a timestamp is duplicated.

---

## 3. Verify

```powershell
python scripts/verify_datasets.py
```

Checks every dataset against its manifest. Exits non-zero on drift, so the pre-commit
hook covers the new files automatically.

---

## 4. Backtest — no arguments needed

```powershell
python scripts/backtest_session_flow.py
```

It pools every `*.master.csv` under `data/`. Per-symbol, per-leg and per-setup blocks
appear on their own.

To isolate one symbol:

```powershell
python scripts/backtest_session_flow.py --dataset gbpusd_m15_2022_10
```

---

## Notes on the other instruments

**Price precision is inferred from the file**, so no configuration is needed:

| Symbol | Digits | Point | Spread column converts as |
|---|---|---|---|
| EURUSD, GBPUSD | 5 | 0.00001 | `spread × 0.00001` |
| USDJPY | 3 | 0.001 | `spread × 0.001` |
| XAUUSD | 2 | 0.01 | `spread × 0.01` |

Everything is expressed in **R**, and R is 25% of that session's range in that
instrument's own price units — so results are directly comparable across symbols
without any pip-value conversion.

**Gold will behave differently.** Its Asian range is far wider in absolute terms, so R
is larger and the spread is a smaller fraction of it. Expect cost drag to matter even
less on gold and slightly more on USDJPY.

---

## What this gets you

| | now | after |
|---|---|---|
| Trades | 24 | **~100** |
| Instruments | 1 | 4 |
| 95% CI | spans zero | narrows by roughly half |
| Stage-2 trade count (≥50) | FAIL | **likely PASS** |

It also answers the question the current sample cannot: **is `SWEEP A→L` real?** Four
trades carrying +12.618R is either the edge or an accident, and only independent
instruments can separate those.

Still in-sample — same fifteen days, same thresholds chosen while looking at them. A
larger sample makes the number more stable, not out-of-sample. Genuine out-of-sample
needs a different date range, held back until the rules are signed.
