# October 06, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.99263 / 0.98930
- Reference range: 33.3 pips
- Stop distance: 8.3 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: NEUTRAL
- New-entry cutoff: 16:00 UTC
- Generated signals: 1
- Executed trades: 1
- Circuit breaker: not triggered

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Short | frozen bias direction |
| Signal | 08:15 UTC | Closed M15 trigger candle |
| Entry | 0.98930 | session top/bottom boundary |
| Stop loss | 0.99013 (8.325 pips) | 25% of reference range |
| Leg A target | 0.98597 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.98514 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 08:15 / 08:15 | RANGE | Short | 0.98930 | 0.99013 | 0.98514 | STOP_LOSS | -1.04R |
