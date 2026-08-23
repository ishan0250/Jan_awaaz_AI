"""
core/models.py
Plain dataclasses shared by every layer. Keeping these here (instead of
letting each module invent its own dict shape) is what makes core/ testable
in isolation from Streamlit.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import uuid


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Ticket:
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    # Raw citizen input
    raw_text: str = ""
    input_channel: str = "web"          # web | whatsapp | ivr
    input_modality: str = "text"        # text | audio | image

    # Gemini structured extraction
    summary_en: str = ""
    original_language: str = "en"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Evidence validation
    confidence: str = "medium"          # low | medium | high
    evidence_note: str = ""

    # Routing
    department_code: str = ""
    department_display: str = ""
    is_fallback_routed: bool = False

    # Scoring
    intensity: int = 1                  # 1-5
    urgency: int = 1                    # 1-5
    duplicate_count: int = 1            # includes the original report
    rpi_score: float = 0.0
    priority_label: str = "ROUTINE CIVIC ISSUE"
    sla_hours: int = 168
    escalation_text: str = ""

    # Clustering
    cluster_master_id: Optional[str] = None  # set if merged into another ticket

    # Lifecycle
    status: str = "open"                # open | dispatched | resolved | audit_escalated
    sla_deadline: Optional[str] = None
    resolved_photo_url: Optional[str] = None
    citizen_verified: Optional[bool] = None  # None = pending, True/False = decided

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Ticket":
        return Ticket(**d)
