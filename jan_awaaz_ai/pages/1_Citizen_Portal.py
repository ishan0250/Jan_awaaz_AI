"""
pages/1_Citizen_Portal.py
Citizen-facing submission form. Thin — all logic delegates to
core/ticket_pipeline.py. Writes go straight through data_store/db.py,
never through session_state, so the Command Center sees new tickets
immediately on its own next render.
"""

import streamlit as st

from core.ai_ingestion import get_client
from core.ticket_pipeline import submit_ticket

st.title("🗣️ Citizen Portal")
st.caption("Report an issue in your own words — text, photo, or voice note.")

with st.form("citizen_complaint_form"):
    channel = st.selectbox(
        "Channel (simulated)", ["web", "whatsapp", "ivr"],
        help="Live WhatsApp/IVR integration is simulated in this build — "
             "see README for why, given the hackathon timeframe.",
    )
    text_input = st.text_area(
        "Describe the issue (any language)",
        placeholder="Hamare ilake me bijli ka naya transformer kharab ho gaya hai...",
    )
    uploaded_image = st.file_uploader("Attach a photo (optional)",
                                       type=["jpg", "jpeg", "png"])
    uploaded_audio = st.file_uploader("Attach a voice note (optional)",
                                       type=["ogg", "mp3", "wav", "m4a"])

    st.markdown("**Location** — required for duplicate-clustering to work. "
                "For live audio submissions with no GPS metadata, always "
                "ask the citizen to confirm location explicitly like this.")
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("Latitude", value=28.6139, format="%.6f")
    with col2:
        longitude = st.number_input("Longitude", value=77.2090, format="%.6f")

    submitted = st.form_submit_button("Submit Complaint")

if submitted:
    if not text_input and not uploaded_image and not uploaded_audio:
        st.error("Please provide text, a photo, or a voice note.")
    else:
        try:
            client = get_client()
            image_bytes = uploaded_image.read() if uploaded_image else None
            audio_bytes = uploaded_audio.read() if uploaded_audio else None

            with st.spinner("Processing with Gemini 2.5 Flash..."):
                ticket, was_merged = submit_ticket(
                    client,
                    text=text_input,
                    input_channel=channel,
                    input_modality=("image" if image_bytes else
                                     "audio" if audio_bytes else "text"),
                    image_bytes=image_bytes,
                    audio_bytes=audio_bytes,
                    latitude=latitude,
                    longitude=longitude,
                )

            if was_merged:
                st.success(
                    f"This matches an existing report — merged into Master "
                    f"Ticket `{ticket.id}`. Duplicate count is now "
                    f"{ticket.duplicate_count}, priority updated to "
                    f"**{ticket.priority_label}** (RPI {ticket.rpi_score})."
                )
            else:
                st.success(f"Ticket `{ticket.id}` created.")

            st.write(f"**Routed to:** {ticket.department_display}"
                      + (" _(fail-safe routing — unclassified issue)_"
                         if ticket.is_fallback_routed else ""))
            st.write(f"**Priority:** {ticket.priority_label} "
                      f"(RPI {ticket.rpi_score}) · SLA: {ticket.sla_hours}h")
            st.write(f"**Summary:** {ticket.summary_en}")
            st.write(f"**Evidence confidence:** {ticket.confidence} "
                      f"— {ticket.evidence_note}")

        except RuntimeError as exc:
            st.error(str(exc))
