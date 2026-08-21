# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `9324aa6f73b0`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: XAUUSD
- Trading date: 2026-08-14
- Timestamp (UTC): 2026-08-14T09:48:22.414906+00:00
- Timestamp (Myanmar): 2026-08-14 16:18 MMT
- Asian session: 2026-08-14T00:00:00+00:00 → 2026-08-14T08:00:00+00:00
- Last closed execution candle: 2026-08-14T09:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 4352.86 / 4353.13 / 0.27

## Asian range (locked)

- High / Low: None / None
- Range: None
- Midpoint: None
- Quartiles: None / None
- Risk unit R (25% of range): None
- Efficiency ratio: None · Close location: None
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=XAUUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- FAIL — G4_SESSION_DATA: expected 32-32 candles, received 0

## Reason codes

`INVALID_ASIAN_DATA`

## Rejection reasons

- G4_SESSION_DATA: expected 32-32 candles, received 0

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
