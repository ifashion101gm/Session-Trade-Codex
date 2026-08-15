from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from session_strategy.journal import Journal
from session_strategy.models import AccountSnapshot, AnalysisResult, Gate


ACCOUNT = AccountSnapshot("****985", "demo", 1000, 1000, "VTMarkets-Demo", True, True, 1)


def result(analysis_id, *, accepted=False, trading_date="2026-08-11", expiry=None, symbol="EURUSD"):
    record = AnalysisResult(analysis_id, datetime(2026, 8, 11, 7, 30, tzinfo=timezone.utc),
                            trading_date, symbol, ACCOUNT, 1.16499, 1.16501, 0.00002,
                            expiry_utc=expiry)
    if accepted:
        record.gates = [Gate("G1_ENVIRONMENT", True, "demo")]
        record.direction, record.entry, record.stop_loss = "LONG", 1.16450, 1.16350
        record.volume, record.initial_risk = 0.05, 0.001
    return record


class JournalTests(unittest.TestCase):
    def test_legacy_schema_is_migrated_without_losing_rows(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.sqlite"
            db = sqlite3.connect(path)
            db.executescript("""
                CREATE TABLE analyses (
                  analysis_id TEXT PRIMARY KEY, created_utc TEXT NOT NULL,
                  session_date TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT, entry REAL,
                  stop_loss REAL, volume REAL, intended_risk REAL, actual_risk REAL,
                  status TEXT NOT NULL, config_hash TEXT NOT NULL, result_json TEXT NOT NULL,
                  json_path TEXT, markdown_path TEXT, chart_path TEXT);
                CREATE TABLE matches (
                  analysis_id TEXT PRIMARY KEY REFERENCES analyses(analysis_id),
                  mt5_ticket INTEGER NOT NULL, position_id INTEGER, state TEXT NOT NULL,
                  realized_pnl REAL DEFAULT 0, matched_utc TEXT NOT NULL, closed_utc TEXT);
                CREATE TABLE sync_state (
                  singleton INTEGER PRIMARY KEY CHECK(singleton=1), healthy INTEGER NOT NULL,
                  synced_utc TEXT NOT NULL, detail TEXT NOT NULL);
                CREATE TABLE verifications (
                  analysis_id TEXT PRIMARY KEY REFERENCES analyses(analysis_id),
                  outcome TEXT NOT NULL, note TEXT NOT NULL, verified_utc TEXT NOT NULL);
            """)
            db.execute("INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       ("legacy", "2026-08-11T00:00:00+00:00", "2026-08-11", "EURUSD",
                        None, None, None, None, None, None, "NO_TRADE", "old", "{}",
                        None, None, None))
            db.commit(); db.close()
            journal = Journal(path)
            self.assertEqual(journal.get("legacy")["status"], "NO_TRADE")
            analysis_columns = {r["name"] for r in journal.db.execute("PRAGMA table_info(analyses)")}
            match_columns = {r["name"] for r in journal.db.execute("PRAGMA table_info(matches)")}
            self.assertIn("artifacts_dir", analysis_columns)
            self.assertIn("realized_r", match_columns)
            journal.close()

    def test_record_and_empty_risk_stats(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            journal.record(result("abc"))
            row = journal.get("abc")
            self.assertEqual(row["symbol"], "EURUSD")
            self.assertEqual(row["status"], "NO_TRADE")
            self.assertEqual(journal.risk_stats(1000, datetime.now(timezone.utc)), (0.0, 0.0))
            journal.mark_sync(True, "ok")
            self.assertTrue(journal.healthy())
            journal.close()

    def test_accepted_signal_is_stored_with_its_direction(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            journal.record(result("acc", accepted=True))
            row = journal.get("acc")
            self.assertEqual(row["status"], "SIGNAL_ACCEPTED")
            self.assertEqual(row["side"], "BUY")
            journal.close()

    def test_expired_unfilled_signal_is_marked_locally(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            journal.record(result("expired", accepted=True,
                                  expiry=datetime(2026, 8, 11, 9, tzinfo=timezone.utc)))
            after = datetime(2026, 8, 11, 9, 1, tzinfo=timezone.utc)
            self.assertEqual(journal.expire_unfilled_proposals(after), ["expired"])
            self.assertEqual(journal.get("expired")["status"], "EXPIRED")
            journal.close()

    def test_session_quota_counts_accepted_and_expired_signals(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            self.assertEqual(journal.trades_this_session("EURUSD", "2026-08-11"), 0)
            journal.record(result("no", accepted=False))
            self.assertEqual(journal.trades_this_session("EURUSD", "2026-08-11"), 0)
            journal.record(result("yes", accepted=True))
            self.assertEqual(journal.trades_this_session("EURUSD", "2026-08-11"), 1)
            self.assertEqual(journal.trades_this_session("GBPUSD", "2026-08-11"), 0)
            self.assertEqual(journal.trades_this_session("EURUSD", "2026-08-12"), 0)
            journal.close()

    def test_open_risk_from_an_earlier_day_does_not_consume_todays_budget(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            record = result("old", accepted=True)
            record.actual_risk_cash = 5.0
            journal.record(record)
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            journal.db.execute(
                "INSERT INTO matches(analysis_id,mt5_ticket,position_id,state,realized_pnl,"
                "realized_r,matched_utc,closed_utc) VALUES (?,?,?,?,?,?,?,NULL)",
                ("old", 111, 111, "POSITION", 0.0, 0.0, yesterday))
            journal.db.commit()
            used, _ = journal.risk_stats(1000, datetime.now(timezone.utc))
            self.assertEqual(used, 0.0)
            journal.close()

    def test_broker_symbol_mapping_matches_suffixed_symbol(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            record = result("gold", accepted=True, symbol="XAUUSD")
            record.entry, record.stop_loss = 2400.0, 2398.0
            journal.record(record)
            from session_strategy.models import SymbolSpec
            spec = SymbolSpec("XAUUSD.crp", 3, .001, .001, .01, 100, .01, 0)
            active = [{"ticket": 7, "identifier": 7, "symbol": "XAUUSD.crp", "type": 0,
                       "price_open": 2400.0, "sl": 2398.0}]
            sync = journal.match_active(active, [], {"XAUUSD": spec},
                                        {"XAUUSD": "XAUUSD.crp"})
            self.assertEqual(sync["matched"], 1)
            self.assertEqual(sync["unmatched_active"], 0)
            journal.close()

    def test_manual_verification_stats_are_config_scoped(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            a, b = result("a"), result("b")
            a.config_hash, b.config_hash = "current", "old"
            journal.record(a); journal.record(b)
            journal.verify("a", "match", "chart reconciled")
            journal.verify("b", "mismatch", "old contract")
            self.assertEqual(journal.verification_stats("current"),
                             {"matches": 1, "mismatches": 0})
            journal.close()

    def test_verification_cannot_be_reclassified_or_deleted(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            journal.record(result("audit"))
            journal.verify("audit", "mismatch", "entry differed")
            with self.assertRaisesRegex(ValueError, "immutable"):
                journal.verify("audit", "match", "try to overwrite")
            with self.assertRaises(sqlite3.IntegrityError):
                journal.db.execute("DELETE FROM verifications WHERE analysis_id='audit'")
            self.assertEqual(journal.verification_stats(""),
                             {"matches": 0, "mismatches": 1})
            journal.close()

    def test_mt5_ticket_can_only_match_one_analysis(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            journal.record(result("one", accepted=True))
            journal.record(result("two", accepted=True))
            columns = "analysis_id,mt5_ticket,position_id,state,realized_pnl,realized_r,matched_utc"
            values = ("one", 42, 42, "POSITION", 0.0, 0.0,
                      datetime.now(timezone.utc).isoformat())
            journal.db.execute(f"INSERT INTO matches({columns}) VALUES (?,?,?,?,?,?,?)", values)
            with self.assertRaises(sqlite3.IntegrityError):
                journal.db.execute(
                    f"INSERT INTO matches({columns}) VALUES (?,?,?,?,?,?,?)",
                    ("two", 42, 42, "POSITION", 0.0, 0.0,
                     datetime.now(timezone.utc).isoformat()))
            journal.close()

    def test_sync_health_distinguishes_healthy_ambiguous_and_stale(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            journal.mark_sync(True, "ok", "HEALTHY")
            self.assertEqual(journal.sync_health(), "HEALTHY")
            journal.mark_sync(False, "two candidates", "AMBIGUOUS")
            self.assertEqual(journal.sync_health(), "AMBIGUOUS")
            stale = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
            journal.db.execute("UPDATE sync_state SET healthy=1, health_status='HEALTHY', synced_utc=?",
                               (stale,))
            journal.db.commit()
            self.assertFalse(journal.healthy())
            self.assertEqual(journal.sync_health(), "STALE")
            journal.close()

    def test_closed_match_records_realized_pnl_and_r(self):
        with TemporaryDirectory() as tmp:
            journal = Journal(Path(tmp) / "j.sqlite")
            trade = result("closed", accepted=True)
            trade.actual_risk_cash = 5.0
            journal.record(trade)
            journal.db.execute(
                "INSERT INTO matches(analysis_id,mt5_ticket,position_id,state,matched_utc) "
                "VALUES (?,?,?,?,?)",
                ("closed", 77, 77, "POSITION", datetime.now(timezone.utc).isoformat()))
            journal.db.commit()
            deals = [{"position_id": 77, "entry": 1, "profit": 10.0, "commission": 0,
                      "swap": 0, "fee": 0, "time": 1786406400}]
            self.assertEqual(journal.update_closed(deals), 1)
            row = journal.db.execute(
                "SELECT realized_pnl, realized_r, state FROM matches WHERE analysis_id='closed'").fetchone()
            self.assertEqual((row["realized_pnl"], row["realized_r"], row["state"]),
                             (10.0, 2.0, "CLOSED"))
            journal.close()


if __name__ == "__main__":
    unittest.main()
