# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `af3a15ee9ce3`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: XAUUSD
- Trading date: 2026-08-14
- Timestamp (UTC): 2026-08-14T09:54:48.726681+00:00
- Timestamp (Myanmar): 2026-08-14 16:24 MMT
- Asian session: 2026-08-14T00:00:00+00:00 → 2026-08-14T08:00:00+00:00
- Last closed execution candle: 2026-08-14T09:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 4354.79 / 4355.06 / 0.27

## Asian range (locked)

- High / Low: 4361.98 / 4310.99
- Range: 50.98999999999978
- Midpoint: 4336.485
- Quartiles: 4323.737499999999 / 4349.2325
- Risk unit R (25% of range): 12.747499999999945
- Efficiency ratio: 0.25024514610708515 · Close location: 0.6405177485781525
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=XAUUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- FAIL — G5_RANGE_BOUNDS: range=50.99, allowed=[2, 25]

## Reason codes

`INVALID_ASIAN_RANGE`

## Rejection reasons

- G5_RANGE_BOUNDS: range=50.99, allowed=[2, 25]

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
