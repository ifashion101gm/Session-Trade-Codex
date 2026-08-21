# SSPF v2.2 Unified Trade Ticket

- Status: **APPROVED_FOR_MANUAL_ENTRY**
- Analysis ID: `659bb4bdb875`
- Timestamp (UTC): 2026-08-11T10:52:01.899183+00:00
- Symbol: GBPUSD
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 1.34982 / 1.3498299999999999 / 9.999999999843467e-06
- Session High / Low: 1.35159 / 1.34945
- Range / Midpoint: 0.0021400000000000308 / 1.35052
- Efficiency Ratio: 0.219178082191791 → RANGE
- Session Bias: BEARISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=GBPUSD
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=2s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.00214, required=0.0004
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BEARISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.00053, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.18
- PASS — G10_DAILY_RISK: used+proposed=9.54, limit=19.76
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=10:52:01 UTC

## Proposed limit order — manual execution only

- Type: SELL_LIMIT
- Volume: 0.18 lots
- Entry: 1.35159
- Protected SL: 1.3521200000000002
- Actual R: 0.0005300000000001415
- Take Profit: 1.34894 (5R)
- Partial Target: close 75% at 1.34945 (4.04R), then manually move SL to breakeven
- Intended / Actual Risk: $9.88 / $9.54
- Expiry: 2026-08-11T11:00:00+00:00

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
