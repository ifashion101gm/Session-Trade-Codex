# October 17, 2022 — Single-Day Backtest

- Reference session: London (07:00-12:00 UTC)
- Reference high / low: 0.97707 / 0.97201
- Reference range: 50.6 pips
- Stop distance: 12.6 pips
- Session classification: RANGE
- Directional bias: BULLISH
- M15 structure bias: BULLISH
- New-entry cutoff: 18:00 UTC
- Generated signals: 1
- Executed trades: 1
- Circuit breaker: DAILY_TARGET_LOCK

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | London session | Completed reference session |
| Entry session | New York | Following execution session |
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Long | frozen bias direction |
| Signal | 12:30 UTC | Closed M15 trigger candle |
| Entry | 0.97707 | session top/bottom boundary |
| Stop loss | 0.97581 (12.650 pips) | 25% of reference range |
| Leg A target | 0.98213 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.98339 | 5x risk (5R) |
| Outcome | TP5_HIT | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 12:30 / 12:30 | RANGE | Long | 0.97707 | 0.97581 | 0.98339 | TP5_HIT | +4.18R |
