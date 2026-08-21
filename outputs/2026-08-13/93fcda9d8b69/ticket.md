# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `93fcda9d8b69`
- Strategy: SSPF_V2_2 v2.2 (config `10304d115519bcc1`)
- Symbol: XAUUSD
- Trading date: 2026-08-13
- Timestamp (UTC): 2026-08-13T08:53:08.422844+00:00
- Timestamp (Myanmar): 2026-08-13 15:23 MMT
- Asian session: 2026-08-13T00:00:00+00:00 → 2026-08-13T08:00:00+00:00
- Last closed execution candle: 2026-08-13T08:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 4376.39 / 4376.65 / 0.26

## Asian range (locked)

- High / Low: 4449.7 / 4368.88
- Range: 80.81999999999971
- Midpoint: 4409.29
- Quartiles: 4389.085 / 4429.495
- Risk unit R (25% of range): 20.204999999999927
- Efficiency ratio: 0.5507300173224496 · Close location: 0.012249443207124292
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=XAUUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- FAIL — G5_RANGE_BOUNDS: range=80.82, allowed=[2, 25]

## Reason codes

`INVALID_ASIAN_RANGE`

## Rejection reasons

- G5_RANGE_BOUNDS: range=80.82, allowed=[2, 25]

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
