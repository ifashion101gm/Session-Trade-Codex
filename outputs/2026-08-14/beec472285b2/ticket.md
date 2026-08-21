# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `beec472285b2`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: USDJPY
- Trading date: 2026-08-14
- Timestamp (UTC): 2026-08-14T09:49:19.839242+00:00
- Timestamp (Myanmar): 2026-08-14 16:19 MMT
- Asian session: 2026-08-14T00:00:00+00:00 → 2026-08-14T08:00:00+00:00
- Last closed execution candle: 2026-08-14T09:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 159.143 / 159.145 / 0.002

## Asian range (locked)

- High / Low: 159.504 / 159.148
- Range: 0.35599999999999454
- Midpoint: 159.326
- Quartiles: 159.237 / 159.415
- Risk unit R (25% of range): 0.08899999999999864
- Efficiency ratio: 0.6376404494382228 · Close location: 0.1629213483145888
- Session type: **BEARISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=USDJPY
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=2s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.356, allowed=[0.15, 1.2]
- PASS — G6_SPREAD: spread=0.002, maximum=0.03
- PASS — G7_SESSION_CLASSIFIED: type=BEARISH_TREND, ER=0.6376, close_location=0.1629
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 7 closed execution candle(s)

## Reason codes

`TREND_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 7 closed execution candle(s)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
