"""
pages/2_Command_Center.py
Municipal Command Dashboard with Dynamic Status Tracking and Filters.
"""

import sqlite3
import streamlit as st
import folium
from streamlit_folium import st_folium
from config import DB_PATH

st.set_page_config(page_title="Command Center | Jan-Awaaz AI", page_icon="🖥️", layout="wide")

st.markdown("## 🖥️ Municipal Command Center")
st.caption("Administrative monitoring portal with live SLA calculation & urgency scores.")

def fetch_tickets():
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY rpi_score DESC, created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

all_tickets = fetch_tickets()

# Sidebar Filters
st.sidebar.markdown("### 🔍 Filter Complaints")
depts = sorted(list(set([t.get('department_display', 'Unknown') for t in all_tickets if t.get('department_display')])))
selected_depts = st.sidebar.multiselect("Filter by Department", depts, default=depts)

filtered_tickets = [t for t in all_tickets if t.get('department_display') in selected_depts] if selected_depts else all_tickets

# Live Pipeline Metrics
st.markdown("### 📊 Governance Metrics")
open_count = len([t for t in filtered_tickets if t.get('status') in ['open', 'reopened', None]])
pending_verify_count = len([t for t in filtered_tickets if t.get('status') == 'pending_citizen_verification'])
closed_count = len([t for t in filtered_tickets if t.get('status') == 'closed'])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Filtered Grievances", len(filtered_tickets))
m2.metric("Active Dept Queue", open_count)
m3.metric("Pending Citizen Approval", pending_verify_count)
m4.metric("Closed & Verified", closed_count)

st.markdown("---")

# SLA Simulator
st.markdown("### ⏩ SLA Fast-Forward Simulator")
sim_hours = st.slider("Simulate elapsed hours since registration", 0, 72, 0, step=6)

active_tickets = [t for t in filtered_tickets if t.get('status') != 'closed']
processed_tickets = []

for t in active_tickets:
    t_copy = dict(t)
    sla = t_copy.get("sla_hours") or 24
    if sim_hours >= sla and t_copy.get("status") != "pending_citizen_verification":
        t_copy["calculated_status"] = "OVERDUE"
        t_copy["map_color"] = "red"
    else:
        rem = max(0, sla - sim_hours)
        t_copy["calculated_status"] = f"Pending ({rem}h left)" if t_copy.get("status") != "pending_citizen_verification" else "Pending Verification"
        t_copy["map_color"] = "orange" if t_copy.get("status") == "pending_citizen_verification" else "blue"
    processed_tickets.append(t_copy)

# Map View
st.markdown("### 📍 Live Spatial Heatmap")
valid_coords = [t for t in processed_tickets if t.get("latitude") and t.get("longitude")]
if valid_coords:
    avg_lat = sum(float(t["latitude"]) for t in valid_coords) / len(valid_coords)
    avg_lon = sum(float(t["longitude"]) for t in valid_coords) / len(valid_coords)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=11)
    for ticket in valid_coords:
        folium.Marker(
            [float(ticket["latitude"]), float(ticket["longitude"])],
            popup=f"<b>{ticket['id']}</b><br>{ticket.get('department_display')}<br>Status: {ticket['calculated_status']}",
            icon=folium.Icon(color=ticket["map_color"], icon="info-sign")
        ).add_to(m)
    st_folium(m, width=1200, height=350)
else:
    st.info("No active geo-tagged tickets to display on the map.")

st.markdown("---")

# Expandable Queue Cards
st.markdown("### 📋 High-Priority Complaints Queue")
for t in processed_tickets:
    status_str = t["calculated_status"]
    
    if "OVERDUE" in status_str:
        badge = "🔴 OVERDUE"
    elif "Pending Verification" in status_str:
        badge = "🟠 AWAITING VERIFICATION"
    else:
        badge = "🟢 ON TRACK"

    with st.expander(f"{badge} | Ticket `{t['id']}` — RPI Priority Score: {t.get('rpi_score', 0)}", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Assigned Department:** `{t.get('department_display')}`")
            st.markdown(f"**Location:** {t.get('evidence_note') or t.get('raw_text')}")
        with col_b:
            st.markdown(f"**Summary:** {t.get('summary_en')}")
            st.markdown(f"**SLA Status:** `{status_str}`")

        c1, c2, c3 = st.columns(3)
        c1.metric("Threat Urgency", f"{t.get('urgency', 2)} / 5")
        c2.metric("Structural Intensity", f"{t.get('intensity', 2)} / 5")
        c3.metric("Calculated RPI Rating", f"{t.get('rpi_score', 0)}")