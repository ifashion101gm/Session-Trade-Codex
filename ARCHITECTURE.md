# Architecture — ASIAN_SESSION_V1

Describes the code as it exists on 2026-08-11, implementing **ASIAN_SESSION_V1 v1.0**. For the rules the code implements see
`STRATEGY_SPEC.md`; for known defects see `AUDIT_REPORT.md`.

---

## 1. Shape of the system

Session Trade Codex is a single-process Python CLI. There is no server, no scheduler inside the project, no
network call other than the local MT5 terminal, and no shared state beyond one SQLite file and
the `outputs/` tree.

```
MetaTrader 5 terminal (local, read-only)
        │
        ▼
mt5_gateway.MT5ReadOnlyGateway ─── the only module that imports MetaTrader5 from the package
        │  account · symbol_spec · tick · broker_utc_offset · candles
        │  loss_for_one_lot · positions · orders · deals
        ▼
cli.analyze_command  ── orchestration: resolves the session window, syncs the journal,
        │                 fetches candles, then calls the engine
        ├──────────────► journal.Journal          (SQLite: analyses · matches · sync_state)
        │                    risk_stats() ─┐
        ▼                                  │
engine.analyze(...)  ◄─────────────────────┘  pure function; every input injected
        │  lock levels → classify → detect setup → prices → risk → 15 gates
        ▼
models.AnalysisResult  ── status derived, never assigned
        │
        ├──► render.write_artifacts ──► outputs/<trading-date>/<analysis-id>/
        │                                  analysis.json · ticket.md · chart.png
        └──► journal.record
                     │
                     ▼
        lifecycle.assess_analysis / assess_profitability   (offline release gate)
                     │
                     ▼
             Human review → manual MT5 execution
```

---

## 2. Module ownership

One concern per module. Nothing below owns a concern listed against another module.

| Module | Owns | Must not |
|---|---|---|
| `config.py` | Loading and freezing `strategy.yaml`; the `config_hash` | contain strategy logic |
| `models.py` | Data shapes (`Candle`, `SymbolSpec`, `AccountSnapshot`, `Gate`, `AnalysisResult`) and **derived** status | perform I/O or calculation beyond derivation |
| `mt5_gateway.py` | Every MT5 call, timestamp normalisation, quote-refresh retry | expose any order-mutating call — enforced by `tests/test_safety.py` |
| `engine.py` | Level locking, classification, the three setup detectors, and all fifteen gates | import MT5, read the clock, touch the filesystem |
| `journal.py` | SQLite persistence, MT5↔analysis reconciliation, risk statistics | decide setups |
| `render.py` | `ticket.md`, `chart.png`, and the fixed `DISCLAIMER` constant | recalculate anything |
| `lifecycle.py` | The two-stage release gate, read from `lifecycle.json` | be invoked from the analysis path |
| `cli.py` | Argument parsing, orchestration, exit codes | contain formulas |

### The purity rule

`engine.analyze()` takes `now`, `account`, `spec`, `tick`, `session_candles`, `execution_candles`,
`one_lot_loss`, `daily_used_cash`, `drawdown_percent`, `journal_healthy` and
`trades_taken_this_session` as arguments. It
reads no clock and opens no connection. This is why the engine is the only module with real test
coverage — keep it that way. Any new rule belongs inside `analyze()`, not in `cli.py`.

### The evidence rule

A decision is expressed as a `Gate(name, passed, detail)` appended to `result.gates`, never as a
bare early return. `AnalysisResult.accepted` is `all(gates passed) and a plan exists`, so
adding a gate is the only way to add a rejection reason that survives into the ticket and the
Stage 1 check.

---

## 3. Entry points and exit codes

`python sspf.py <command>` (`session_strategy/__main__.py` is an undocumented duplicate — see
finding A15).

| Command | Effect | Exit codes |
|---|---|---|
| `health` | Connects, prints masked account and per-symbol broker metadata | `0` ok, `1` exception |
| `analyze --symbol S [--trading-date D] [--output DIR]` | Full analysis; writes artifacts; records to journal | `0` signal accepted, `3` no trade, `2` unsupported symbol, `1` exception |
| `journal sync` | Reconciles MT5 positions/orders against accepted signals; expires stale ones | `0` healthy, `4` ambiguous match, `1` exception |
| `monitor --analysis-id ID` | Read-only status of a matched position/order, including current R | `0`, `1` exception |
| `stage analysis --analysis A --ticket T` | Stage 1 conformance | `0` pass, `5` fail |
| `stage profitability --trades F` | Stage 2 verification | `0` pass, `5` fail |

Global flags: `--config` (default `config/strategy.yaml`), `--journal` (default
`data/sspf_journal.sqlite3`).

Errors are caught in `main()` and emitted as `{"error": ..., "read_only": true}` on stderr with
exit `1`. Note that this path produces **no artifact** — see finding A6.

---

## 4. Storage

### `outputs/<trading-date>/<analysis-id>/`

Three files per run, written together and never modified afterwards:

- `analysis.json` — the machine-readable `AnalysisResult`: `schema_version`, `strategy_id`,
  `contract_version`, config hash, locked Asian levels, classification inputs, setup and
  direction, entry/stop/TP1/TP2, every gate, and `reason_codes`.
- `ticket.md` — the human-readable proposal, carrying the fixed disclaimer that Stage 1 greps for.
- `chart.png` — session shading plus entry/SL/TP/partial/bid/ask lines.

`analysis_id` is a random 12-hex-character UUID slice. `schema_version`, `config_hash`, and the
full active `config_snapshot` are embedded so a historical artifact remains reconstructable.

### `data/sspf_journal.sqlite3`

| Table | Purpose |
|---|---|
| `analyses` | One row per run: identity, proposed levels, status, config hash, full result JSON, artifact paths |
| `matches` | Links an accepted signal to one MT5 ticket; tracks `ORDER → POSITION → CLOSED` and realised P&L |
| `sync_state` | Singleton row: last sync health and timestamp. A sync older than 5 minutes counts as unhealthy and fails G13/G14 |

Reconciliation is **inference, not instruction**: `match_active` claims an MT5 item only when
exactly one candidate matches on symbol, side, entry, and stop within one tick. Two candidates
produce an ambiguity, which marks the sync unhealthy and fails the risk gates closed.

---

## 5. Design decisions worth preserving

- **The gateway is the safety boundary.** Because only `mt5_gateway.py` imports MetaTrader5 from
  the package, "is this system read-only?" is answerable by reading one small file, and
  `tests/test_safety.py` automates that reading. Do not import MetaTrader5 anywhere else.
- **Status is derived, never set.** `AnalysisResult.status` is a property over `gates` and the
  presence of a tradeable plan. Nothing can stamp a result accepted.
- **Time is injected.** `now` is a parameter, which is what makes the engine tests deterministic
  across the execution-window and staleness gates.
- **Volume is floored, never rounded.** `_volume_floor` guarantees the planned worst-case loss
  cannot exceed the intended risk after broker step rounding.
- **Expiry is local-only.** `expire_unfilled_proposals` marks a row `EXPIRED` in SQLite; it never
  touches the MT5 order, consistent with the read-only boundary.

## 6. Resolved architectural debt

- Chart generation is owned exclusively by `session_strategy.render` and consumes normalized
  UTC candles; the orphan MT5 chart script and its hard-coded offset were removed (finding A8).
- `scripts/run_session_check.ps1` is the canonical scheduler entrypoint, so Task Scheduler only
  needs to invoke a version-controlled command (finding A10).
- `tests/fixtures/` contains versioned golden candle feeds for the four baseline regression
  scenarios and is exercised directly by the test suite (finding A11).
