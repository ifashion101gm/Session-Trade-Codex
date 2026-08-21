# October 13, 2022 — Single-Day Backtest

- Reference session: Asian (22:00(previous day)-07:00 UTC)
- Reference high / low: 0.97221 / 0.96887
- Reference range: 33.4 pips
- Stop distance: 8.4 pips
- Session classification: BEARISH_TREND
- Directional bias: BULLISH
- M15 structure bias: BULLISH
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
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | Flowchart-selected branch |
| Direction | Short | classified session direction |
| Signal | 08:00 UTC | Closed M15 trigger candle |
| Entry | 0.97054 | confirmed 45-55% retracement; midpoint order after confirmation |
| Stop loss | 0.97137 (8.350 pips) | 25% of reference range |
| Leg A target | 0.96720 | 75% at 4R; move 25% runner to BE and target 5R |
| TP5 | 0.96636 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 08:00 / 08:30 | TREND | Short | 0.97054 | 0.97137 | 0.96636 | STOP_LOSS | -1.09R |
