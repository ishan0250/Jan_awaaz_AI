"""
data_store/db.py

THE FIX for the v2.5 bug: "citizen submits, officer's dashboard doesn't
show it." That happened because tickets lived in st.session_state, which
is scoped per browser session and never syncs across tabs/users.

Rule for the whole codebase: NO page or module touches ticket data except
through the functions in this file. Every page reads fresh from SQLite on
every render. st.session_state is only ever used for transient UI state
(form drafts, which tab is open, the fast-forward simulator clock) —
never for ticket data itself.

SQLite is used instead of raw JSON because:
- it's still stdlib (sqlite3), zero new setup, still a single file you can
  delete to reset your demo
- it gives atomic writes, so a citizen submitting and an officer viewing
  at the same moment can't corrupt the file
- embeddings are stored as JSON text in a column, so we don't need a
  vector DB for a 36-hour build
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
    conn.execute("PRAGMA journal_mode=WAL;")  # safer concurrent read/write
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
    embedding = d.pop("embedding_json", None)  # not part of Ticket model
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
    """Used by vector_clustering.py to check nearby existing tickets."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE cluster_master_id IS NULL "
            "AND status != 'resolved' AND latitude IS NOT NULL"
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            embedding = json.loads(d["embedding_json"]) if d["embedding_json"] else None
            out.append((_row_to_ticket(row), embedding))
        return out


def reset_db() -> None:
    """Wipe all tickets — useful between demo runs. Does NOT delete the file."""
    with _connect() as conn:
        conn.execute("DELETE FROM tickets")
