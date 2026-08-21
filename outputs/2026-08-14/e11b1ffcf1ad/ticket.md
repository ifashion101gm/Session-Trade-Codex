# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `e11b1ffcf1ad`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: GBPUSD
- Trading date: 2026-08-14
- Timestamp (UTC): 2026-08-14T09:48:51.604811+00:00
- Timestamp (Myanmar): 2026-08-14 16:18 MMT
- Asian session: 2026-08-14T00:00:00+00:00 → 2026-08-14T08:00:00+00:00
- Last closed execution candle: 2026-08-14T09:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.35228 / 1.35229 / 1e-05

## Asian range (locked)

- High / Low: 1.3513600000000001 / 1.34887
- Range: 0.0024900000000001032
- Midpoint: 1.3501150000000002
- Quartiles: 1.3494925 / 1.3507375000000001
- Risk unit R (25% of range): 0.0006225000000000258
- Efficiency ratio: 0.8955823293172136 · Close location: 0.9477911646585622
- Session type: **BULLISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=GBPUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=3s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00249, allowed=[0.0018, 0.015]
- PASS — G6_SPREAD: spread=1e-05, maximum=0.00035
- PASS — G7_SESSION_CLASSIFIED: type=BULLISH_TREND, ER=0.8956, close_location=0.9478
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 7 closed execution candle(s)

## Reason codes

`TREND_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 7 closed execution candle(s)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
