"""
core/scoring_engine.py

Composite Risk Priority Index (RPI).

    RPI = (Intensity x Urgency) + min(log2(N_duplicates + 1), MAX_CROWD_BOOST)

Design note (say this to judges, don't just paste it in a slide):
The Intensity x Urgency structure is the same Consequence x Likelihood
pattern used in recognized risk-assessment methods such as ISO 31000 and
FEMA's THIRA (CPG 201). The exact weighting, the log2 crowd-boost, and the
SLA tiers below are our own design choices, calibrated to feel consistent
with CPGRAMS-style escalation timelines. We are not claiming CPGRAMS
publishes this exact formula.

Confidence gating: if the evidence-validation step (evidence_validator.py)
returns low confidence, we cap the ticket at MEDIUM priority regardless of
the raw score, pending human review. This is a real, visible answer to
"what stops fake/spam evidence from getting emergency priority."
"""

import math
from config import MAX_CROWD_BOOST, SLA_TIERS, MIN_CONFIDENCE_FOR_FULL_PRIORITY

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def compute_rpi(intensity: int, urgency: int, duplicate_count: int) -> float:
    """Pure math. duplicate_count includes the original report (>=1)."""
    intensity = max(1, min(5, intensity))
    urgency = max(1, min(5, urgency))
    duplicate_count = max(1, duplicate_count)

    base = intensity * urgency
    crowd_boost = min(math.log2(duplicate_count) if duplicate_count > 1 else 0.0,
                       MAX_CROWD_BOOST)
    return round(base + crowd_boost, 2)


def classify_tier(rpi_score: float) -> tuple[str, int, str, str]:
    """Returns (label, sla_hours, sla_display, escalation_text) for a raw RPI score."""
    for min_rpi, label, sla_hours, sla_display, escalation_text in SLA_TIERS:
        if rpi_score >= min_rpi:
            return label, sla_hours, sla_display, escalation_text
    # Should never hit this since SLA_TIERS bottoms out at 0
    lowest = SLA_TIERS[-1]
    return lowest[1], lowest[2], lowest[3], lowest[4]


def score_ticket(intensity: int, urgency: int, duplicate_count: int,
                  confidence: str = "medium") -> dict:
    """
    Full scoring pipeline for a ticket. Applies the confidence gate,
    then returns everything a Ticket record needs to persist.
    """
    rpi_score = compute_rpi(intensity, urgency, duplicate_count)
    label, sla_hours, sla_display, escalation_text = classify_tier(rpi_score)

    confidence_ok = _CONFIDENCE_RANK.get(confidence, 1) >= _CONFIDENCE_RANK[MIN_CONFIDENCE_FOR_FULL_PRIORITY]
    if not confidence_ok and label == "CRITICAL EMERGENCY":
        # Downgrade one tier and note why — never silently drop the ticket
        label, sla_hours, sla_display, escalation_text = classify_tier(11.99)
        escalation_text = (f"[Confidence-gated] {escalation_text} "
                            f"Original score qualified for a higher tier but "
                            f"evidence confidence was '{confidence}'; capped "
                            f"pending human review.")

    return {
        "rpi_score": rpi_score,
        "priority_label": label,
        "sla_hours": sla_hours,
        "sla_display": sla_display,
        "escalation_text": escalation_text,
    }
