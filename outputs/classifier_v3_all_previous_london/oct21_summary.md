# October 21, 2022 — Single-Day Backtest

- Reference session: London (07:00-12:00 UTC)
- Reference high / low: 0.98025 / 0.97323
- Reference range: 70.2 pips
- Stop distance: 17.5 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: NEUTRAL
- New-entry cutoff: 18:00 UTC
- Generated signals: 2
- Executed trades: 2
- Circuit breaker: MAX_SESSION_LOSS_LOCK

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | London session | Completed reference session |
| Entry session | New York | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Short | frozen bias direction |
| Signal | 12:00 UTC | Closed M15 trigger candle |
| Entry | 0.97323 | session top/bottom boundary |
| Stop loss | 0.97498 (17.550 pips) | 25% of reference range |
| Leg A target | 0.96621 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.96446 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |

### Trade 2

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | London session | Completed reference session |
| Entry session | New York | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Short | frozen bias direction |
| Signal | 14:00 UTC | Closed M15 trigger candle |
| Entry | 0.98025 | session top/bottom boundary |
| Stop loss | 0.98200 (17.550 pips) | 25% of reference range |
| Leg A target | 0.97323 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97148 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 12:00 / 12:00 | RANGE | Short | 0.97323 | 0.97498 | 0.96446 | STOP_LOSS | -1.07R |
| 2 | 14:00 / 14:00 | RANGE | Short | 0.98025 | 0.98200 | 0.97148 | STOP_LOSS | -1.05R |
