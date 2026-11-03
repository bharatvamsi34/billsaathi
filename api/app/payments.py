"""Sandbox payments (mock): no real money ever moves.

A payment needs a SAFE, unforced verdict, the user's explicit confirmation and an idempotency
key. Every attempt, allowed or refused, is one row in an append-only audit log; triggers make
the database itself refuse any update or delete, and each row carries a hash of the one before.

In production the database file is on an Azure Files share (infra/deploy.ps1 step 13), so a restart
or a new revision keeps the audit history. SQLite on a network share needs one writer at a time:
the app stays at max 1 replica.
"""

import hashlib
import json
import sqlite3
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agent.loop import AgentSession
from app.bbps_mock import service
from app.pii import mask_id
from app.schemas import Verdict

SANDBOX_NOTE = "Sandbox: no real money moved. BBPS is a mock."

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    check_id TEXT NOT NULL,
    idempotency_key TEXT,
    detail TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TABLE IF NOT EXISTS receipts (
    idempotency_key TEXT PRIMARY KEY,
    check_id TEXT NOT NULL UNIQUE,
    receipt TEXT NOT NULL
);
"""


class PaymentRefused(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class PaymentStore:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # A network share can be slow to hand over its lock after a restart.
        self._db = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self._db.executescript(_SCHEMA)
        self._lock = threading.Lock()

    def _audit(
        self, action: str, outcome: str, check_id: str, key: str | None, detail: dict[str, Any]
    ) -> int:
        row = self._db.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev = row[0] if row else "genesis"
        at = datetime.now(UTC).isoformat(timespec="milliseconds")
        text = json.dumps(detail, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(
            "|".join([prev, at, action, outcome, check_id, key or "", text]).encode()
        ).hexdigest()
        cursor = self._db.execute(
            "INSERT INTO audit_log (at, action, outcome, check_id, idempotency_key, detail,"
            " prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (at, action, outcome, check_id, key, text, prev, digest),
        )
        return cursor.lastrowid

    def refuse(self, check_id: str, key: str | None, code: str) -> None:
        with self._lock, self._db:
            self._audit("pay", "refused", check_id, key, {"code": code})

    def pay(
        self, check_id: str, key: str, build: Callable[[], dict[str, Any]]
    ) -> tuple[dict[str, Any], bool]:
        """The receipt for this key or check, or a new one. Returns (receipt, replayed)."""
        with self._lock:
            existing = self._db.execute(
                "SELECT check_id, receipt FROM receipts WHERE idempotency_key = ? OR check_id = ?",
                (key, check_id),
            ).fetchone()
            if existing is not None and existing[0] != check_id:
                with self._db:
                    self._audit("pay", "refused", check_id, key, {"code": "key_reused"})
                raise PaymentRefused(
                    409, "key_reused", "This idempotency key belongs to another payment."
                )
            with self._db:  # the receipt and its audit row are saved together, or not at all
                if existing is not None:
                    receipt = json.loads(existing[1])
                    self._audit(
                        "pay", "replayed", check_id, key, {"receipt": receipt["receipt_id"]}
                    )
                    return receipt, True
                receipt = build()
                receipt["audit_id"] = self._audit(
                    "pay",
                    "sandbox_paid",
                    check_id,
                    key,
                    {
                        "receipt": receipt["receipt_id"],
                        "biller_id": receipt["biller_id"],
                        "consumer": receipt["consumer_masked"],
                        "amount": receipt["amount"],
                    },
                )
                self._db.execute(
                    "INSERT INTO receipts (idempotency_key, check_id, receipt) VALUES (?, ?, ?)",
                    (key, check_id, json.dumps(receipt, ensure_ascii=False)),
                )
                return receipt, False

    def audit_rows(self) -> list[dict[str, Any]]:
        columns = ("id", "at", "action", "outcome", "check_id", "idempotency_key", "detail", "prev_hash", "hash")  # fmt: skip
        rows = self._db.execute(f"SELECT {', '.join(columns)} FROM audit_log ORDER BY id")
        return [dict(zip(columns, row, strict=True)) for row in rows]


def _verified_consumer(session: AgentSession) -> str | None:
    """The consumer number the biller confirmed (it may have come from the user's answer)."""
    for result in reversed(session.record.tool_results):
        if result.tool == "fetch_bill" and result.ok:
            return result.args.get("consumer_number")
    return None


def payable(session: AgentSession | None) -> dict[str, Any]:
    """What may be paid for this check, taken from the checks. Refuses unless SAFE."""
    final = session.final if session else None
    if final is None or final.verdict != Verdict.SAFE or final.forced:
        raise PaymentRefused(409, "not_safe", "Only a check with a SAFE verdict can be paid.")
    biller_id = next(
        r.data.get("biller_id") for r in session.record.tool_results if r.tool == "lookup_biller"
    )
    return {
        "biller_id": biller_id,
        "biller_name": service.get_biller(biller_id).name,
        "consumer_masked": mask_id(_verified_consumer(session)),
        "amount": session.input.extraction.amount.value,
    }


def new_receipt(payment: dict[str, Any], check_id: str) -> dict[str, Any]:
    return {
        "receipt_id": f"SBX-{uuid.uuid4().hex[:10].upper()}",
        "check_id": check_id,
        **payment,
        "currency": "INR",
        "paid_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "SANDBOX_SUCCESS",
        "sandbox": True,
        "note": SANDBOX_NOTE,
    }
