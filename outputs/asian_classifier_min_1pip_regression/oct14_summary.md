# October 14, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.98082 / 0.97617
- Reference range: 46.5 pips
- Stop distance: 11.6 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: BEARISH
- New-entry cutoff: 16:00 UTC
- Generated signals: 2
- Executed trades: 2
- Circuit breaker: MAX_SESSION_LOSS_LOCK

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | Flowchart-selected branch |
| Direction | Long | swept boundary reversal direction |
| Signal | 07:15 UTC | Closed M15 trigger candle |
| Entry | 0.97624 | sweep candle body outer edge |
| Stop loss | 0.97508 (11.625 pips) | 25% of reference range |
| Leg A target | 0.98082 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.98205 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |

### Trade 2

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | Flowchart-selected branch |
| Direction | Long | swept boundary reversal direction |
| Signal | 12:45 UTC | Closed M15 trigger candle |
| Entry | 0.97353 | sweep candle body outer edge |
| Stop loss | 0.97237 (11.625 pips) | 25% of reference range |
| Leg A target | 0.98082 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97934 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 07:15 / 07:30 | SWEEP | Long | 0.97624 | 0.97508 | 0.98205 | STOP_LOSS | -1.07R |
| 2 | 12:45 / 13:30 | SWEEP | Long | 0.97353 | 0.97237 | 0.97934 | STOP_LOSS | -1.08R |
