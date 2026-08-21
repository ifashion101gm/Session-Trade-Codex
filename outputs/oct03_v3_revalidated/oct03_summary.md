# October 03, 2022 — Single-Day Backtest

- Reference session: Asian (22:00(previous day)-07:00 UTC)
- Reference high / low: 0.98344 / 0.97843
- Reference range: 50.1 pips
- Stop distance: 12.5 pips
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
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | Flowchart-selected branch |
| Direction | Short | swept boundary reversal direction |
| Signal | 15:15 UTC | Closed M15 trigger candle |
| Entry | 0.98342 | sweep candle body outer edge |
| Stop loss | 0.98467 (12.525 pips) | 25% of reference range |
| Leg A target | 0.97843 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97716 | 5x risk (5R) |
| Outcome | END_WINDOW | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 15:15 / 15:30 | SWEEP | Short | 0.98342 | 0.98467 | 0.97716 | END_WINDOW | +1.02R |
