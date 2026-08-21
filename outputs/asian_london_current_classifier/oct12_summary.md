# October 12, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.97343 / 0.96826
- Reference range: 51.7 pips
- Stop distance: 12.9 pips
- Session classification: RANGE
- Directional bias: BULLISH
- M15 structure bias: BULLISH
- New-entry cutoff: 16:00 UTC
- Generated signals: 1
- Executed trades: 0
- Circuit breaker: not triggered

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
| Signal | 14:45 UTC | Closed M15 trigger candle |
| Entry | 0.96735 | sweep candle body outer edge |
| Stop loss | 0.96606 (12.925 pips) | 25% of reference range |
| Leg A target | 0.97343 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97381 | 5x risk (5R) |
| Outcome | UNFILLED | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 14:45 / unfilled | SWEEP | Long | 0.96735 | 0.96606 | 0.97381 | UNFILLED | N/A |
