"""
core/sla_engine.py

SLA deadline stamping + escalation checks + the citizen verification /
audit escalation flow. Kept separate from scoring_engine.py so "how is
priority calculated" and "what happens once a deadline is set" are two
independently testable concerns.
"""

from datetime import datetime, timedelta, timezone


def stamp_deadline(created_at_iso: str, sla_hours: int) -> str:
    created_at = datetime.fromisoformat(created_at_iso)
    deadline = created_at + timedelta(hours=sla_hours)
    return deadline.isoformat()


def is_overdue(sla_deadline_iso: str, as_of: datetime | None = None) -> bool:
    as_of = as_of or datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(sla_deadline_iso)
    return as_of > deadline


def time_remaining_display(sla_deadline_iso: str, as_of: datetime | None = None) -> str:
    as_of = as_of or datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(sla_deadline_iso)
    delta = deadline - as_of
    if delta.total_seconds() <= 0:
        overdue_by = as_of - deadline
        hours = int(overdue_by.total_seconds() // 3600)
        return f"OVERDUE by {hours}h"
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return f"{hours}h {minutes}m remaining"


def bucket_by_sla_state(tickets: list, as_of: datetime | None = None) -> tuple[list, list]:
    """
    Splits a ticket list into (on_track, overdue) as of a given moment.

    This is the pure logic behind the Command Center's SLA fast-forward
    simulator: `as_of` is a *display-time override only* — it never reads
    or writes anything to data_store/db.py, so simulating "6 hours from now"
    for a judge demo can't corrupt real ticket timestamps. The simulator UI
    just calls this (and time_remaining_display) with a virtual `as_of`
    instead of the real clock.
    """
    as_of = as_of or datetime.now(timezone.utc)
    on_track, overdue = [], []
    for t in tickets:
        if t.sla_deadline and is_overdue(t.sla_deadline, as_of=as_of):
            overdue.append(t)
        else:
            on_track.append(t)
    return on_track, overdue


def handle_citizen_verification(approved: bool) -> dict:
    """
    Called when a citizen responds to a "Resolved" ticket.
    Returns the status/note to write back via data_store.db.update_ticket.
    """
    if approved:
        return {"status": "resolved", "citizen_verified": True,
                "note": "Citizen confirmed the fix. Case closed."}
    return {"status": "audit_escalated", "citizen_verified": False,
            "note": ("Citizen rejected the resolution photo. Escalated to "
                      "DARPG-style audit queue for supervisory review.")}
