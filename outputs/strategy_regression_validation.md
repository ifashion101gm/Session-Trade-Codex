# Strategy Regression Validation

Run date: 2026-08-14  
Data: Connected approved MT5 EUR/USD M15 history  
Purpose: verify that the October 4 Range Setup repair preserves both confirmed
October 3 Sweep entries.

| Benchmark | Expected geometry | Current engine | Entry validation | Feed outcome |
| --- | --- | --- | --- | --- |
| 2022-10-03 Asian → London | Short Sweep, 15:15 UTC, entry 0.98342, SL 0.9846725, TP5 0.9771575 | Exact same setup, time, direction and prices | PASS | END_WINDOW on connected feed; source benchmark says TP5_HIT |
| 2022-10-03 London → New York | Short Sweep, 14:15 UTC, entry 0.98181, SL 0.9836775, TP5 0.9724725 | Exact same setup, time, direction and prices | PASS | STOP_LOSS at 15:00 UTC, −1R; matches source benchmark |
| 2022-10-04 London → New York | Long Range, 12:15 UTC, entry 0.99039, SL 0.98911, TP5 0.99679 | Exact setup and prices; TP5 at 15:00 UTC | PASS | TP5_HIT; +4.25R position-weighted before friction |

## Regression observation

The October 3 Asian → London cycle also generates an earlier bearish Range
breakout at 09:30 UTC under the new direction-aligned Range rule. It does not
prevent the truth-source 15:15 Sweep from being generated. Eliminating the
earlier Range trade solely because a later Sweep occurs would require future
lookahead. Therefore the engine preserves both causal signals and reports the
additional trade rather than suppressing it with date-specific logic.

## Status

- Both previous truth-source entries remain reproducible: **PASS**.
- October 3 New York −1R outcome remains reproducible: **PASS**.
- October 4 Range entry/SL/TP and TP5 outcome remain reproducible: **PASS**.
- October 3 London source-video TP5 versus connected-feed end-window result:
  **SOURCE_DATA_MISMATCH**, preserved without hardcoding.
