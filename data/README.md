# Data — the column contract

Two consumers in this repo want different column names for the same bars. Neither is wrong,
and neither has been changed. Instead there is **one master file** holding the superset, and
the narrow views are **generated** from it.

```
                    raw MT5 export (server time)
                              │
                  scripts/build_dataset.py build
                              │
              <stem>.master.csv   ← the only file with authority
                   ╱                        ╲
      <stem>_utc.csv                    <stem>_audit.csv
   time,o,h,l,c,spread              timestamp,o,h,l,c,volume
        │                                       │
  asian_session_backtester.py        .claude/skills/market-data-quality/
  scripts/validate_golden_oct3.py      scripts/audit_ohlcv.py
```

## Files

| File | Columns | Consumer |
|---|---|---|
| `<stem>.master.csv` | `timestamp, open, high, low, close, volume, spread` | source of truth — nothing reads it directly |
| `<stem>_utc.csv` | `time, open, high, low, close, spread` | engine / backtester |
| `<stem>_audit.csv` | `timestamp, open, high, low, close, volume` | `market-data-quality` skill |
| `<stem>.manifest.json` | — | provenance + `sha256` of master and every view |

## Rules

1. **Views are derived artifacts. Never hand-edit them.** Edit nothing; rebuild from the raw export.
2. **All timestamps are UTC.** The MT5 export is in broker server time and the offset is applied
   once, at build, and recorded in the manifest. October 2022 = **UTC+3** (Europe left DST on
   30 Oct 2022).
3. **A build refuses to write** if any bar fails `low <= open <= high`, `low <= close <= high`,
   or if a timestamp is duplicated.
4. **`verify` is the drift control.** It recomputes every hash against the manifest and exits
   non-zero if a view no longer matches its master. Run it before any backtest whose result you
   intend to keep.

## Commands

```bash
# build everything from a raw MT5 export
python scripts/build_dataset.py build EURUSD_M15_202210030000_202210212345.csv \
    --server-offset 3 --stem data/eurusd_m15_2022_10

# drift check — CI, pre-commit, or before a run that matters
python scripts/build_dataset.py verify --stem data/eurusd_m15_2022_10
```

## Current dataset

`eurusd_m15_2022_10` — EURUSD M15, VT Markets MT5 export, 1,440 bars,
**2022-10-02 21:00 → 2022-10-21 20:45 UTC**, built at server offset UTC+3.

```
master  d9c1549b8f0a9bf8
_utc    658199e50c2846b8     <- referenced by SESSION_CASCADE_V1_SPEC.md §10.5
_audit  be7502f34eb83a24
```

Structural audit: **pass**, 1,440 rows, zero issues.

## Why not standardise on one schema

Renaming to satisfy `audit_ohlcv.py` would mean editing `asian_session_backtester.py` and the
validation scripts — changing engine code to suit a reporting tool. Renaming the other way would
mean editing a vendored skill, which then diverges from upstream on the next update. Generating
both from one master costs nothing, keeps each consumer on its own contract, and makes divergence
a detectable failure rather than a silent one.

## Getting a new export from MT5

1. **Ctrl+U** → select the symbol → **Bars** tab
2. Set the period to **M15**, request the date range, click **Request**
3. **Export** → save as CSV
4. Run `build_dataset.py build` with the correct `--server-offset` for that period

The export carries `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>`.
`volume` in the master is **TICKVOL**; broker `VOL` is normally 0 on FX and is discarded.

> A structural audit cannot see timezone errors, wrong session boundaries, or feed differences
> between brokers. Those have caused every real defect in this project so far. Passing the audit
> means the file is well-formed, not that it is the right data.
