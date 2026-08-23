"""
tests/test_sla_simulator.py

Covers core/sla_engine.bucket_by_sla_state — the pure logic behind the
Command Center's SLA Fast-Forward Simulator. Uses plain Ticket objects
directly, no Streamlit and no DB, so this runs in the same fast
in-memory suite as scoring/routing.
"""

from datetime import datetime, timedelta, timezone

from core.models import Ticket
from core.sla_engine import stamp_deadline, bucket_by_sla_state, is_overdue


def _make_ticket(sla_hours: int, created_at: datetime | None = None) -> Ticket:
    created_at = created_at or datetime.now(timezone.utc)
    t = Ticket(created_at=created_at.isoformat())
    t.sla_hours = sla_hours
    t.sla_deadline = stamp_deadline(t.created_at, sla_hours)
    return t


def test_bucket_all_on_track_at_creation_time():
    tickets = [_make_ticket(4), _make_ticket(24), _make_ticket(168)]
    on_track, overdue = bucket_by_sla_state(tickets, as_of=datetime.now(timezone.utc))
    assert len(on_track) == 3
    assert len(overdue) == 0


def test_bucket_splits_correctly_after_fast_forward():
    # A 4h-SLA ticket and a 168h-SLA ticket, both created "now".
    critical = _make_ticket(4)
    routine = _make_ticket(168)

    # Fast-forward 10 hours: the 4h ticket should now be overdue,
    # the 168h (7-day) ticket should still be on track.
    virtual_now = datetime.now(timezone.utc) + timedelta(hours=10)
    on_track, overdue = bucket_by_sla_state([critical, routine], as_of=virtual_now)

    assert critical in overdue
    assert routine in on_track
    assert len(on_track) == 1
    assert len(overdue) == 1


def test_bucket_never_mutates_ticket_state():
    # The simulator must be read-only: as_of is a display override,
    # never a write to the ticket's real deadline/status.
    t = _make_ticket(4)
    original_deadline = t.sla_deadline
    original_status = t.status

    far_future = datetime.now(timezone.utc) + timedelta(hours=500)
    bucket_by_sla_state([t], as_of=far_future)

    assert t.sla_deadline == original_deadline
    assert t.status == original_status


def test_is_overdue_matches_bucket_result():
    t = _make_ticket(4)
    virtual_now = datetime.now(timezone.utc) + timedelta(hours=10)
    on_track, overdue = bucket_by_sla_state([t], as_of=virtual_now)
    assert is_overdue(t.sla_deadline, as_of=virtual_now) == (t in overdue)
