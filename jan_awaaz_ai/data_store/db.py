"""
data_store/db.py
Single source of truth for database interactions across the app.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from config import DB_PATH
from core.models import Ticket

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    raw_text TEXT,
    input_channel TEXT,
    input_modality TEXT,
    summary_en TEXT,
    original_language TEXT,
    latitude REAL,
    longitude REAL,
    confidence TEXT,
    evidence_note TEXT,
    department_code TEXT,
    department_display TEXT,
    is_fallback_routed INTEGER,
    intensity INTEGER,
    urgency INTEGER,
    duplicate_count INTEGER,
    rpi_score REAL,
    priority_label TEXT,
    sla_hours INTEGER,
    escalation_text TEXT,
    cluster_master_id TEXT,
    status TEXT,
    sla_deadline TEXT,
    resolved_photo_url TEXT,
    citizen_verified INTEGER,
    embedding_json TEXT
);
"""


@contextmanager
def _connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def _row_to_ticket(row: sqlite3.Row) -> Ticket:
    d = dict(row)
    embedding = d.pop("embedding_json", None)
    d["is_fallback_routed"] = bool(d["is_fallback_routed"])
    d["citizen_verified"] = (None if d["citizen_verified"] is None
                              else bool(d["citizen_verified"]))
    return Ticket.from_dict(d)


def insert_ticket(ticket: Ticket, embedding: Optional[list[float]] = None) -> None:
    d = ticket.to_dict()
    d["is_fallback_routed"] = int(d["is_fallback_routed"])
    d["citizen_verified"] = (None if d["citizen_verified"] is None
                              else int(d["citizen_verified"]))
    d["embedding_json"] = json.dumps(embedding) if embedding is not None else None

    cols = ", ".join(d.keys())
    placeholders = ", ".join("?" for _ in d)
    with _connect() as conn:
        conn.execute(f"INSERT INTO tickets ({cols}) VALUES ({placeholders})",
                     list(d.values()))


def update_ticket(ticket: Ticket) -> None:
    d = ticket.to_dict()
    d["is_fallback_routed"] = int(d["is_fallback_routed"])
    d["citizen_verified"] = (None if d["citizen_verified"] is None
                              else int(d["citizen_verified"]))
    ticket_id = d.pop("id")
    set_clause = ", ".join(f"{k} = ?" for k in d.keys())
    with _connect() as conn:
        conn.execute(f"UPDATE tickets SET {set_clause} WHERE id = ?",
                     list(d.values()) + [ticket_id])


def update_ticket_status(ticket_id: str, new_status: str, escalation_text: Optional[str] = None, citizen_verified: Optional[bool] = None) -> None:
    """Explicit database helper to update ticket verification status."""
    updates = ["status = ?"]
    params = [new_status]

    if escalation_text is not None:
        updates.append("escalation_text = ?")
        params.append(escalation_text)

    if citizen_verified is not None:
        updates.append("citizen_verified = ?")
        params.append(int(citizen_verified))

    params.append(ticket_id)
    query = f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?"

    with _connect() as conn:
        conn.execute(query, params)


def get_ticket(ticket_id: str) -> Optional[Ticket]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _row_to_ticket(row) if row else None


def list_tickets(status: Optional[str] = None,
                 department_code: Optional[str] = None) -> list[Ticket]:
    """Always reads fresh from disk — this is what every page should call."""
    query = "SELECT * FROM tickets WHERE cluster_master_id IS NULL"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if department_code:
        query += " AND department_code = ?"
        params.append(department_code)
    query += " ORDER BY rpi_score DESC, created_at DESC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_ticket(r) for r in rows]


def list_open_tickets_with_location() -> list[tuple[Ticket, Optional[list[float]]]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE cluster_master_id IS NULL "
            "AND status != 'closed' AND latitude IS NOT NULL"
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            embedding = json.loads(d["embedding_json"]) if d["embedding_json"] else None
            out.append((_row_to_ticket(row), embedding))
        return out


def reset_db() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM tickets")