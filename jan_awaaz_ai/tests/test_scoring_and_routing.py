"""
tests/test_scoring_and_routing.py

Covers the parts of core/ that don't need a live Gemini API call:
scoring, routing keyword matching, geo distance, and SLA math. Run with:

    pytest tests/

Having this pass live in front of judges is a much stronger answer to
"how do you know your logic works" than a verbal claim.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.scoring_engine import compute_rpi, classify_tier, score_ticket
from core.routing_engine import match_department
from core.sla_engine import stamp_deadline, is_overdue
from utils.geo import haversine_meters


def test_rpi_basic_formula():
    # Intensity 3 x Urgency 3 = 9, no duplicates -> no crowd boost
    assert compute_rpi(3, 3, duplicate_count=1) == 9.0


def test_rpi_crowd_boost_capped():
    # Even with an enormous duplicate count, crowd boost never exceeds 5
    score_small = compute_rpi(1, 1, duplicate_count=2)
    score_huge = compute_rpi(1, 1, duplicate_count=100000)
    assert score_huge - 1 <= 5.01  # base(1) + boost(<=5)
    assert score_huge > score_small


def test_rpi_clamps_out_of_range_inputs():
    # Intensity/urgency outside 1-5 should be clamped, not crash
    assert compute_rpi(9, 9, duplicate_count=1) == 25.0
    assert compute_rpi(0, 0, duplicate_count=1) == 1.0


def test_classify_tier_boundaries():
    assert classify_tier(20)[0] == "CRITICAL EMERGENCY"
    assert classify_tier(19.9)[0] == "HIGH PRIORITY"
    assert classify_tier(12)[0] == "HIGH PRIORITY"
    assert classify_tier(6)[0] == "MEDIUM PRIORITY"
    assert classify_tier(5.9)[0] == "ROUTINE CIVIC ISSUE"


def test_confidence_gate_downgrades_critical():
    # Intensity 5 x Urgency 5 = 25 -> would be CRITICAL, but low confidence
    # must cap it below CRITICAL pending human review.
    result_low_conf = score_ticket(5, 5, duplicate_count=1, confidence="low")
    result_high_conf = score_ticket(5, 5, duplicate_count=1, confidence="high")
    assert result_high_conf["priority_label"] == "CRITICAL EMERGENCY"
    assert result_low_conf["priority_label"] != "CRITICAL EMERGENCY"
    assert "Confidence-gated" in result_low_conf["escalation_text"]


def test_routing_live_wire_to_discom():
    result = match_department("There is a live wire sparking near the school")
    assert result["department_code"] == "DISCOM"
    assert result["is_fallback_routed"] is False


def test_routing_pothole_to_pwd():
    result = match_department("Large pothole on the main road near my house")
    assert result["department_code"] == "PWD_CPWD_NHAI"


def test_routing_unclassified_falls_back():
    result = match_department("Illegal construction near the heritage monument")
    assert result["is_fallback_routed"] is True
    assert result["department_code"] == "DM_OFFICE_FALLBACK"


def test_haversine_zero_distance():
    assert haversine_meters(28.6139, 77.2090, 28.6139, 77.2090) == 0.0


def test_haversine_known_distance_roughly_correct():
    # Roughly 500m apart (small lat offset near Delhi's latitude)
    d = haversine_meters(28.6139, 77.2090, 28.6184, 77.2090)
    assert 400 < d < 600


def test_sla_deadline_and_overdue():
    created = "2026-08-23T00:00:00+00:00"
    deadline = stamp_deadline(created, sla_hours=4)
    assert deadline.startswith("2026-08-23T04:00:00")

    from datetime import datetime, timezone
    just_before = datetime(2026, 8, 23, 3, 59, tzinfo=timezone.utc)
    just_after = datetime(2026, 8, 23, 4, 1, tzinfo=timezone.utc)
    assert is_overdue(deadline, as_of=just_before) is False
    assert is_overdue(deadline, as_of=just_after) is True
