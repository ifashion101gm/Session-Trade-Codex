# October 06, 2022 — Single-Day Backtest

- Reference session: Asian (22:00(previous day)-07:00 UTC)
- Reference high / low: 0.99263 / 0.98817
- Reference range: 44.6 pips
- Stop distance: 11.2 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: NEUTRAL
- New-entry cutoff: 09:00 UTC
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
| Direction | Long | swept boundary reversal direction |
| Signal | 08:45 UTC | Closed M15 trigger candle |
| Entry | 0.98767 | sweep candle body outer edge |
| Stop loss | 0.98656 (11.150 pips) | 25% of reference range |
| Leg A target | 0.99263 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.99325 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 08:45 / 10:15 | SWEEP | Long | 0.98767 | 0.98656 | 0.99325 | STOP_LOSS | -1.03R |
