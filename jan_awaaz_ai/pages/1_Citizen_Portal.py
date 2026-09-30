"""
pages/1_Citizen_Portal.py
Citizen Grievance Submission Portal.
"""

import streamlit as st
from core.ticket_pipeline import create_and_store_ticket

st.set_page_config(page_title="Citizen Portal | Jan-Awaaz AI", page_icon="📝", layout="wide")

st.markdown("## 📝 Citizen Grievance Portal")
st.caption("Report civic issues in English or any Indian regional language.")

st.markdown("---")

with st.form("grievance_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox("Select State / UT *", ["Uttar Pradesh", "Delhi", "Maharashtra", "Karnataka", "Tamil Nadu"])
        district = st.text_input("District / Municipal Corporation / ULB *", value="Ghaziabad")
    with col2:
        location_note = st.text_input("Detailed Address / Landmark *", placeholder="e.g., Near Raj Nagar Extension Flyover")
    
    user_text = st.text_area(
        "Describe the Issue (Text or Regional Voice Transcription) *", 
        height=100, 
        placeholder="Grievance description in English, Hindi, Hinglish, Marathi, etc."
    )
    
    uploaded_file = st.file_uploader("Upload Evidence Photo (Optional)", type=["jpg", "jpeg", "png"])
    image_bytes = uploaded_file.read() if uploaded_file else None

    submitted = st.form_submit_button("🚀 Submit Grievance", type="primary", use_container_width=True)

if submitted:
    if not state or not district or not location_note or not user_text.strip():
        st.error("Please fill in all required fields marked with *")
    else:
        # Animated Status Spinner
        with st.status("🧠 Processing Multimodal Grievance Input...", expanded=True) as status:
            st.write("🔍 Parsing text and extracting spatial context...")
            st.write("🖼️ Analyzing image evidence (if provided)...")
            st.write("⚡ Computing RPI (Relative Priority Index) and assigning SLA...")
            
            try:
                ticket_id, details = create_and_store_ticket(
                    state=state,
                    district=district,
                    location_note=location_note,
                    user_text=user_text,
                    image_bytes=image_bytes
                )
                status.update(label="✅ Ticket Successfully Registered!", state="complete", expanded=False)
                st.balloons()

                # Clean Receipt Display
                st.markdown("---")
                st.subheader("🎉 Grievance Receipt")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ticket ID", ticket_id)
                c2.metric("Assigned SLA", f"{details.get('sla_hours', 24)} Hours")
                c3.metric("RPI Priority Rating", f"{details.get('rpi_score', 0)} / 75")

                st.info(f"**Assigned Department:** {details.get('department_display')}")
                st.write(f"**Generated English Summary:** {details.get('summary_en')}")

            except Exception as e:
                status.update(label="❌ Error processing grievance", state="error")
                st.error(f"Failed to submit ticket: {str(e)}")