# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `4735dc0807a9`
- Strategy: SSPF_V2_2 v2.2 (config `47c20587123f3296`)
- Symbol: USDJPY
- Trading date: 2026-08-12
- Timestamp (UTC): 2026-08-12T08:54:09.082202+00:00
- Timestamp (Myanmar): 2026-08-12 15:24 MMT
- Asian session: 2026-08-12T00:00:00+00:00 → 2026-08-12T08:00:00+00:00
- Last closed execution candle: 2026-08-12T08:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 159.326 / 159.328 / 0.002

## Asian range (locked)

- High / Low: 159.461 / 159.2
- Range: 0.2610000000000241
- Midpoint: 159.3305
- Quartiles: 159.26524999999998 / 159.39575000000002
- Risk unit R (25% of range): 0.06525000000000603
- Efficiency ratio: 0.375478927203081 · Close location: 0.6590038314176613
- Session type: **BULLISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=USDJPY
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.261, allowed=[0.15, 1.2]
- PASS — G6_SPREAD: spread=0.002, maximum=0.03
- PASS — G7_SESSION_CLASSIFIED: type=BULLISH_TREND, ER=0.3755, close_location=0.6590
- FAIL — G8_SESSION_QUOTA: taken=1, allowed=1

## Reason codes

`TREND_SESSION` `TRADE_ALREADY_TAKEN`

## Rejection reasons

- G8_SESSION_QUOTA: taken=1, allowed=1

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
