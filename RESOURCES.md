# Resource Requirements

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

What is needed to run Session Trade Codex, what it consumes, and what it costs. Figures are
measured from the current installation where possible.

---

## 1. Platform

| Requirement | Detail | Why |
|---|---|---|
| **Windows** | Windows 10 or 11 | The `MetaTrader5` Python package is Windows-only. There is no macOS or Linux path — this is a hard constraint from the vendor, not a design choice. |
| Python | 3.10 or newer; **3.14 currently installed** | The code uses `from __future__ import annotations` throughout, so it is syntactically 3.9-compatible, but is only tested on the installed interpreter. |
| Local disk | ~200 MB free for a year of operation | See §5 |
| MetaTrader 5 terminal | installed, running, and logged in **at the moment of every run** | The Python API attaches to a running terminal; it cannot start one or log in |
| Always-on machine or a reliable morning routine | the schedule fires at 08:05, 08:15–11:00 and 11:05 UTC | A machine asleep at 08:05 UTC produces no baseline |

**Not required:** "Allow algorithmic trading" in MT5. No gate reads `expert_allowed`. Leave it
off — it only widens the path through which an order could reach the broker.

---

## 2. Software dependencies

From `requirements.txt` — three packages, deliberately minimal:

| Package | Purpose | Notes |
|---|---|---|
| `MetaTrader5` | the only broker interface | Windows-only; must match the terminal's bitness |
| `matplotlib` | chart rendering | the heaviest dependency, used only for `chart.png` |
| `PyYAML` | strategy config loading | |

Standard library only for everything else: `sqlite3` for the journal, `argparse` for the CLI,
`unittest` for tests, `hashlib` for the config hash. No web framework, no data-science stack, no
network access beyond the local terminal.

```powershell
pip install -r requirements.txt
```

**No pinned versions.** `requirements.txt` names three packages with no version constraints, so
two installations can differ. If reproducibility matters — and for a strategy whose evidence base
depends on identical calculation, it does — pin them.

---

## 3. Accounts and market data

| Resource | Current value | Notes |
|---|---|---|
| Broker | VT Markets | |
| Server | `VTMarkets-Demo` | Gate G1 requires an exact match |
| Account | demo, login ending `985` | Suffix matching is a weak fallback — set `SSPF_ALLOWED_LOGINS` for an exact allowlist. A live account fails closed |
| Account balance | ~$987 | Drives position sizing; the $20 daily cash cap is currently non-binding at this balance |
| Account currency | as configured at the broker | All risk figures are in this currency |
| Instruments | logical `EURUSD`, `GBPUSD`, `USDJPY`, `XAUUSD` | Broker strings mapped in config (`XAUUSD` → `XAUUSD.crp`); the gateway calls `symbol_select` if needed |

**Data requirements per run:** 36 closed M15 candles for the Asian session, up to 8 for the
execution window, one live tick per symbol, and symbol metadata (digits, tick size, volume
min/max/step, minimum stop distance). All are standard broker-provided data — no paid feed, no
external data vendor, no news API.

**A quiet dependency:** deriving the broker's UTC offset requires **at least two symbols quoting
fresh ticks simultaneously**. If only one instrument is trading, analysis fails with no artifact
(finding A6). Budget for this on thin sessions and around the Monday open.

---

## 4. Human resource — the real cost

The software is cheap; the discipline is not.

| Activity | Frequency | Time |
|---|---|---|
| Morning health check and journal sync | daily | 2 min |
| Review tickets for 4 symbols | daily | 10–15 min |
| Visual verification in MT5 before entry | per proposal | 5 min |
| Manual order placement | per accepted proposal | 2 min |
| Position management — 75% off at 4R, stop to entry | per open position | 5–10 min, at unpredictable moments during 07:00–16:00 UTC |
| Journal review and outcome recording | weekly | 30 min |
| **Realistic daily commitment** | | **20–40 minutes, anchored to M15 checks during 07:00–16:00 UTC** |

That window is **13:30–15:30 Myanmar time**. The strategy is not compatible with being
unavailable in that block. The Asian range builds unattended from 22:00 UTC (04:30 MMT); only the
nine-hour London execution window needs you.

**Skills assumed:** running commands in PowerShell, reading a JSON file, placing and modifying
limit orders in MT5, and the self-discipline to accept a `NO_TRADE` without re-running the
analysis hoping for a different answer.

---

## 5. Storage and growth

Measured from 28 stored analyses:

| Item | Size |
|---|---|
| `analysis.json` | ~2.7 KB |
| `ticket.md` | ~0.9 KB |
| `chart.png` | ~45 KB — 96% of the total |
| **Per analysis** | **~56 KB** |
| Current `outputs/` | 1.8 MB (28 runs) |
| Current journal | 124 KB |

**Projected:** 4 symbols × 3 scheduled passes × ~250 trading days ≈ 3,000 analyses ≈ **165 MB per
year**, almost entirely PNG. Manual re-runs add to this.

Two consequences worth planning for:

- The folder is OneDrive-synced, so every chart is uploaded. 165 MB/year is tolerable; a sweep
  monitor firing every 15 minutes instead of on qualifying events would not be.
- There is **no retention or supersession policy**. Superseded intraday runs are kept
  indefinitely alongside final ones, with nothing marking which is which.

---

## 6. Scheduling

Three weekday automations drive the daily cycle:

| Task | Time (UTC) | Purpose |
|---|---|---|
| range lock | 07:00 | Asian levels freeze; first analysis for all symbols |
| execution monitor | 07:00–16:00, after each M15 close | Detect a qualifying setup |
| window close | 09:00 | Final artifacts; expire unfilled signals |

**These definitions are not stored in this project** (finding A10). They are unversioned external
objects that cannot be reviewed, restored after a machine rebuild, or reconciled against a config
hash. Treat recreating them as a real task, not a footnote.

---

## 7. Financial cost

| Item | Cost |
|---|---|
| Software | £0 — all dependencies are open source |
| Data | £0 — broker-provided |
| Broker demo account | £0 |
| Machine | existing |
| **Capital at risk during the demo phase** | **£0** |
| Capital at risk if it ever goes live | 0.5% of equity per trade, 2% daily ceiling, 15% drawdown boundary |

The only material cost of this project is time and attention.

---

## 8. What is missing from the resource picture

| Gap | Consequence |
|---|---|
| No version control | No config-hash-to-commit traceability, which Stage 2 assumes. A machine failure loses the change history entirely. |
| No pinned dependency versions | Two installations can calculate differently |
| No backup of `data/sspf_journal.sqlite3` | The journal is the evidence base; OneDrive sync is not a backup, it propagates deletions |
| Automation definitions outside the project | Not restorable |
| No artifact retention policy | Unbounded growth, no supersession marking |

Initialising git and pinning `requirements.txt` are each a few minutes' work and close the first
two.
