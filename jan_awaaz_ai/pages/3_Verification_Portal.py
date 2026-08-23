"""
pages/3_Verification_Portal.py
Citizen approves/rejects an officer's "resolved" photo. Reject -> audit
escalation, per core/sla_engine.handle_citizen_verification.
"""

import streamlit as st

from data_store.db import list_tickets, update_ticket
from core.sla_engine import handle_citizen_verification

st.title("✅ Citizen Verification Portal")
st.caption("Confirm whether your reported issue was actually fixed.")

dispatched = list_tickets(status="dispatched")

if not dispatched:
    st.info("No tickets are currently pending citizen verification. "
             "(Mark a ticket as 'dispatched' with a resolved photo from "
             "the Command Center flow to test this page.)")
else:
    for t in dispatched:
        with st.container(border=True):
            st.write(f"**Ticket `{t.id}`** — {t.summary_en}")
            st.write(f"Department: {t.department_display}")
            if t.resolved_photo_url:
                st.write(f"Resolved photo: {t.resolved_photo_url}")
            else:
                st.write("_(No resolved photo attached in this demo run.)_")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Fixed", key=f"approve_{t.id}"):
                    result = handle_citizen_verification(approved=True)
                    t.status = result["status"]
                    t.citizen_verified = result["citizen_verified"]
                    update_ticket(t)
                    st.success(result["note"])
                    st.rerun()
            with col2:
                if st.button("❌ Reject — Not Actually Fixed", key=f"reject_{t.id}"):
                    result = handle_citizen_verification(approved=False)
                    t.status = result["status"]
                    t.citizen_verified = result["citizen_verified"]
                    update_ticket(t)
                    st.warning(result["note"])
                    st.rerun()
