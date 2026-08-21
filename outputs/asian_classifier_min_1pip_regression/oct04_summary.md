# October 04, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.98720 / 0.98060
- Reference range: 66.0 pips
- Stop distance: 16.5 pips
- Session classification: RANGE
- Directional bias: BULLISH
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
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Long | frozen bias direction |
| Signal | 07:00 UTC | Closed M15 trigger candle |
| Entry | 0.98720 | session top/bottom boundary |
| Stop loss | 0.98555 (16.500 pips) | 25% of reference range |
| Leg A target | 0.99380 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.99545 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 07:00 / 07:00 | RANGE | Long | 0.98720 | 0.98555 | 0.99545 | STOP_LOSS | -1.07R |
