# Session Strategy Entry Database

Every result is mapped to its recorded strategy contract. Rows marked `REPLAY_REQUIRED` are legacy evidence and do not validate the active engine.

## 1. EURUSD-20221003-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-03 | Stored benchmark date |
| Contract | v3.0 / CURRENT | Evidence compatibility |
| Reference | Asian 22:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=YES -> SWEEP_SETUP |
| Direction | Short | Swept boundary reversal direction |
| Signal | 2022-10-03T15:15:00Z | Closed M15 trigger |
| Entry | 0.98342 | Sweep candle body outer edge |
| Stop loss | 0.9846725 (12.525 pips) | 25% of reference range |
| Leg A target | 0.97843 | 75% after one range move then 25% to BE/5R |
| TP5 | 0.9771575 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | END_WINDOW | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 2. EURUSD-20221003-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-03 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=YES -> SWEEP_SETUP |
| Direction | Short | Swept boundary reversal direction |
| Signal | 2022-10-03T14:15:00Z | Closed M15 trigger |
| Entry | 0.98181 | Sweep candle body outer edge |
| Stop loss | 0.9836775 (18.675 pips) | 25% of reference range |
| Leg A target | 0.97526 | 75% after one range move then 25% to BE/5R |
| TP5 | 0.9724725 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 3. EURUSD-20221004-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-04 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BULLISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Long | Frozen bias direction |
| Signal | 2022-10-04T12:15:00Z | Closed M15 trigger |
| Entry | 0.99039 | First valid session boundary |
| Stop loss | 0.98911 (12.8 pips) | 25% of reference range |
| Leg A target | 0.99551 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.99679 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | TP5_HIT | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 4. EURUSD-20221005-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-05 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BULLISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Long | Frozen bias direction |
| Signal | 2022-10-05T07:15:00Z | Closed M15 trigger |
| Entry | 0.99592 | First valid session boundary |
| Stop loss | 0.9950275 (8.925 pips) | 25% of reference range |
| Leg A target | 0.99949 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 1.0003825 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 5. EURUSD-20221005-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-05 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-05T13:00:00Z | Closed M15 trigger |
| Entry | 0.98995 | First valid session boundary |
| Stop loss | 0.99192 (19.7 pips) | 25% of reference range |
| Leg A target | 0.98207 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.98010 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | END_WINDOW | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 6. EURUSD-20221006-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-06 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-06T08:15:00Z | Closed M15 trigger |
| Entry | 0.98930 | First valid session boundary |
| Stop loss | 0.9901325 (8.325 pips) | 25% of reference range |
| Leg A target | 0.98597 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.9851375 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 7. EURUSD-20221006-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-06 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Trend Setup | BIAS=BEARISH -> RANGE?=NO -> TREND_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | UNRESOLVED_FROM_SCREENSHOT | Closed M15 trigger |
| Entry | 0.988935 | Middle of reference range |
| Stop loss | 0.9905025 (15.675 pips) | 25% of reference range |
| Leg A target | 0.982665 | Close 75% at 4R and trail remaining 25% |
| TP5 | 0.9810975 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | NO_FILL | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 8. EURUSD-20221007-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-07 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-07T08:15:00Z | Closed M15 trigger |
| Entry | 0.98118 | First valid session boundary |
| Stop loss | 0.9823325 (11.525 pips) | 25% of reference range |
| Leg A target | 0.97657 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.9754175 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | TP5_HIT | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 9. EURUSD-20221007-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-07 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-07T12:30:00Z | Closed M15 trigger |
| Entry | 0.97815 | First valid session boundary |
| Stop loss | 0.9790325 (8.825 pips) | 25% of reference range |
| Leg A target | 0.97462 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.9737375 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | TP5_HIT | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 10. EURUSD-20221011-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-11 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-11T15:45:00Z | Closed M15 trigger |
| Entry | 0.97381 | First valid session boundary |
| Stop loss | 0.97503 (12.2 pips) | 25% of reference range |
| Leg A target | 0.96893 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.96771 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 11. EURUSD-20221012-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-12 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | BIAS=BULLISH -> RANGE?=YES -> SWEEP?=YES -> SWEEP_SETUP |
| Direction | Long | Swept boundary reversal direction |
| Signal | 2022-10-12T14:45:00Z | Closed M15 trigger |
| Entry | 0.96735 | Sweep candle body outer edge |
| Stop loss | 0.9660575 (12.925 pips) | 25% of reference range |
| Leg A target | 0.97343 | 75% at opposite boundary then 25% to BE/5R |
| TP5 | 0.9738125 | 5x risk (5R) |
| Source outcome | MISSED_TRADE | Source/chart evidence |
| Connected-feed outcome | UNFILLED | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 12. EURUSD-20221012-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-12 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | BIAS=BULLISH -> RANGE?=NO -> SWEEP?=N/A -> TREND_SETUP |
| Direction | Long | Frozen bias direction |
| Signal | 2022-10-12T12:45:00Z | Closed M15 trigger |
| Entry | 0.971095 | Middle of reference range |
| Stop loss | 0.9703275 (7.675 pips) | 25% of reference range |
| Leg A target | 0.974165 | 75% at 4R then trail remaining 25% |
| TP5 | 0.9749325 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 13. EURUSD-20221013-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-13 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | BIAS=BULLISH -> RANGE?=NO -> SWEEP?=N/A -> TREND_SETUP |
| Direction | Long | Frozen bias direction |
| Signal | 2022-10-13T07:45:00Z | Closed M15 trigger |
| Entry | 0.97054 | Middle of reference range |
| Stop loss | 0.969705 (8.35 pips) | 25% of reference range |
| Leg A target | 0.97388 | 75% at 4R then trail remaining 25% |
| TP5 | 0.974715 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | TP5_HIT | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 14. EURUSD-20221014-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-14 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=YES -> SWEEP_SETUP |
| Direction | Long | Swept boundary reversal direction |
| Signal | 2022-10-14T07:15:00Z | Closed M15 trigger |
| Entry | 0.97624 | Sweep candle body outer edge |
| Stop loss | 0.9750775 (11.625 pips) | 25% of reference range |
| Leg A target | 0.98082 | 75% at opposite boundary then 25% to BE/5R |
| TP5 | 0.9820525 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 15. EURUSD-20221018-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-18 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | Yes | Step 3 when Range = Yes |
| Setup | Sweep Setup | BIAS=BULLISH -> RANGE?=YES -> SWEEP?=YES -> SWEEP_SETUP |
| Direction | Short | Swept boundary reversal direction |
| Signal | 2022-10-18T07:00:00Z | Closed M15 trigger |
| Entry | 0.98627 | Sweep candle body outer edge |
| Stop loss | 0.987505 (12.35 pips) | 25% of reference range |
| Leg A target | 0.98232 | 75% at opposite boundary then 25% to BE/5R |
| TP5 | 0.980095 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 16. EURUSD-20221020-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-20 | Stored benchmark date |
| Contract | v3.0 / CURRENT | Evidence compatibility |
| Reference | Asian 22:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | BIAS=BULLISH -> RANGE?=NO -> SWEEP?=N/A -> TREND_SETUP |
| Direction | Long | Frozen bias direction |
| Signal | 2022-10-20T07:15:00Z | Closed M15 trigger |
| Entry | 0.97743 | Confirmed 45-55% retracement; midpoint order after confirmation |
| Stop loss | 0.976435 (9.95 pips) | 25% of reference range |
| Leg A target | 0.98141 | 75% at 4R then 25% to BE/5R |
| TP5 | 0.982405 | 5x risk (5R) |
| Source outcome | TP5_HIT | Source/chart evidence |
| Connected-feed outcome | TP5_HIT | Bar-by-bar simulation |
| Evidence | SOURCE_CHART_VALIDATED | Validation status |

## 17. EURUSD-20221020-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-20 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bullish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BULLISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Long | Frozen bias direction |
| Signal | UNRESOLVED_FROM_SCREENSHOT | Closed M15 trigger |
| Entry | 0.97716 | First valid session boundary |
| Stop loss | 0.9757275 (14.325 pips) | 25% of reference range |
| Leg A target | 0.98289 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.9843225 | 5x risk (5R) |
| Source outcome | MISSED_TRADE | Source/chart evidence |
| Connected-feed outcome | UNFILLED | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 18. EURUSD-20221021-AS-LDN-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-21 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | Asian 00:00-07:00 UTC | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | Yes | Step 2: Is Range Session? |
| Sweep During Session? | No | Step 3 when Range = Yes |
| Setup | Range Setup | BIAS=BEARISH -> RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-21T07:15:00Z | Closed M15 trigger |
| Entry | 0.97835 | First valid session boundary |
| Stop loss | 0.9788925 (5.425 pips) | 25% of reference range |
| Leg A target | 0.97618 | 75% at one range projection (4R) then 25% to BE/5R |
| TP5 | 0.9756375 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

## 19. EURUSD-20221021-LDN-NY-01

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Date | 2022-10-21 | Stored benchmark date |
| Contract | v2.23 / REPLAY_REQUIRED | Evidence compatibility |
| Reference | London 07:00-12:00 UTC | Completed reference session |
| Entry session | New_York | Following execution session |
| Bias | Bearish | Step 1: Determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | BIAS=BEARISH -> RANGE?=NO -> SWEEP?=N/A -> TREND_SETUP |
| Direction | Short | Frozen bias direction |
| Signal | 2022-10-21T12:45:00Z | Closed M15 trigger |
| Entry | 0.97674 | Middle of reference range |
| Stop loss | 0.978495 (17.55 pips) | 25% of reference range |
| Leg A target | 0.96972 | 75% at 4R then trail remaining 25% |
| TP5 | 0.967965 | 5x risk (5R) |
| Source outcome | STOP_LOSS | Source/chart evidence |
| Connected-feed outcome | STOP_LOSS | Bar-by-bar simulation |
| Evidence | USER_CONFIRMED_TRUTH | Validation status |

