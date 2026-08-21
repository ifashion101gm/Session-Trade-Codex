# October 21, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.97835 / 0.97618
- Reference range: 21.7 pips
- Stop distance: 5.4 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: NEUTRAL
- New-entry cutoff: 16:00 UTC
- Generated signals: 2
- Executed trades: 2
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
| Signal | 07:15 UTC | Closed M15 trigger candle |
| Entry | 0.97835 | session top/bottom boundary |
| Stop loss | 0.97889 (5.425 pips) | 25% of reference range |
| Leg A target | 0.97618 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97564 | 5x risk (5R) |
| Outcome | STOP_LOSS | Bar-by-bar simulation |

### Trade 2

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | Flowchart-selected branch |
| Direction | Short | frozen bias direction |
| Signal | 08:45 UTC | Closed M15 trigger candle |
| Entry | 0.97618 | session top/bottom boundary |
| Stop loss | 0.97672 (5.425 pips) | 25% of reference range |
| Leg A target | 0.97401 | 75% after one reference-range move; 25% to BE/5R |
| TP5 | 0.97347 | 5x risk (5R) |
| Outcome | TP5_HIT | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 07:15 / 07:15 | RANGE | Short | 0.97835 | 0.97889 | 0.97564 | STOP_LOSS | -1.16R |
| 2 | 08:45 / 08:45 | RANGE | Short | 0.97618 | 0.97672 | 0.97347 | TP5_HIT | +4.12R |
