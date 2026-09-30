"""
pages/3_Verification_Portal.py
Field Officer Verification & 2-Step Citizen Resolution Portal.
"""

import sqlite3
import streamlit as st
from config import DB_PATH
from data_store.db import update_ticket_status

st.set_page_config(page_title="Verification Portal | Jan-Awaaz AI", page_icon="✅", layout="wide")

st.title("✅ Field Officer & Citizen Verification Portal")
st.caption("2-Step Resolution Workflow: Department Submission -> Citizen Cross-Verification.")

def fetch_all_tickets():
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE status != 'closed' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

tickets = fetch_all_tickets()

tab1, tab2 = st.tabs(["👮‍♂️ Step 1: Department Field Action", "👤 Step 2: Citizen Cross-Verification"])

# --- TAB 1: FIELD OFFICER RESOLUTION ---
with tab1:
    open_tickets = [t for t in tickets if t.get("status") in ["open", "reopened", None]]
    
    if not open_tickets:
        st.success("🎉 No active department grievances pending resolution!")
    else:
        ticket_options = {f"{t['id']} - {t.get('department_display', 'Municipal Dept')}": t for t in open_tickets}
        selected_label = st.selectbox("Select Complaint to Mark Resolved *", list(ticket_options.keys()))
        selected_ticket = ticket_options[selected_label]

        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Ticket ID:** `{selected_ticket['id']}`")
            st.markdown(f"**Assigned Authority:** {selected_ticket.get('department_display')}")
            st.markdown(f"**Location:** {selected_ticket.get('evidence_note') or selected_ticket.get('raw_text')}")
        with col2:
            st.markdown(f"**Issue Summary:** {selected_ticket.get('summary_en')}")
            st.markdown(f"**Current Status:** `{selected_ticket.get('status', 'open').upper()}`")

        st.markdown("---")
        st.subheader("📸 Submit Field Repair Evidence")
        proof_image = st.file_uploader("Upload Completion Photo (After Repair) *", type=["jpg", "jpeg", "png"])
        field_notes = st.text_area("Field Action Notes *", placeholder="e.g., Sewer line cleared using jetting machine by Jal Shakti Crew #2.")

        if st.button("Submit for Citizen Verification", type="primary"):
            if not proof_image:
                st.error("Please upload a completion photo as proof of work.")
            elif not field_notes.strip():
                st.error("Please provide field action notes.")
            else:
                update_ticket_status(
                    ticket_id=selected_ticket['id'],
                    new_status="pending_citizen_verification",
                    escalation_text=f"Field Action: {field_notes}"
                )
                st.success(f"Ticket {selected_ticket['id']} updated! Moved to Citizen Verification step.")
                st.rerun()

# --- TAB 2: CITIZEN CROSS-VERIFICATION ---
with tab2:
    pending_citizen = [t for t in tickets if t.get("status") == "pending_citizen_verification"]
    
    if not pending_citizen:
        st.info("No tickets currently awaiting citizen cross-verification.")
    else:
        st.subheader("Review Department Resolution")
        for t in pending_citizen:
            with st.container():
                st.markdown(f"### Ticket `{t['id']}` - {t.get('summary_en')}")
                st.write(f"**Department Action:** {t.get('escalation_text', 'Work reported complete.')}")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirm Work Done (Close Ticket)", key=f"confirm_{t['id']}", type="primary"):
                        update_ticket_status(
                            ticket_id=t['id'],
                            new_status="closed",
                            citizen_verified=True,
                            escalation_text=t.get('escalation_text', '') + " | Verified and Approved by Citizen."
                        )
                        st.success(f"Ticket {t['id']} is officially CLOSED and verified!")
                        st.balloons()
                        st.rerun()
                with c2:
                    if st.button("❌ Issue Not Resolved (Re-Open)", key=f"reopen_{t['id']}"):
                        update_ticket_status(
                            ticket_id=t['id'],
                            new_status="reopened",
                            citizen_verified=False,
                            escalation_text="Re-opened by Citizen: Ground issue persists."
                        )
                        st.warning(f"Ticket {t['id']} re-opened and sent back to department queue.")
                        st.rerun()
            st.divider()