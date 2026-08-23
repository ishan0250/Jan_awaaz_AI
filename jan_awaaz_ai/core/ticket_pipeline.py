"""
core/ticket_pipeline.py

The single function Streamlit pages should call to turn citizen input
into a persisted ticket. This is the "Ingestion -> Perception -> Route ->
Cluster -> Score" flow from the handbook, wired together end to end.

Keeping this orchestration in core/ (not in pages/1_Citizen_Portal.py)
means it's unit-testable and the UI file stays thin.
"""

from core.ai_ingestion import extract_from_input
from core.evidence_validator import validate_evidence
from core.routing_engine import match_department
from core.vector_clustering import embed_text, find_duplicate_match
from core.scoring_engine import score_ticket
from core.sla_engine import stamp_deadline
from core.models import Ticket
from data_store.db import insert_ticket, update_ticket, list_open_tickets_with_location


def submit_ticket(client, *, text: str = "", input_channel: str = "web",
                   input_modality: str = "text",
                   audio_bytes: bytes | None = None, audio_mime_type: str = "audio/ogg",
                   image_bytes: bytes | None = None, image_mime_type: str = "image/jpeg",
                   latitude: float | None = None, longitude: float | None = None
                   ) -> tuple[Ticket, bool]:
    """
    Runs the full pipeline and persists the result.

    Returns (ticket, was_merged_into_existing).
    If was_merged_into_existing is True, `ticket` is the EXISTING master
    ticket (now with an updated duplicate_count/score) — not a new row.
    """
    # 1. Perception — Gemini structured extraction
    extraction = extract_from_input(
        client, text=text, audio_bytes=audio_bytes, audio_mime_type=audio_mime_type,
        image_bytes=image_bytes, image_mime_type=image_mime_type,
    )

    # 1b. Evidence validation (confidence gating)
    evidence = validate_evidence(client, extraction["summary_en"],
                                  image_bytes=image_bytes, image_mime_type=image_mime_type)

    # 2. Routing
    routing = match_department(extraction["summary_en"])

    # 3. Clustering — only possible if we have coordinates
    merged_ticket = None
    new_embedding = embed_text(client, extraction["summary_en"])
    if latitude is not None and longitude is not None:
        candidates = list_open_tickets_with_location()
        merged_ticket = find_duplicate_match(latitude, longitude, new_embedding, candidates)

    if merged_ticket:
        # Bump duplicate count + rescore the existing master ticket
        merged_ticket.duplicate_count += 1
        scoring = score_ticket(merged_ticket.intensity, merged_ticket.urgency,
                                merged_ticket.duplicate_count, merged_ticket.confidence)
        merged_ticket.rpi_score = scoring["rpi_score"]
        merged_ticket.priority_label = scoring["priority_label"]
        merged_ticket.sla_hours = scoring["sla_hours"]
        merged_ticket.escalation_text = scoring["escalation_text"]
        merged_ticket.sla_deadline = stamp_deadline(merged_ticket.created_at, merged_ticket.sla_hours)
        update_ticket(merged_ticket)
        return merged_ticket, True

    # 4. Scoring (new ticket)
    intensity = extraction["suggested_intensity"]
    urgency = extraction["suggested_urgency"]
    scoring = score_ticket(intensity, urgency, duplicate_count=1,
                            confidence=evidence["confidence"])

    ticket = Ticket(
        raw_text=text,
        input_channel=input_channel,
        input_modality=input_modality,
        summary_en=extraction["summary_en"],
        original_language=extraction["original_language"],
        latitude=latitude,
        longitude=longitude,
        confidence=evidence["confidence"],
        evidence_note=evidence.get("reason", ""),
        department_code=routing["department_code"],
        department_display=routing["department_display"],
        is_fallback_routed=routing["is_fallback_routed"],
        intensity=intensity,
        urgency=urgency,
        duplicate_count=1,
        rpi_score=scoring["rpi_score"],
        priority_label=scoring["priority_label"],
        sla_hours=scoring["sla_hours"],
        escalation_text=scoring["escalation_text"],
        status="open",
    )
    ticket.sla_deadline = stamp_deadline(ticket.created_at, ticket.sla_hours)
    insert_ticket(ticket, embedding=new_embedding)
    return ticket, False
