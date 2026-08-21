# SSPF v2.2 Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `5b7ba0632925`
- Timestamp (UTC): 2026-08-10T07:54:51.109757+00:00
- Symbol: USDJPY
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 158.502 / 158.505 / 0.002999999999985903
- Session High / Low: None / None
- Range / Midpoint: None / None
- Efficiency Ratio: None → UNCLASSIFIED
- Session Bias: NONE
- Sweep: NO
- Setup: NONE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=USDJPY
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=3s
- FAIL — G2_DATA_INTEGRITY: candles are not a contiguous session-ending suffix

## Rejection reasons

- G2_DATA_INTEGRITY: candles are not a contiguous session-ending suffix

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
