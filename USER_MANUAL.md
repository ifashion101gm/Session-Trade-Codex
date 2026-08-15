# User Manual — SESSION_FLOW_V1

How to run Session Trade Codex day to day. For the rules it applies see `SESSION_FLOW_V1_SPEC.md`;
for what it needs to run see `RESOURCES.md`.

**Before you start:** this tool applies *your* strategy and recommends; you execute. It cannot
place, change, or close an order, and it has no opinion about the market. Everything it produces
is your own rulebook applied to today's chart.

The project is in **Stage 1** (recommendation correctness) and is demo/shadow only until that
closes. See `STAGE1_QUALIFICATION.md`.

---

## 1. First-time setup

```powershell
cd "C:\Users\aungp\OneDrive\Documents\ChatGPT\Session Trade Codex"
pip install -r requirements.txt
python sspf.py health
python sspf.py readiness
```

A good result prints `"strategy_id": "ASIAN_SESSION_V1"`, your masked login, `"account_type":
"demo"`, server `VTMarkets-Demo`, and for each symbol `"available": true` plus `"spread_ok"`.

Then confirm in MT5: **Tools → Options → Expert Advisors → Allow algorithmic trading is OFF.**
Nothing here needs it, and leaving it off removes a path to your broker.

`readiness` is the authoritative release check. Do not begin manual day trading unless it prints
`READY_FOR_MANUAL_DAY_TRADING`; a failing check names the remaining action.

---

## 2. The daily rhythm

The entry window is **07:00–16:00 UTC = 13:30–22:30 Myanmar.**

| Time (UTC) | Myanmar | What happens |
|---|---|---|
| 22:00 | 04:30 | Asian session starts building (previous calendar day) |
| 07:00 | 13:30 | **Range locks.** High and low are frozen and never change |
| 07:00–16:00 | 13:30–22:30 | Execution window — watch for a setup |
| 16:00 | 22:30 | Unfilled signals expire |

### The engine runs TWICE a day, at the reference closes

| Run | UTC | Myanmar | Produces |
|---|---|---|---|
| 1 | 07:00 | 13:30 | the London entry plan, from the completed Asian range |
| 2 | 12:00 | 18:30 | the New York entry plan, from the completed London range |

Each run reads exactly one range: London reads Asian, New York reads London. Nothing else.
See `SESSION_FLOW_V1_SPEC.md` §5.

RANGE and TREND entries are limits you can place the moment the run finishes. A SWEEP entry
depends on a candle that has not printed yet — see §5.3a, unsigned.

### At 07:05, check the system

```powershell
python sspf.py health
python sspf.py journal sync
```

Stop if either reports an unhealthy connection, the wrong account or server, an unavailable
symbol, or an ambiguous journal match. An unhealthy journal deliberately fails the risk gates.

### Then analyse

```powershell
python sspf.py analyze --symbol EURUSD
python sspf.py analyze --symbol GBPUSD
python sspf.py analyze --symbol USDJPY
python sspf.py analyze --symbol XAUUSD
```

Use the **logical** symbol names. `XAUUSD` maps to the broker string `XAUUSD.crp` via
`symbols.XAUUSD.broker_symbol`, so suffix changes never touch the strategy or the journal. The engine is run at the reference close, not continuously. If the session is RANGE and you are
watching for a sweep, re-run when a candle closes back inside the boundary.

Add `--trading-date YYYY-MM-DD` to reconstruct a past day. Historical runs never produce an
accepted signal, because G15 requires the live time to be inside the window.

---

## 3. Reading a ticket

Artifacts land in `outputs/<trading-date>/<analysis-id>/` as `analysis.json`, `ticket.md` and
`chart.png`. Symbols are named logically (`XAUUSD`), with the broker string recorded alongside.

```
- Status: **SIGNAL_ACCEPTED**
- Analysis ID: `a1b2c3d4e5f6`
- Strategy: ASIAN_SESSION_V1 v1.0 (config `2530b751134fbf6e`)

## Asian range (locked)
- High / Low: 1.16800 / 1.16400        ← verify these two on your chart first
- Range: 0.00400
- Risk unit R (25% of range): 0.00100
- Efficiency ratio: 0.25 · Close location: 0.50
- Session type: **RANGE**
- Setup: **SWEEP** LONG

## Gate evaluation
- PASS — G11_STRUCTURAL_STOP: stop=1.16300, must be beyond 1.16322 ...
  ... 15 gates in total

## Proposed signal — manual execution only
- Entry: 1.16400          ← the long sweep candle's body low
- Stop loss: 1.16300
- Initial risk (1R): 0.00100
- Partial target (75% off): 1.16800 (opposite session boundary)
- TP2 (runner): 1.16900 (5R)
- Volume: 0.05 lots  (partial 0.04 / runner 0.01)   ← enter as printed
- Estimated cost: 0.020R  ->  net TP1 3.98R, net TP2 4.98R (gross 5.0R)

## Reason codes
`RANGE_SESSION` `SELL_SIDE_SWEEP` `CLOSE_BACK_INSIDE` `STRUCTURAL_STOP_VALID`
```

### Two statuses only

| Status | Meaning |
|---|---|
| `SIGNAL_ACCEPTED` | every gate passed and a tradeable plan exists |
| `NO_TRADE` | at least one gate failed, or no setup qualified. The reason codes say which |

A `NO_TRADE` is an answer, not a failure. Do not re-run hoping for a different one.

---

## 4. Placing the trade

1. **Verify on your own chart:** symbol and trading date → Asian high, low, midpoint → the signal
   candle → entry, stop, TP1, TP2, volume.
2. If anything disagrees, **do not trade**. A mismatch means either the ticket or your chart is
   wrong and you do not yet know which.
3. Open the order window (`F9`).
4. Enter the volume **exactly as printed**. It has already passed the volume, daily-risk and
   drawdown gates; a hand-sized lot passes none of them and cannot be reconciled by the journal.
5. Use the labelled entry: **sweep candle body**, **session boundary**, or **50% midpoint**. Skip a missed entry; do not chase.
6. Run `python sspf.py journal sync` so the order is matched to its signal.

---

## 5. Managing the position

Management is setup-specific:

1. Open with the original stop.
2. **Sweep/Range:** at the opposite boundary, close 75% and move the remaining stop to entry.
3. **Trend:** at +4R, close 75%, move the remaining stop to entry, and target 5R.
4. Never move the initial stop farther away.
5. Do not re-enter the same setup after the trade completes or is stopped.

```powershell
python sspf.py journal sync
python sspf.py monitor --analysis-id a1b2c3d4e5f6
```

`monitor` reports your current R and the next action. It changes nothing, and it will never say a
partial close or breakeven move happened unless MT5 data shows it.

**No trailing stops.** Trailing is explicitly out of scope for v1 and may only arrive as a
separately tested version. A trailed trade is not rule-compliant evidence.

---

## 6. The three setups

| Setup | When | Entry |
|---|---|---|
| `SWEEP` | RANGE session, price takes liquidity beyond a boundary and closes back inside | sweep candle close |
| `RANGE_REJECTION` | RANGE session, no sweep, a boundary touch rejected by a candle closing back with direction | rejection candle close |
| `TREND_CONTINUATION` | BULLISH/BEARISH_TREND session, price retraces into the 45–55% midpoint zone with a confirming candle | confirmation candle close |

Priority is Sweep → Range Rejection → Trend. One accepted trade per symbol per session.

---

## 7. Exit codes

| Code | Meaning |
|---|---|
| `0` | signal accepted / healthy / stage passed |
| `1` | exception — **no artifact was written**; the run did not happen |
| `2` | unsupported symbol |
| `3` | analysis completed, no trade |
| `4` | journal sync unhealthy or ambiguous |
| `5` | lifecycle stage failed |
| `6` | not ready for manual day trading; inspect the readiness checks |

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `MT5 initialization failed` | terminal not running or not logged in | start MT5 and log in; the tool cannot |
| `MT5 symbol not found or not selectable` | broker symbol wrong or not in Market Watch | check `symbols.<name>.broker_symbol`; the gateway calls `symbol_select` automatically |
| `Broker UTC offset could not be verified…` | fewer than two symbols quoting fresh ticks | wait; common at thin hours. No artifact is written |
| `G4_SESSION_DATA` candle-count message | the Asian session is incomplete | run after 07:00 UTC |
| `G5_RANGE_BOUNDS` fails | range outside this symbol's configured min/max | expected on very quiet or very wild nights |
| `G6_SPREAD` fails | spread above this symbol's limit | wait for spreads to normalise |
| `G7_SESSION_CLASSIFIED` fails | `UNCERTAIN` — high efficiency but a middling close | expected; the strategy stands aside |
| `G10_STRUCTURAL_STOP` fails | the fixed 25% stop does not clear the sweep wick | **correct behaviour.** Never widen the stop to make it fit |
| `G15_EXECUTION_WINDOW` fails | outside 07:00–16:00 UTC, or a historical date | expected |

### Expect a lot of `NO_TRADE`

A sweep is only tradeable when the reclaim candle closes back to within roughly a quarter of the
range above the Asian low (mirrored for shorts). That is a direct consequence of the fixed 25%
stop. If sweeps are refused essentially every day, the buffer parameters need your review — see
`STRATEGY_SPEC.md` §7.

---

## 9. Release-gate commands

```powershell
python sspf.py stage analysis --analysis PATH_TO_ANALYSIS.json --ticket PATH_TO_TICKET.md
python sspf.py stage profitability --trades PATH_TO_TRADES.json
python sspf.py journal verify --analysis-id ANALYSIS_ID --outcome match --note "chart and ticket reconciled"
python sspf.py readiness
```

During shadow qualification, verify each fresh ticket against MT5. Record `match` only when the
session levels, signal candle, entry, stop, targets and volume all agree; otherwise record
`mismatch` and stop qualification. Readiness requires 20 matches under the active config and zero
mismatches. A new config hash starts a new evidence set automatically.

**Stage 1** checks an artifact faithfully represents your rules. Closing Stage 1 is the gate to
day trading; the checklist is in `STAGE1_QUALIFICATION.md`.

**Stage 2** scores a backtest trade log. **No backtest engine exists yet**, so this command has
nothing to score — building it is the largest outstanding work. Each setup must be backtested
separately, or a profitable one will hide a losing one.

---

## 10. Rules of use

1. An accepted signal means the configured rules passed. Nothing more.
2. Never use an expired signal — generate a fresh analysis.
3. Never re-run an analysis hoping for a different answer.
4. Never size a position by hand.
5. Never widen a stop, and never move it before its trigger.
6. Never trail in v1.
7. Never skip visual verification.
8. Change one configuration value at a time, recording the hash before and after.

---

Analysis only. Levels and calculated volume are proposals, not automated signals. Verify every
value against your own chart and broker order window before placing or managing an order manually.
