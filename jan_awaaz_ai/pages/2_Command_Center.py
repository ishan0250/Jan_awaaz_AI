"""
pages/2_Command_Center.py
Officer-facing dashboard. Reads tickets fresh from data_store/db.py on
every render — this is what guarantees it stays in sync with whatever the
Citizen Portal just wrote, regardless of which browser/tab/user submitted.

Also hosts the SLA Fast-Forward Simulator: a judge demo can't wait 4 real
hours to show a CRITICAL ticket breach its SLA, so this lets you preview
"what the dashboard looks like N hours from now" using a virtual clock.
The virtual clock lives in st.session_state (transient UI state, per the
rule in data_store/db.py) and is passed as `as_of` into sla_engine — it
never touches a persisted ticket's real sla_deadline or created_at.
"""

from datetime import datetime, timedelta, timezone

import streamlit as st
from streamlit_folium import st_folium

from config import DEPARTMENTS
from data_store.db import list_tickets
from core.sla_engine import time_remaining_display, bucket_by_sla_state
from utils.map_visualizer import build_ticket_map

st.title("🖥️ Municipal Command Center")

col_filter, col_refresh = st.columns([3, 1])
with col_filter:
    dept_filter = st.selectbox(
        "Filter by department", ["All"] + [d["display_name"] for d in DEPARTMENTS.values()],
    )
with col_refresh:
    st.write("")
    if st.button("🔄 Refresh"):
        st.rerun()

dept_code = None
if dept_filter != "All":
    for code, dept in DEPARTMENTS.items():
        if dept["display_name"] == dept_filter:
            dept_code = code
            break

tickets = list_tickets(department_code=dept_code)

# --------------------------------------------------------------------
# SLA Fast-Forward Simulator (demo-only virtual clock)
# --------------------------------------------------------------------
st.subheader("⏩ SLA Fast-Forward Simulator")
st.caption(
    "For the demo: preview how this dashboard looks N hours from now, "
    "without waiting in real time and without touching any real ticket "
    "data. Resets to 'now' on page reload."
)

sim_col, reset_col = st.columns([4, 1])
with sim_col:
    ff_hours = st.slider(
        "Simulate hours elapsed since submission", min_value=0, max_value=200,
        value=st.session_state.get("ff_hours", 0), step=1, key="ff_hours",
    )
with reset_col:
    st.write("")
    if st.button("↩️ Reset to now"):
        st.session_state["ff_hours"] = 0
        st.rerun()

virtual_now = datetime.now(timezone.utc) + timedelta(hours=ff_hours)
if ff_hours > 0:
    st.info(
        f"Showing the dashboard as it would look **{ff_hours}h from now** "
        f"(simulated clock: {virtual_now.strftime('%Y-%m-%d %H:%M UTC')})."
    )

on_track, overdue = bucket_by_sla_state(tickets, as_of=virtual_now)

st.subheader(f"{len(tickets)} active ticket(s)")
m1, m2, m3 = st.columns(3)
m1.metric("Total active", len(tickets))
m2.metric("On track", len(on_track))
m3.metric("Overdue at this clock", len(overdue), delta=None,
          delta_color="inverse")

if tickets:
    m = build_ticket_map(tickets)
    st_folium(m, width=1100, height=500)

    # Overdue-first, then by RPI descending — the same "what needs eyes
    # first" ordering an officer would want, adjusted for the virtual clock.
    ordered = sorted(
        tickets,
        key=lambda t: (t not in overdue, -t.rpi_score),
    )

    for t in ordered:
        is_late = t in overdue
        badge = "🔴 OVERDUE" if is_late else "🟢 On track"
        with st.expander(
            f"{badge} · [{t.priority_label}] {t.department_display} — "
            f"RPI {t.rpi_score} — {t.duplicate_count} report(s)"
        ):
            st.write(f"**Summary:** {t.summary_en}")
            st.write(f"**Status:** {t.status}")
            if t.sla_deadline:
                st.write(f"**SLA (at simulated clock):** "
                         f"{time_remaining_display(t.sla_deadline, as_of=virtual_now)}")
            st.write(f"**Escalation policy:** {t.escalation_text}")
            st.write(f"**Evidence confidence:** {t.confidence}")
else:
    st.info("No active tickets match this filter.")
