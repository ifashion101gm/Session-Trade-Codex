# October 07, 2022 — Single-Day Backtest

- Reference session: Asian (22:00(previous day)-07:00 UTC)
- Reference high / low: 0.98118 / 0.97657
- Reference range: 46.1 pips
- Stop distance: 11.5 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: BEARISH
- New-entry cutoff: 09:00 UTC
- Generated signals: 1
- Executed trades: 1
- Circuit breaker: DAILY_TARGET_LOCK

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Short | frozen bias direction |
| Signal | 08:15 UTC | Closed M15 trigger candle |
| Entry | 0.98118 | session top/bottom boundary |
| Stop loss | 0.98233 (11.525 pips) | 25% of reference range |
| Leg A target | 0.97657 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97542 | 5x risk (5R) |
| Outcome | TP5_HIT | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 08:15 / 08:15 | RANGE | Short | 0.98118 | 0.98233 | 0.97542 | TP5_HIT | +4.18R |
