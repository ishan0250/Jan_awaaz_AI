"""
utils/map_visualizer.py
Builds the Folium map for the Command Center page. Pure function of a
ticket list in, a folium.Map out — no Streamlit or DB calls here, so the
page just does: tickets = list_tickets(); m = build_ticket_map(tickets).
"""

import folium
from core.models import Ticket

_TIER_COLORS = {
    "CRITICAL EMERGENCY": "red",
    "HIGH PRIORITY": "orange",
    "MEDIUM PRIORITY": "blue",
    "ROUTINE CIVIC ISSUE": "green",
}


def build_ticket_map(tickets: list[Ticket], center=(28.6139, 77.2090)) -> folium.Map:
    m = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

    for t in tickets:
        if t.latitude is None or t.longitude is None:
            continue
        color = _TIER_COLORS.get(t.priority_label, "gray")
        popup_html = (
            f"<b>{t.department_display}</b><br>"
            f"{t.summary_en}<br>"
            f"RPI: {t.rpi_score} ({t.priority_label})<br>"
            f"Duplicates merged: {t.duplicate_count}<br>"
            f"Status: {t.status}"
        )
        folium.CircleMarker(
            location=(t.latitude, t.longitude),
            radius=6 + min(t.duplicate_count, 10),
            color=color,
            fill=True,
            fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(m)

    return m
