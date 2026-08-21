# SSPF v2.2 Unified Trade Ticket

- Status: **APPROVED_FOR_MANUAL_ENTRY**
- Analysis ID: `e65ad68d53da`
- Timestamp (UTC): 2026-08-11T10:09:20.347237+00:00
- Symbol: XAUUSD.crp
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 4373.57 / 4373.84 / 0.27000000000043656
- Session High / Low: 4435.08 / 4356.69
- Range / Midpoint: 78.39000000000033 / 4395.885
- Efficiency Ratio: 0.2957242293669179 → RANGE
- Session Bias: BEARISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=XAUUSD.crp
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=78.39, required=10.8
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BEARISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=19.598, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.01
- PASS — G10_DAILY_RISK: used+proposed=19.60, limit=19.76
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=10:09:20 UTC

## Proposed limit order — manual execution only

- Type: SELL_LIMIT
- Volume: 0.01 lots
- Entry: 4435.08
- Protected SL: 4454.678
- Actual R: 19.597999999999956
- Take Profit: 4337.09 (5R)
- Partial Target: close 75% at 4356.69 (4.00R), then manually move SL to breakeven
- Intended / Actual Risk: $19.76 / $19.60
- Expiry: 2026-08-11T11:00:00+00:00

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
