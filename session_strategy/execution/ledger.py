"""Local durable execution ledger.

The whole point of this module is the write that happens BEFORE ``order_send()``
is called. Without it, the dangerous sequence is:

    order_send() succeeds at the broker
              |
    Python process crashes before the result is recorded anywhere
              |
    program restarts
              |
    broker history query is briefly stale/unavailable
              |
    nothing local says "this signal already went out"
              |
    duplicate send

``mark_send_requested()`` persists to disk *before* ``order_send()`` runs, so a
signal_id stuck at ``SEND_REQUESTED`` on restart is a known, visible, ambiguous
state that forces a reconciliation check against the broker -- never a silent
green light to send again.

Lifecycle
---------
    PREPARED -> SEND_REQUESTED -> SEND_ACCEPTED -> POSITION_CONFIRMED
                                -> SEND_REJECTED
                (any state)     -> RECONCILIATION_FAILED

``signal_id`` is the primary key -- one row per signal, ever. A signal already
at ``SEND_REQUESTED`` or later is considered committed; see
``is_committed()``.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMMITTED_STATUSES = ("SEND_REQUESTED", "SEND_ACCEPTED", "POSITION_CONFIRMED", "PENDING_ORDER_CONFIRMED")


class ExecutionLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        # This ledger exists specifically for crash safety around order_send --
        # do not relax durability the way the analysis journal does.
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS executions (
          signal_id TEXT PRIMARY KEY,
          attempt_id TEXT NOT NULL,
          status TEXT NOT NULL,
          symbol TEXT NOT NULL,
          direction TEXT,
          request_json TEXT,
          magic INTEGER,
          order_check_retcode INTEGER,
          order_check_comment TEXT,
          order_send_retcode INTEGER,
          order_send_comment TEXT,
          order_ticket INTEGER,
          deal_ticket INTEGER,
          position_ticket INTEGER,
          filled_volume REAL,
          requested_price REAL,
          fill_price REAL,
          sl REAL,
          tp REAL,
          created_utc TEXT NOT NULL,
          updated_utc TEXT NOT NULL,
          note TEXT
        );
        """)
        self.db.commit()
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Add columns safely to ledgers created before this column existed.

        Bug found live 2026-08-25: has_committed_execution_today() originally
        had no way to distinguish a real ASIAN_SESSION_V1 commit (magic
        123456) from the test harness's own commits (magic 999999) on the
        same symbol/date -- an infrastructure test on EURUSD silently blocked
        the real strategy's EURUSD quota for the rest of the day.
        """
        columns = {row["name"] for row in self.db.execute("PRAGMA table_info(executions)")}
        if "magic" not in columns:
            self.db.execute("ALTER TABLE executions ADD COLUMN magic INTEGER")
            self.db.commit()

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "ExecutionLedger":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def get(self, signal_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM executions WHERE signal_id=?", (signal_id,)
        ).fetchone()
        return dict(row) if row else None

    def prepare(self, signal_id: str, attempt_id: str, symbol: str,
               direction: str | None, request: dict[str, Any] | None) -> None:
        """PREPARED -- written before validation/risk-sizing/order_check, so
        even a crash during those earlier steps leaves a trace."""
        existing = self.get(signal_id)
        now = datetime.now(timezone.utc).isoformat()
        magic = (request or {}).get("magic")
        if existing is not None:
            # Re-preparing an existing, not-yet-committed row (e.g. a retried
            # dry run) refreshes the attempt id and request; a committed row
            # is left untouched here -- is_committed() is what blocks re-send.
            self.db.execute(
                "UPDATE executions SET attempt_id=?, request_json=?, magic=?, updated_utc=? "
                "WHERE signal_id=?",
                (attempt_id, json.dumps(request) if request else None, magic, now, signal_id),
            )
        else:
            self.db.execute(
                "INSERT INTO executions "
                "(signal_id, attempt_id, status, symbol, direction, request_json, magic, "
                " created_utc, updated_utc) VALUES (?,?,?,?,?,?,?,?,?)",
                (signal_id, attempt_id, "PREPARED", symbol, direction,
                 json.dumps(request) if request else None, magic, now, now),
            )
        self.db.commit()

    def mark_send_requested(self, signal_id: str) -> None:
        """Persisted BEFORE order_send() is called -- the critical write."""
        self._update(signal_id, status="SEND_REQUESTED")

    def mark_send_response(self, signal_id: str, retcode: int | None,
                           comment: str | None, order_ticket: int | None,
                           requested_price: float | None = None,
                           sl: float | None = None, tp: float | None = None) -> None:
        # 10009 == MetaTrader5.TRADE_RETCODE_DONE
        status = "SEND_ACCEPTED" if retcode == 10009 else "SEND_REJECTED"
        self._update(
            signal_id, status=status, order_send_retcode=retcode,
            order_send_comment=comment, order_ticket=order_ticket,
            requested_price=requested_price, sl=sl, tp=tp,
        )

    def mark_position_confirmed(self, signal_id: str, deal_ticket: int | None,
                                position_ticket: int | None,
                                filled_volume: float | None,
                                fill_price: float | None) -> None:
        self._update(
            signal_id, status="POSITION_CONFIRMED", deal_ticket=deal_ticket,
            position_ticket=position_ticket, filled_volume=filled_volume,
            fill_price=fill_price,
        )

    def mark_pending_order_confirmed(self, signal_id: str, order_ticket: int | None,
                                     requested_price: float | None, sl: float | None,
                                     tp: float | None) -> None:
        """A PENDING (LIMIT/STOP) order was accepted and independently confirmed
        still resting in the broker's own order book -- distinct from
        POSITION_CONFIRMED, which means a MARKET order filled immediately.
        Both are committed, successful terminal states; which one applies
        depends on intent.entry_type."""
        self._update(
            signal_id, status="PENDING_ORDER_CONFIRMED", order_ticket=order_ticket,
            requested_price=requested_price, sl=sl, tp=tp,
        )

    def mark_reconciliation_failed(self, signal_id: str, note: str) -> None:
        self._update(signal_id, status="RECONCILIATION_FAILED", note=note)

    def mark_order_check(self, signal_id: str, retcode: int | None, comment: str | None) -> None:
        self._update(signal_id, order_check_retcode=retcode, order_check_comment=comment)

    def _update(self, signal_id: str, **fields: Any) -> None:
        fields["updated_utc"] = datetime.now(timezone.utc).isoformat()
        cols = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(
            f"UPDATE executions SET {cols} WHERE signal_id=?",
            (*fields.values(), signal_id),
        )
        self.db.commit()

    def has_committed_execution_today(self, symbol: str, trading_date: str, magic: int) -> bool:
        """True if a signal for this EXACT symbol+magic reached SEND_REQUESTED
        or later on this trading date (YYYY-MM-DD).

        This is what `execute_session_signal.py` uses for its own session-quota
        gate -- NOT `journal.trades_this_session()`, which counts every printed
        ticket (including dry runs and --check calls) as "taken." Conflating
        "a ticket was printed" with "an order was sent" meant a plain dry run
        could silently burn the one-shot quota for a real signal before it was
        ever offered to order_check, found live 2026-08-25.

        `magic` is REQUIRED (found live, same day): without it, an unrelated
        commit under a different magic number on the same symbol -- e.g. the
        TEST_EXECUTION harness (magic 999999) -- silently blocked the real
        ASIAN_SESSION_V1 (magic 123456) quota for the rest of the day, since
        both target the same broker symbol.
        """
        placeholders = ",".join("?" for _ in COMMITTED_STATUSES)
        row = self.db.execute(
            f"SELECT COUNT(*) as n FROM executions WHERE symbol=? AND magic=? "
            f"AND created_utc LIKE ? AND status IN ({placeholders})",
            (symbol, magic, f"{trading_date}%", *COMMITTED_STATUSES),
        ).fetchone()
        return int(row["n"]) > 0

    def is_committed(self, signal_id: str) -> tuple[bool, str]:
        """True once we've persisted that we even ASKED the broker to send --
        SEND_REQUESTED or later. PREPARED alone (never reached order_send) is
        not committed and may be retried or abandoned freely."""
        row = self.get(signal_id)
        if row is None:
            return False, ""
        if row["status"] in COMMITTED_STATUSES:
            return True, f"local ledger status={row['status']} (attempt {row['attempt_id']})"
        return False, ""
