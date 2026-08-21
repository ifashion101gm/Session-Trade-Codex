# SSPF v2.2 Trade Analysis Ticket

- Status: **APPROVED_FOR_MANUAL_ENTRY**
- Analysis ID: `d1ac42462410`
- Timestamp (UTC): 2026-08-10T08:07:53.892517+00:00
- Symbol: USDJPY
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 158.475 / 158.477 / 0.0020000000000095497
- Session High / Low: 158.457 / 157.652
- Range / Midpoint: 0.8050000000000068 / 158.0545
- Efficiency Ratio: 0.5794912559618242 → RANGE
- Session Bias: BULLISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=USDJPY
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.805, required=0.08
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BULLISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.201, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.03
- PASS — G10_DAILY_RISK: used+proposed=3.83, limit=9.88
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=08:07:53 UTC

## Proposed limit order — manual execution only

- Type: BUY_LIMIT
- Volume: 0.03 lots
- Entry: 157.65200000000002
- Protected SL: 157.451
- Actual R: 0.20100000000002183
- Take Profit: 158.657 (5R)
- Intended / Actual Risk: $4.94 / $3.83
- Expiry: 2026-08-10T11:00:00+00:00

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
