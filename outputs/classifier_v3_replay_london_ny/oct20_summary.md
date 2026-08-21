# October 20, 2022 — Single-Day Backtest

- Reference session: London (07:00-12:00 UTC)
- Reference high / low: 0.98289 / 0.97716
- Reference range: 57.3 pips
- Stop distance: 14.3 pips
- Session classification: BULLISH_TREND
- Directional bias: BULLISH
- M15 structure bias: BULLISH
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
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | Flowchart-selected branch |
| Direction | Long | classified session direction |
| Signal | 13:00 UTC | Closed M15 trigger candle |
| Entry | 0.98003 | confirmed 45-55% retracement; midpoint order after confirmation |
| Stop loss | 0.97859 (14.325 pips) | 25% of reference range |
| Leg A target | 0.98576 | 75% at 4R; move 25% runner to BE and target 5R |
| TP5 | 0.98719 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |

### Trade 2

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | London session | Completed reference session |
| Entry session | New York | Following execution session |
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | Flowchart-selected branch |
| Direction | Long | classified session direction |
| Signal | 16:30 UTC | Closed M15 trigger candle |
| Entry | 0.98003 | confirmed 45-55% retracement; midpoint order after confirmation |
| Stop loss | 0.97859 (14.325 pips) | 25% of reference range |
| Leg A target | 0.98576 | 75% at 4R; move 25% runner to BE and target 5R |
| TP5 | 0.98719 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 13:00 / 13:15 | TREND | Long | 0.98003 | 0.97859 | 0.98719 | STOP_LOSS | -1.06R |
| 2 | 16:30 / 16:45 | TREND | Long | 0.98003 | 0.97859 | 0.98719 | STOP_LOSS | -1.06R |
