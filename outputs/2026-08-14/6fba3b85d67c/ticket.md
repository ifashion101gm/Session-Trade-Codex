# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `6fba3b85d67c`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: EURUSD
- Trading date: 2026-08-14
- Timestamp (UTC): 2026-08-14T09:53:43.804896+00:00
- Timestamp (Myanmar): 2026-08-14 16:23 MMT
- Asian session: 2026-08-14T00:00:00+00:00 → 2026-08-14T08:00:00+00:00
- Last closed execution candle: 2026-08-14T09:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.15527 / 1.15528 / 1e-05

## Asian range (locked)

- High / Low: 1.15512 / 1.15321
- Range: 0.0019099999999998563
- Midpoint: 1.1541649999999999
- Quartiles: 1.1536875 / 1.1546425
- Risk unit R (25% of range): 0.00047749999999996406
- Efficiency ratio: 0.8900523560210276 · Close location: 0.9842931937172896
- Session type: **BULLISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=EURUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=2s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00191, allowed=[0.0015, 0.012]
- PASS — G6_SPREAD: spread=1e-05, maximum=0.0003
- PASS — G7_SESSION_CLASSIFIED: type=BULLISH_TREND, ER=0.8901, close_location=0.9843
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 7 closed execution candle(s)

## Reason codes

`TREND_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 7 closed execution candle(s)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
