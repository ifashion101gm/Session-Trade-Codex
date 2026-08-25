# ASIAN_SESSION_V1 v1.0 — Trade Analysis Ticket

- Status: **SIGNAL_ACCEPTED**
- Analysis ID: `6053413a4f24`
- Strategy: ASIAN_SESSION_V1 v1.0 (config `f10cfb4cb99a1bd8`)
- Symbol: EURUSD
- Trading date: 2026-08-25
- Timestamp (UTC): 2026-08-25T14:31:06.777786+00:00
- Timestamp (Myanmar): 2026-08-25 21:01 MMT
- Asian session: 2026-08-25T00:00:00+00:00 → 2026-08-25T07:00:00+00:00
- Last closed execution candle: 2026-08-25T14:15:00Z
- Account: DEMO `*****746` | Equity: $1000.00
- Bid / Ask / Spread: 1.167 / 1.16714 / 0.00014

## Asian range (locked)

- High / Low: 1.16704 / 1.16506
- Range: 0.001980000000000093
- Midpoint: 1.16605
- Quartiles: 1.165555 / 1.1665450000000002
- Risk unit R (25% of range): 0.0004950000000000232
- Efficiency ratio: 0.7676767676767144 · Close location: 0.08080808080804569
- Session type: **BEARISH_TREND**
- Setup: **TREND_CONTINUATION** SHORT

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VantageMarkets-Demo, login=*****746 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=EURUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=4s
- PASS — G4_SESSION_DATA: 28 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00198, allowed=[0.0015, 0.012]
- PASS — G6_SPREAD: spread=0.00014, maximum=0.0003
- PASS — G7_SESSION_CLASSIFIED: type=BEARISH_TREND, ER=0.7677, close_location=0.0808
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- PASS — G10_SETUP_DETECTED: setup=TREND_CONTINUATION SHORT
- PASS — G11_STRUCTURAL_STOP: not applicable to this setup
- PASS — G12_STOPS_LEVEL: distance=0.00049, broker minimum=0
- PASS — G13_VOLUME_BOUNDS: volume=0.1, allowed=[0.01, 100.0]
- PASS — G14_DAILY_RISK: used+proposed=4.90, limit=20.00
- PASS — G15_DRAWDOWN: drawdown=0.00%, maximum=15.00%
- PASS — G16_EXECUTION_WINDOW: now=2026-08-25T14:31:06.777786+00:00, window=[2026-08-25T07:00:00+00:00, 2026-08-25T16:00:00+00:00)

## Proposed signal — manual execution only

- Direction: SHORT
- Signal candle close (UTC): 2026-08-25T07:15:00+00:00
- Entry: 1.16605
- Stop loss: 1.1665400000000001
- Initial risk (1R): 0.0004900000000001015
- Partial target (75% off): 1.16409 (4R)
- TP2 (runner): 1.1636000000000002 (5R)
- Volume: 0.1 lots  (partial 0.08 / runner 0.02)
- Risk: $5.00 intended / $4.90 actual
- Risk basis: $1000.00 (lower of balance and equity)
- Signal expires: 2026-08-25T16:00:00+00:00
- Estimated cost: 0.327R  ->  net TP1 3.67R, net TP2 4.67R (gross 5.0R)

### Management sequence

1. Open the position with the original stop.
2. At 4R (1.16409): close 75%.
3. Move the remaining stop to entry (1.16605) and target 5R (1.1636000000000002).
4. Never move the initial stop farther away.
5. Do not re-enter this setup after the trade completes or is stopped.

## Reason codes

`TREND_SESSION` `MIDPOINT_RETRACEMENT`

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.
