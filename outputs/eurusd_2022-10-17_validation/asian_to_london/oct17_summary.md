# October 17, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.97561 / 0.97308
- Reference range: 25.3 pips
- Stop distance: 6.3 pips
- Session classification: RANGE
- Directional bias: BULLISH
- M15 structure bias: BULLISH
- New-entry cutoff: 16:00 UTC
- Generated signals: 1
- Executed trades: 1
- Circuit breaker: DAILY_TARGET_LOCK

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | Flowchart-selected branch |
| Direction | Long | swept boundary reversal direction |
| Signal | 08:30 UTC | Closed M15 trigger candle |
| Entry | 0.97338 | sweep candle body outer edge |
| Stop loss | 0.97275 (6.325 pips) | 25% of reference range |
| Leg A target | 0.97561 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97654 | 5x risk (5R) |
| Outcome | TP5_HIT | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 08:30 / 08:45 | SWEEP | Long | 0.97338 | 0.97275 | 0.97654 | TP5_HIT | +3.78R |
