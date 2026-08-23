"""
pages/4_Compliance_Reference_Drawer.py
The honest, judge-facing explanation of the scoring methodology. Open
this the moment a judge asks "what's the proof for your scoring scale."
"""

import streamlit as st

st.title("📚 Compliance & Methodology Reference Drawer")

st.markdown(
    """
### How we score priority — and what it's actually based on

We designed our own composite scoring formula for Jan-Awaaz AI. We are
**not** claiming any government body published this exact formula. What we
did is adapt a well-established *pattern* from recognized risk-assessment
methodologies to the civic-grievance context:

- **ISO 31000** and **FEMA's THIRA (CPG 201)** both score risk as
  *Consequence × Likelihood* on a bounded scale — that's the direct source
  of our **Intensity × Urgency** structure.
- **CPGRAMS** (DARPG, Government of India) uses tiered escalation timelines
  based on severity and public-safety impact — that's the pattern our SLA
  tiers are modeled on, not a literal copy of a published table.
- **NDMA's Incident Response System (IRS)** evaluates hazards along two
  axes — structural/physical damage vs. threat to life — which is why we
  kept Intensity and Urgency as two separate 1–5 scores instead of one
  blended number.

### The formula

`RPI = (Intensity × Urgency) + min(log2(duplicate_reports), 5)`

- **Intensity (1–5):** physical/structural damage scale.
- **Urgency (1–5):** threat-to-life / time-criticality scale.
- **Crowd boost:** every additional citizen report of the same issue
  nudges priority up, but logarithmically and capped at +5 — our own
  design choice, so one viral street can't mathematically outrank a lone
  report of, say, a collapsing structure.

### SLA tiers
"""
)

from config import SLA_TIERS  # noqa: E402

for min_rpi, label, sla_hours, sla_display, escalation_text in SLA_TIERS:
    st.markdown(f"**{label}** (RPI ≥ {min_rpi}) — {sla_display}\n\n"
                f"> {escalation_text}")

st.markdown(
    """
### Fake/spam evidence safeguard

Every photo submission is run through a Gemini vision confidence check
(`core/evidence_validator.py`). Low-confidence evidence caps the ticket at
Medium priority, regardless of stated severity, pending human review —
this is a live mechanism in the code, not just a talking point.

### Zero-drop routing guarantee

Any complaint that doesn't match our Tier-1 department keyword taxonomy
is automatically routed to a Tier-2 fail-safe (District Nodal Grievance
Officer / DM Office equivalent) rather than rejected. See
`config.FALLBACK_DEPARTMENT` and `core/routing_engine.py`.
"""
)
