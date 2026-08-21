# SSPF v2.1 Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `2f22392cb981`
- Timestamp (UTC): 2026-08-09T15:18:16.161833+00:00
- Symbol: EURUSD
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 1.15584 / 1.15589 / 5.0000000000105516e-05
- Session High / Low: 1.15256 / 1.15179
- Range / Midpoint: 0.0007699999999999374 / 1.1521750000000002
- Efficiency Ratio: 0.031976744186059274 → RANGE
- Session Bias: BULLISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo
- PASS — G3_UNIVERSE: symbol=EURUSD
- PASS — G2_DATA_INTEGRITY: valid session
- FAIL — G4_RANGE_FLOOR: range=0.00077, required=0.002
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BULLISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.00019, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.25
- PASS — G10_DAILY_RISK: used+proposed=4.75, limit=19.76
- PASS — G11_DRAWDOWN: drawdown=0.00%
- FAIL — G12_EXECUTION_WINDOW: now=15:18:16 UTC

## Proposed limit order — manual execution only

- Type: BUY_LIMIT
- Volume: 0.25 lots
- Entry: 1.15179
- Protected SL: 1.1516000000000002
- Actual R: 0.00018999999999991246
- Take Profit: 1.15274 (5R)
- Intended / Actual Risk: $4.94 / $4.75
- Expiry: 2026-08-07T11:00:00+00:00

## Rejection reasons

- G4_RANGE_FLOOR: range=0.00077, required=0.002
- G12_EXECUTION_WINDOW: now=15:18:16 UTC

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
