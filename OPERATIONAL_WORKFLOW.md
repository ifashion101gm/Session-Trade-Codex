# ASIAN_SESSION_V1 Operational Workflow

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

The supported daily workflow. It describes what the application actually implements.

All times are UTC. Myanmar time (UTC+6:30) is shown for convenience only.

---

## 1. Prepare MT5

1. Start the local MetaTrader 5 terminal and connect to the configured demo account.
2. Confirm the account ends in `985` and the server is `VTMarkets-Demo`.
3. **Algorithmic trading must stay OFF.** Nothing here needs it; leaving it off removes a path
   through which an order could reach the broker.
4. Run:

```powershell
python sspf.py health
python sspf.py journal sync
python sspf.py readiness
```

Stop if either reports an unhealthy connection, the wrong account or server, an unavailable
symbol, a spread above the configured limit, or an ambiguous journal match.

Before Stage 1 closes, reconcile every generated ticket and record the result:

```powershell
python sspf.py journal verify --analysis-id ANALYSIS_ID --outcome match --note "checked against MT5"
```

Use `mismatch` when any value disagrees. Never relabel or delete a mismatch to make the gate pass.

---

## 2. The day's shape

| Phase | UTC | Myanmar | What happens |
|---|---|---|---|
| Asian range construction | 22:00–07:00 | 04:30–13:30 | 36 M15 candles accumulate. Nothing is decided |
| **Range locks** | 07:00 | 13:30 | High, low, range, midpoint and quartiles freeze permanently |
| Execution window | 07:00–16:00 | 13:30–22:30 | 36 M15 candles are watched for one qualifying setup |
| Window closes | 09:00 | 15:30 | Unfilled signals expire |

The Asian session crosses midnight. Its **trading date is the date it ends**, so the session
beginning 22:00 on the 10th belongs to the 11th.

---

## 3. Analyse during the window

For scheduled checks, configure Windows Task Scheduler to invoke the version-controlled entrypoint
`powershell.exe -NoProfile -File scripts/run_session_check.ps1`. The script fails closed when the
health or readiness gate fails and treats an ordinary `NO_TRADE` result as a completed analysis.

```powershell
python sspf.py analyze --symbol EURUSD
python sspf.py analyze --symbol GBPUSD
python sspf.py analyze --symbol USDJPY
python sspf.py analyze --symbol XAUUSD
```

Re-run after each M15 close. A setup can appear at any of the eight execution candles, and the
engine only ever considers **closed** candles — an incomplete candle is invisible to it.

The engine calculates, in this order:

- the locked Asian high, low, range, midpoint, quartiles and the 25% risk unit from exactly 36
  closed M15 candles;
- efficiency ratio and close location, giving `RANGE`, `BULLISH_TREND`, `BEARISH_TREND` or
  `UNCERTAIN`;
- the first qualifying setup in priority order — `SWEEP`, then `RANGE_REJECTION`, then
  `TREND_CONTINUATION`;
- setup-specific entry (sweep body, session boundary or midpoint), a stop at exactly 25% of the
  Asian range, a setup-specific partial target and a 5R runner target;
- broker-normalised volume from 0.5% of equity;
- all fifteen environment, data, range, cost, classification, quota, structural, broker, risk and
  timing gates.

`UNCERTAIN` sessions produce no trade. Anything incomplete, stale, contradictory, out of bounds or
outside the window is also `NO_TRADE`, always with a reason code.

---

## 4. Review the ticket

Each run writes `analysis.json`, `ticket.md` and `chart.png` beneath
`outputs/<trading-date>/<analysis-id>/`.

Before acting, verify in MT5:

1. Symbol and trading date.
2. Asian high, low and midpoint, and that the session really is 22:00–07:00.
3. Session type, setup, and the signal candle.
4. Entry, stop loss, TP1, TP2, volume, spread and expiry.
5. Every gate shows `PASS` and the status is `SIGNAL_ACCEPTED`.

An accepted signal means only that the configured rules passed. It is not a prediction.

---

## 5. Execute manually

Enter the trade yourself in MT5 and recheck symbol, direction, volume, entry, stop and targets
before confirming. Use only the ticket's exact pending-entry level; skip the setup rather than
chasing price.

Signals expire at 16:00 UTC. Do not use an expired ticket; generate a fresh analysis.

---

## 6. Manage manually

```powershell
python sspf.py journal sync
python sspf.py monitor --analysis-id ANALYSIS_ID
```

The management sequence depends on the setup:

1. Open with the original stop.
2. **Sweep/Range:** at the opposite boundary, close **75%** and move the stop to entry.
3. **Trend:** at **+4R**, close **75%**, move the remaining stop to entry, and target **5R**.
4. Never move the initial stop farther away.
5. Do not re-enter the same setup after the trade completes or is stopped.

`monitor` reports the matched MT5 item, current R and the next action. It never changes anything,
and never claims a partial close or breakeven move happened unless MT5 confirms it.

**No trailing stops in v1.** Trailing may only arrive as a separately tested strategy version.

---

## 7. Keep the audit trail

Retain the generated artifacts and the SQLite journal. Every evaluation — including every refusal
— is recorded with a stable reason code, config hash, schema version, and embedded configuration
snapshot. This lets a ticket be reconstructed even after the active configuration changes.

Use Stage 1 to verify ticket conformance. Stage 2 requires a backtest, which does not exist yet;
each of the three setups must be backtested separately, or a profitable setup will hide a losing
one. Passing either stage does not authorise live or automated execution.
