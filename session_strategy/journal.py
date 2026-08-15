from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3

from .models import AnalysisResult, SymbolSpec


class Journal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS analyses (
          analysis_id TEXT PRIMARY KEY, created_utc TEXT NOT NULL, session_date TEXT NOT NULL,
          symbol TEXT NOT NULL, side TEXT, entry REAL, stop_loss REAL, volume REAL,
          intended_risk REAL, actual_risk REAL, status TEXT NOT NULL, config_hash TEXT NOT NULL,
          result_json TEXT NOT NULL, json_path TEXT, markdown_path TEXT, chart_path TEXT,
          asian_high REAL, asian_low REAL, asian_midpoint REAL, session_type TEXT,
          setup_name TEXT, tp1_price REAL, tp2_price REAL, artifacts_dir TEXT
        );
        CREATE TABLE IF NOT EXISTS matches (
          analysis_id TEXT PRIMARY KEY REFERENCES analyses(analysis_id), mt5_ticket INTEGER NOT NULL UNIQUE,
          position_id INTEGER, state TEXT NOT NULL, realized_pnl REAL DEFAULT 0,
          realized_r REAL DEFAULT 0, matched_utc TEXT NOT NULL, closed_utc TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_state (
          singleton INTEGER PRIMARY KEY CHECK(singleton=1), healthy INTEGER NOT NULL,
          synced_utc TEXT NOT NULL, detail TEXT NOT NULL, health_status TEXT NOT NULL DEFAULT 'UNHEALTHY'
        );
        CREATE TABLE IF NOT EXISTS verifications (
          analysis_id TEXT PRIMARY KEY REFERENCES analyses(analysis_id),
          outcome TEXT NOT NULL CHECK(outcome IN ('MATCH','MISMATCH')),
          note TEXT NOT NULL, verified_utc TEXT NOT NULL
        );
        """)
        self._migrate_schema()
        self.db.commit()

    def _migrate_schema(self) -> None:
        """Add audit fields safely to journals created by earlier releases."""
        analysis_columns = {row["name"] for row in self.db.execute("PRAGMA table_info(analyses)")}
        analysis_additions = {
            "asian_high": "REAL", "asian_low": "REAL", "asian_midpoint": "REAL",
            "session_type": "TEXT", "setup_name": "TEXT", "tp1_price": "REAL",
            "tp2_price": "REAL", "artifacts_dir": "TEXT",
        }
        for name, sql_type in analysis_additions.items():
            if name not in analysis_columns:
                self.db.execute(f"ALTER TABLE analyses ADD COLUMN {name} {sql_type}")
        match_columns = {row["name"] for row in self.db.execute("PRAGMA table_info(matches)")}
        if "realized_r" not in match_columns:
            self.db.execute("ALTER TABLE matches ADD COLUMN realized_r REAL DEFAULT 0")
        sync_columns = {row["name"] for row in self.db.execute("PRAGMA table_info(sync_state)")}
        if "health_status" not in sync_columns:
            self.db.execute(
                "ALTER TABLE sync_state ADD COLUMN health_status TEXT NOT NULL DEFAULT 'UNHEALTHY'")
        try:
            self.db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_matches_mt5_ticket ON matches(mt5_ticket)")
        except sqlite3.IntegrityError as exc:
            raise RuntimeError("Journal contains duplicate MT5 tickets; reconciliation is unsafe") from exc
        self.db.executescript("""
        CREATE TRIGGER IF NOT EXISTS verifications_no_update
        BEFORE UPDATE ON verifications
        BEGIN SELECT RAISE(ABORT, 'verification records are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS verifications_no_delete
        BEFORE DELETE ON verifications
        BEGIN SELECT RAISE(ABORT, 'verification records are immutable'); END;
        """)

    def close(self) -> None:
        self.db.close()

    def record(self, result: AnalysisResult, paths: dict[str, str] | None = None) -> None:
        paths = paths or {}
        side = None if result.direction is None else ("BUY" if result.direction == "LONG" else "SELL")
        json_path = paths.get("json")
        artifacts_dir = str(Path(json_path).parent) if json_path else None
        columns = (
            "analysis_id,created_utc,session_date,symbol,side,entry,stop_loss,volume,"
            "intended_risk,actual_risk,status,config_hash,result_json,json_path,markdown_path,"
            "chart_path,asian_high,asian_low,asian_midpoint,session_type,setup_name,tp1_price,"
            "tp2_price,artifacts_dir"
        )
        updates = ",".join(
            f"{name}=excluded.{name}" for name in columns.split(",") if name != "analysis_id")
        self.db.execute(
            f"INSERT INTO analyses({columns}) VALUES ({','.join('?' for _ in range(24))}) "
            f"ON CONFLICT(analysis_id) DO UPDATE SET {updates}", (
                result.analysis_id, result.timestamp_utc.isoformat(), result.trading_date,
                result.symbol, side, result.entry, result.stop_loss, result.volume,
                result.intended_risk_cash, result.actual_risk_cash, result.status,
                result.config_hash, json.dumps(result.to_dict()), json_path,
                paths.get("markdown"), paths.get("chart"), result.asian_high, result.asian_low,
                result.midpoint, result.session_type, None if result.setup == "NONE" else result.setup,
                result.tp1_4r, result.tp2_5r, artifacts_dir))
        self.db.commit()

    def trades_this_session(self, symbol: str, trading_date: str) -> int:
        """Accepted signals already recorded for this symbol on this trading date."""
        row = self.db.execute(
            "SELECT COUNT(*) c FROM analyses WHERE symbol=? AND session_date=? "
            "AND status IN ('SIGNAL_ACCEPTED','EXPIRED')", (symbol, trading_date)).fetchone()
        return int(row["c"])

    def get(self, analysis_id: str) -> dict:
        row = self.db.execute("SELECT * FROM analyses WHERE analysis_id=?", (analysis_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown analysis ID: {analysis_id}")
        return dict(row)

    def mark_sync(self, healthy: bool, detail: str, health_status: str | None = None) -> None:
        status = health_status or ("HEALTHY" if healthy else "UNHEALTHY")
        if status not in {"HEALTHY", "AMBIGUOUS", "STALE", "UNHEALTHY"}:
            raise ValueError(f"Invalid sync health status: {status}")
        self.db.execute(
            "INSERT INTO sync_state(singleton,healthy,synced_utc,detail,health_status) VALUES (1,?,?,?,?) "
            "ON CONFLICT(singleton) DO UPDATE SET healthy=excluded.healthy, "
            "synced_utc=excluded.synced_utc, detail=excluded.detail, "
            "health_status=excluded.health_status",
            (int(healthy), datetime.now(timezone.utc).isoformat(), detail, status))
        self.db.commit()

    def healthy(self) -> bool:
        row = self.db.execute(
            "SELECT healthy, synced_utc, health_status FROM sync_state WHERE singleton=1").fetchone()
        if not row or not row["healthy"]:
            return False
        return datetime.fromisoformat(row["synced_utc"]) >= datetime.now(timezone.utc) - timedelta(minutes=5)

    def sync_health(self) -> str:
        row = self.db.execute(
            "SELECT healthy, synced_utc, health_status FROM sync_state WHERE singleton=1").fetchone()
        if not row:
            return "UNHEALTHY"
        if datetime.fromisoformat(row["synced_utc"]) < datetime.now(timezone.utc) - timedelta(minutes=5):
            return "STALE"
        return str(row["health_status"])

    def expire_unfilled_proposals(self, now: datetime) -> list[str]:
        """Expire local-only proposals past their TTL; MT5 orders are never changed."""
        expired: list[str] = []
        for row in self.db.execute("""SELECT analysis_id, result_json FROM analyses
                                    WHERE status='SIGNAL_ACCEPTED'
                                    AND analysis_id NOT IN (SELECT analysis_id FROM matches)""").fetchall():
            expiry = json.loads(row["result_json"]).get("expiry_utc")
            if expiry and datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= now:
                self.db.execute("UPDATE analyses SET status='EXPIRED' WHERE analysis_id=?", (row["analysis_id"],))
                expired.append(row["analysis_id"])
        self.db.commit()
        return expired

    def match_active(self, positions: list[dict], orders: list[dict], specs: dict[str, SymbolSpec],
                     broker_symbols: dict[str, str] | None = None) -> dict:
        broker_symbols = broker_symbols or {name: name for name in specs}
        candidates = [dict(r) for r in self.db.execute("SELECT * FROM analyses WHERE status='SIGNAL_ACCEPTED'")]
        active = [("position", x) for x in positions] + [("order", x) for x in orders]
        matched, ambiguous = 0, []
        already_matched = {r["analysis_id"] for r in
                           self.db.execute("SELECT analysis_id FROM matches").fetchall()}
        for analysis in candidates:
            if self.db.execute("SELECT 1 FROM matches WHERE analysis_id=?", (analysis["analysis_id"],)).fetchone():
                continue
            spec = specs.get(analysis["symbol"])
            if not spec:
                continue
            hits = []
            for kind, item in active:
                if item.get("symbol") != broker_symbols.get(analysis["symbol"], analysis["symbol"]):
                    continue
                item_type = int(item.get("type", -1))
                expected_buy = analysis["side"] == "BUY"
                side_ok = (kind == "position" and item_type == (0 if expected_buy else 1)) or (kind == "order" and item_type == (2 if expected_buy else 3))
                if not side_ok:
                    continue
                price = item.get("price_open")
                sl = item.get("sl", 0.0)
                if price is not None and abs(price - analysis["entry"]) <= spec.tick_size + 1e-12 and abs(sl - analysis["stop_loss"]) <= spec.tick_size + 1e-12:
                    hits.append((kind, item))
            if len(hits) == 1:
                kind, item = hits[0]
                ticket = int(item["ticket"])
                position_id = int(item.get("identifier", ticket)) if kind == "position" else None
                self.db.execute(
                    "INSERT INTO matches(analysis_id,mt5_ticket,position_id,state,realized_pnl,"
                    "realized_r,matched_utc,closed_utc) VALUES (?,?,?,?,?,?,?,NULL)",
                    (analysis["analysis_id"], ticket, position_id, kind.upper(), 0.0, 0.0,
                     datetime.now(timezone.utc).isoformat()))
                matched += 1
            elif len(hits) > 1:
                ambiguous.append(analysis["analysis_id"])
        # Promote a previously matched pending order to its filled position.
        for row in self.db.execute("SELECT m.*, a.symbol, a.side, a.entry, a.stop_loss FROM matches m JOIN analyses a USING(analysis_id) WHERE m.state='ORDER'").fetchall():
            spec = specs.get(row["symbol"])
            if not spec:
                continue
            expected_type = 0 if row["side"] == "BUY" else 1
            broker_symbol = broker_symbols.get(row["symbol"], row["symbol"])
            hits = [p for p in positions if p.get("symbol") == broker_symbol and int(p.get("type", -1)) == expected_type
                    and abs(float(p.get("price_open", 0)) - row["entry"]) <= spec.tick_size + 1e-12
                    and abs(float(p.get("sl", 0)) - row["stop_loss"]) <= spec.tick_size + 1e-12]
            if len(hits) == 1:
                p = hits[0]
                self.db.execute("UPDATE matches SET mt5_ticket=?, position_id=?, state='POSITION' WHERE analysis_id=?",
                                (int(p["ticket"]), int(p.get("identifier", p["ticket"])), row["analysis_id"]))
            elif len(hits) > 1:
                ambiguous.append(row["analysis_id"])
        self.db.commit()
        # Count MT5 items that have no journal row at all, rather than subtracting this
        # run's match count — otherwise anything matched previously reports as unmatched.
        linked_tickets = {int(r["mt5_ticket"]) for r in
                          self.db.execute("SELECT mt5_ticket FROM matches").fetchall()}
        unmatched = sum(1 for _, item in active if int(item["ticket"]) not in linked_tickets)
        return {"matched": matched, "ambiguous": ambiguous, "unmatched_active": unmatched}

    def update_closed(self, deals: list[dict], active_position_ids: set[int] | None = None) -> int:
        active_position_ids = active_position_ids or set()
        active_tickets = {int(d.get("position_id", 0)): [] for d in deals}
        for deal in deals:
            active_tickets.setdefault(int(deal.get("position_id", 0)), []).append(deal)
        count = 0
        for row in self.db.execute(
                "SELECT m.*, a.actual_risk FROM matches m JOIN analyses a USING(analysis_id) "
                "WHERE m.state='POSITION'").fetchall():
            if int(row["position_id"] or 0) in active_position_ids:
                continue
            ds = active_tickets.get(int(row["position_id"] or 0), [])
            exits = [d for d in ds if int(d.get("entry", -1)) in (1, 3)]
            if exits:
                pnl = sum(float(d.get("profit", 0)) + float(d.get("commission", 0)) + float(d.get("swap", 0)) + float(d.get("fee", 0)) for d in ds)
                realized_r = pnl / float(row["actual_risk"]) if row["actual_risk"] else 0.0
                closed = datetime.fromtimestamp(max(int(d["time"]) for d in exits), timezone.utc).isoformat()
                self.db.execute(
                    "UPDATE matches SET state='CLOSED', realized_pnl=?, realized_r=?, closed_utc=? "
                    "WHERE analysis_id=?", (pnl, realized_r, closed, row["analysis_id"]))
                count += 1
        self.db.commit()
        return count

    def risk_stats(self, balance: float, day: datetime) -> tuple[float, float]:
        start = datetime.combine(day.date(), datetime.min.time(), timezone.utc).isoformat()
        realized_loss = self.db.execute("SELECT COALESCE(SUM(-realized_pnl),0) v FROM matches WHERE state='CLOSED' AND closed_utc>=? AND realized_pnl<0", (start,)).fetchone()["v"]
        # Open risk is scoped to positions opened on this trading day; a position carried
        # from an earlier day must not permanently consume today's budget.
        open_risk = self.db.execute(
            """SELECT COALESCE(SUM(a.actual_risk),0) v FROM matches m JOIN analyses a USING(analysis_id)
               WHERE m.state IN ('POSITION','ORDER') AND m.matched_utc>=?""", (start,)).fetchone()["v"]
        pnls = [float(r[0]) for r in self.db.execute("SELECT realized_pnl FROM matches WHERE state='CLOSED' ORDER BY closed_utc")]
        equity = peak = balance - sum(pnls)
        max_dd = 0.0
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak * 100)
        return float(realized_loss + open_risk), max_dd

    def verify(self, analysis_id: str, outcome: str, note: str) -> None:
        outcome = outcome.upper()
        if outcome not in {"MATCH", "MISMATCH"}:
            raise ValueError("verification outcome must be MATCH or MISMATCH")
        self.get(analysis_id)
        try:
            self.db.execute(
                "INSERT INTO verifications VALUES (?,?,?,?)",
                (analysis_id, outcome, note.strip(), datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError as exc:
            raise ValueError("verification already exists and is immutable") from exc
        self.db.commit()

    def verification_stats(self, config_hash: str) -> dict[str, int]:
        rows = self.db.execute(
            """SELECT v.outcome, COUNT(*) count FROM verifications v
               JOIN analyses a USING(analysis_id) WHERE a.config_hash=? GROUP BY v.outcome""",
            (config_hash,)).fetchall()
        counts = {row["outcome"]: int(row["count"]) for row in rows}
        return {"matches": counts.get("MATCH", 0), "mismatches": counts.get("MISMATCH", 0)}
