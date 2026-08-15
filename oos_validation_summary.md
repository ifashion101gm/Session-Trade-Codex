# Out-of-Sample Validation Summary

The calibrated M15 boundary-limit strategy was tested without parameter changes. Results include the dynamic spread model and 0.2-pip round-trip slippage. Drawdown is peak-to-trough in R, not a percentage; a percentage requires a specified account risk per trade.

## OOS Window 1 — EUR/USD, November–December 2022

| Month | Trades | TP5 Win Rate | Profit Factor | Max Drawdown | Gross R | Net R |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-11 | 27 | 11.11% | 0.66 | 9.48R | -5.57R | -7.97R |
| 2022-12 | 27 | 22.22% | 1.90 | 6.64R | +18.62R | +15.96R |
| **Combined** | **54** | **16.67%** | — | — | **+13.05R** | **+7.98R** |

November failed while December recovered strongly. The two-month aggregate is positive, but the 9.48R November drawdown is material.

## OOS Window 2 — EUR/USD, Full Year 2023

| Month | Trades | TP5 Win Rate | Profit Factor | Max DD | Gross R | Net R |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jan | 24 | 20.83% | 1.41 | 3.45R | +10.22R | +7.37R |
| Feb | 21 | 19.05% | 0.94 | 7.94R | +1.54R | -1.13R |
| Mar | 20 | 30.00% | 2.67 | 2.31R | +22.58R | +20.27R |
| Apr | 18 | 16.67% | 1.11 | 9.21R | +4.03R | +1.63R |
| May | 26 | 26.92% | 1.68 | 6.87R | +16.62R | +13.05R |
| Jun | 20 | 20.00% | 0.99 | 6.12R | +2.75R | -0.21R |
| Jul | 23 | 17.39% | 1.33 | 7.98R | +8.79R | +5.88R |
| Aug | 29 | 13.79% | 1.33 | 8.51R | +11.59R | +7.26R |
| Sep | 21 | 23.81% | 1.13 | 7.21R | +5.25R | +2.33R |
| Oct | 26 | 23.08% | 1.52 | 4.95R | +13.84R | +10.64R |
| Nov | 23 | 17.39% | 1.28 | 7.61R | +6.75R | +5.04R |
| Dec | 19 | 10.53% | 0.59 | 8.08R | -4.50R | -7.49R |
| **Total** | **270** | **20.00%** | — | **9.21R max monthly** | **+99.47R** | **+64.64R** |

Three months were negative after friction. This is encouraging OOS evidence, not authorization for live trading; tick-level fills, commissions, rollover, news, and portfolio correlation remain unmodeled.
