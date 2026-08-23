"""
data_store/seed_data.py

Pre-seeded tickets so the Command Center map/dashboard has content the
instant you launch the app, before anyone submits a live complaint.
Loaded once on first run (checked via a marker query in load_seed_data).
"""

from datetime import datetime, timezone

from core.models import Ticket
from core.scoring_engine import score_ticket
from core.sla_engine import stamp_deadline
from data_store.db import insert_ticket, list_tickets

_SEED_TICKETS = [
    dict(raw_text="Transformer sparking near Sector 12 market",
         summary_en="A transformer is sparking near the Sector 12 market, posing fire risk.",
         department_code="DISCOM", department_display="State DISCOM / Electricity Board",
         latitude=28.6139, longitude=77.2090, intensity=5, urgency=5, confidence="high"),
    dict(raw_text="Large pothole on MG Road causing traffic",
         summary_en="A large pothole on MG Road is causing traffic slowdowns.",
         department_code="PWD_CPWD_NHAI", department_display="PWD / CPWD / NHAI",
         latitude=28.6169, longitude=77.2140, intensity=3, urgency=2, confidence="high"),
    dict(raw_text="Garbage not collected for 4 days in Green Park",
         summary_en="Garbage has not been collected for four days in the Green Park area.",
         department_code="ULB_SANITATION", department_display="Urban Local Bodies (ULB) / Sanitation",
         latitude=28.5590, longitude=77.2040, intensity=3, urgency=2, confidence="medium"),
    dict(raw_text="Water main burst flooding street near City Hospital",
         summary_en="A water main has burst, flooding the street near City Hospital.",
         department_code="JAL_SHAKTI", department_display="Jal Shakti / Municipal Water Board",
         latitude=28.6304, longitude=77.2177, intensity=5, urgency=4, confidence="high"),
]


def load_seed_data_if_empty() -> int:
    """Inserts seed tickets only if the DB is currently empty. Returns count inserted."""
    if list_tickets():
        return 0

    inserted = 0
    for raw in _SEED_TICKETS:
        scoring = score_ticket(raw["intensity"], raw["urgency"],
                                duplicate_count=1, confidence=raw["confidence"])
        ticket = Ticket(
            raw_text=raw["raw_text"],
            input_channel="web",
            input_modality="text",
            summary_en=raw["summary_en"],
            original_language="English",
            latitude=raw["latitude"],
            longitude=raw["longitude"],
            confidence=raw["confidence"],
            department_code=raw["department_code"],
            department_display=raw["department_display"],
            is_fallback_routed=False,
            intensity=raw["intensity"],
            urgency=raw["urgency"],
            duplicate_count=1,
            rpi_score=scoring["rpi_score"],
            priority_label=scoring["priority_label"],
            sla_hours=scoring["sla_hours"],
            escalation_text=scoring["escalation_text"],
            status="open",
        )
        ticket.sla_deadline = stamp_deadline(ticket.created_at, ticket.sla_hours)
        insert_ticket(ticket)
        inserted += 1
    return inserted
