"""SQLite persistence for scan records.

Plain ``sqlite3`` (no SQLAlchemy) — small schema, sync calls dispatched
to a threadpool from async routes via ``asyncio.to_thread``. Swap for
Postgres later by replacing the connection factory.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id      TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    media_type   TEXT NOT NULL DEFAULT 'image',
    status       TEXT NOT NULL DEFAULT 'queued',
    score        REAL,
    risk_label   TEXT,
    result_json  TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at DESC);
"""


class ScanStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, scan_id: str, filename: str, media_type: str = "image") -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO scans (scan_id, filename, media_type, status, created_at, updated_at) "
                "VALUES (?, ?, ?, 'queued', ?, ?)",
                (scan_id, filename, media_type, now, now),
            )
            conn.commit()

    def update_status(self, scan_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE scans SET status = ?, updated_at = ? WHERE scan_id = ?",
                (status, self._now(), scan_id),
            )
            conn.commit()

    def finalize(
        self,
        scan_id: str,
        status: str,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        score: Optional[float] = None,
        risk_label: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE scans SET
                    status      = ?,
                    score       = COALESCE(?, score),
                    risk_label  = COALESCE(?, risk_label),
                    result_json = COALESCE(?, result_json),
                    error       = COALESCE(?, error),
                    updated_at  = ?
                WHERE scan_id = ?
                """,
                (
                    status,
                    score,
                    risk_label,
                    json.dumps(result) if result is not None else None,
                    error,
                    self._now(),
                    scan_id,
                ),
            )
            conn.commit()

    def get(self, scan_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM scans ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete(self, scan_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM scans WHERE scan_id = ?", (scan_id,))
            conn.commit()
        return cur.rowcount > 0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        if d.get("result_json"):
            try:
                d["result"] = json.loads(d["result_json"])
            except json.JSONDecodeError:
                d["result"] = None
        else:
            d["result"] = None
        d.pop("result_json", None)
        return d


def classify_risk(score: float) -> str:
    """Same thresholds the Streamlit prototype used."""
    if score >= 0.80:
        return "HIGH_RISK"
    if score >= 0.50:
        return "AI_GENERATED"
    if score >= 0.30:
        return "INCONCLUSIVE"
    return "AUTHENTIC"
