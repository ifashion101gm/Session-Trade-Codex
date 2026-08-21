# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `fc4729b7aac8`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: USDJPY
- Trading date: 2026-08-13
- Timestamp (UTC): 2026-08-13T10:07:18.726466+00:00
- Timestamp (Myanmar): 2026-08-13 16:37 MMT
- Asian session: 2026-08-13T00:00:00+00:00 → 2026-08-13T08:00:00+00:00
- Last closed execution candle: 2026-08-13T09:45:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 159.334 / 159.336 / 0.002

## Asian range (locked)

- High / Low: 159.485 / 159.179
- Range: 0.3060000000000116
- Midpoint: 159.332
- Quartiles: 159.2555 / 159.4085
- Risk unit R (25% of range): 0.0765000000000029
- Efficiency ratio: 0.09477124183004988 · Close location: 0.6013071895424527
- Session type: **RANGE**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=USDJPY
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=3s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.306, allowed=[0.15, 1.2]
- PASS — G6_SPREAD: spread=0.002, maximum=0.03
- PASS — G7_SESSION_CLASSIFIED: type=RANGE, ER=0.0948, close_location=0.6013
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 8 closed execution candle(s)

## Reason codes

`RANGE_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 8 closed execution candle(s)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
