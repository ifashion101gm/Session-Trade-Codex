# Run the 12-month pull — three commands

The data pull must run on **this Windows machine**, because the `MetaTrader5`
Python package talks to the terminal through a local pipe. MetaTrader 5 is
already open and logged in as `1144985 · VTMarkets-Demo · Demo Account - Hedge`,
and **Algo Trading is off** — leave it off.

Open **Windows PowerShell** and paste this block:

```powershell
cd "$env:USERPROFILE\OneDrive\Documents\ChatGPT\Session Trade Codex"
pip install MetaTrader5
python scripts\fetch_mt5_year.py --months 12 --seal-from 2026-05-01
python scripts\verify_datasets.py
python scripts\backtest_session_flow.py --match m15_y12
```

## What each line does

| Line | Effect |
|---|---|
| `fetch_mt5_year.py --months 12 --seal-from 2026-05-01` | Pulls M15 for EURUSD, GBPUSD, USDJPY, XAUUSD from Aug 2025. Everything **before** 1 May 2026 goes to `data/` as the development set; everything **on or after** goes to `data/sealed/`. |
| `verify_datasets.py` | Recomputes every sha256 and fails on drift. |
| `backtest_session_flow.py --match m15_y12` | Runs the development set only. `data/sealed/` is outside the glob — it prints a line confirming how many sealed sets it skipped. |

## Read the offset check before you read the result

The pull ends with an hourly range profile per symbol:

```
    00:00  0.61 |########                    | asian ref
    ...
    13:00  1.84 |###########################  | new york
    asian mean 0.68 vs rest 1.31  -> OK
```

The Asian hours must sit in the **trough**. That is the DST verification — the
year crosses two changeovers (2025-11-02 `+3 -> +2`, 2026-03-08 `+2 -> +3`) and a
wrong offset slides every session window by an hour.

**If any symbol prints FAIL, stop.** Re-run with `--summer-offset` /
`--winter-offset` adjusted. Do not backtest data that failed this check.

## If a symbol returns no bars

Open an M15 chart for it in MT5 and press **Home** to force the terminal to
download history, then re-run. Gold is the usual offender.

## The sealed set

`data/sealed/` holds May–Aug 2026 and must not be opened until every rule in
`SESSION_FLOW_V1_SPEC.md` §4 is signed. Three remain: §4-A, §4-B, §4-C.
Its manifest carries the reason in a `seal_note` field.

Nothing in any of these scripts places, modifies or cancels an order.
