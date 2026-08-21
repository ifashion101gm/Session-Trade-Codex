# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `2e69f8ecabd1`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: GBPUSD
- Trading date: 2026-08-13
- Timestamp (UTC): 2026-08-13T11:08:51.434426+00:00
- Timestamp (Myanmar): 2026-08-13 17:38 MMT
- Asian session: 2026-08-13T00:00:00+00:00 → 2026-08-13T08:00:00+00:00
- Last closed execution candle: 2026-08-13T10:45:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.34893 / 1.34894 / 1e-05

## Asian range (locked)

- High / Low: 1.35007 / 1.3474300000000001
- Range: 0.0026399999999999757
- Midpoint: 1.3487500000000001
- Quartiles: 1.34809 / 1.3494100000000002
- Risk unit R (25% of range): 0.0006599999999999939
- Efficiency ratio: 0.5454545454545914 · Close location: 0.3219696969696224
- Session type: **BEARISH_TREND**
- Setup: **TREND_CONTINUATION** SHORT

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=GBPUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00264, allowed=[0.0018, 0.015]
- PASS — G6_SPREAD: spread=1e-05, maximum=0.00035
- PASS — G7_SESSION_CLASSIFIED: type=BEARISH_TREND, ER=0.5455, close_location=0.3220
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- PASS — G10_SETUP_DETECTED: setup=TREND_CONTINUATION SHORT
- PASS — G11_STRUCTURAL_STOP: not applicable to this setup
- PASS — G12_STOPS_LEVEL: distance=0.00066, broker minimum=0
- PASS — G13_VOLUME_BOUNDS: volume=0.07, allowed=[0.01, 100.0]
- PASS — G14_DAILY_RISK: used+proposed=4.62, limit=19.76
- PASS — G15_DRAWDOWN: drawdown=0.00%, maximum=15.00%
- FAIL — G16_EXECUTION_WINDOW: now=2026-08-13T11:08:51.434426+00:00, window=[2026-08-13T08:00:00+00:00, 2026-08-13T11:00:00+00:00)

## Proposed signal — manual execution only

- Direction: SHORT
- Signal candle close (UTC): 2026-08-13T10:45:00+00:00
- Entry: 1.3487500000000001
- Stop loss: 1.3494100000000002
- Initial risk (1R): 0.000660000000000105
- Partial target (75% off): 1.3461100000000001 (4R)
- TP2 (runner): 1.34545 (5R)
- Volume: 0.07 lots  (partial 0.06 / runner 0.01)
- Risk: $4.94 intended / $4.62 actual
- Risk basis: $987.82 (lower of balance and equity)
- Signal expires: 2026-08-13T11:00:00+00:00
- Estimated cost: 0.045R  ->  net TP1 3.95R, net TP2 4.95R (gross 5.0R)

### Management sequence

1. Open the position with the original stop.
2. At 4R (1.3461100000000001): close 75%.
3. Trail the remaining 25% toward 5R (1.34545) or further.
4. Never move the initial stop farther away.
5. Do not re-enter this setup after the trade completes or is stopped.

## Reason codes

`TREND_SESSION` `MIDPOINT_RETRACEMENT` `OUTSIDE_EXECUTION_WINDOW`

## Rejection reasons

- G16_EXECUTION_WINDOW: now=2026-08-13T11:08:51.434426+00:00, window=[2026-08-13T08:00:00+00:00, 2026-08-13T11:00:00+00:00)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
