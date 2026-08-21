# SSPF v2.2 Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `b2f0361b1a4c`
- Timestamp (UTC): 2026-08-10T07:54:45.390286+00:00
- Symbol: GBPUSD
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 1.34939 / 1.3494 / 9.999999999843467e-06
- Session High / Low: 1.34978 / 1.34832
- Range / Midpoint: 0.0014600000000000168 / 1.34905
- Efficiency Ratio: 0.13394495412847432 → RANGE
- Session Bias: BULLISH
- Sweep: NO
- Setup: NONE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=GBPUSD
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.00146, required=0.0004
- FAIL — G5_BREACH_QUALITY: sweep conflicts with bias
- FAIL — G6_BIAS_AGREEMENT: bias=BULLISH, setup=NONE
- PASS — G7_STOP_PROTECTION: protected

## Rejection reasons

- G5_BREACH_QUALITY: sweep conflicts with bias
- G6_BIAS_AGREEMENT: bias=BULLISH, setup=NONE

## Warnings

- Only bias-conflicting sweep(s) qualified

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
