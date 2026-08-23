"""
app.py
Entrypoint only. All business logic lives in core/ and data_store/; all
page content lives in pages/ (Streamlit's native multipage system, which
replaces manual tab-switching and avoids a class of session_state bugs).

Run with: streamlit run app.py
"""

import io

import qrcode
import streamlit as st
from dotenv import load_dotenv

from data_store.db import init_db
from data_store.seed_data import load_seed_data_if_empty
from core.whatsapp_gateway import build_click_to_chat_link

load_dotenv()

st.set_page_config(page_title="Jan-Awaaz AI", page_icon="📢", layout="wide")

# Idempotent: safe to call on every rerun.
init_db()
inserted = load_seed_data_if_empty()

st.title("📢 Jan-Awaaz AI — Smart Civic Grievance & Service Router")
st.caption("SIH 2026 · Student Innovation Track · Governance / Smart Automation")

st.markdown(
    """
Use the sidebar to navigate:

- **Citizen Portal** — submit a complaint by text, photo, or (simulated) voice note.
- **Command Center** — municipal officer view: live map, priorities, SLA clocks.
- **Verification Portal** — citizens confirm or reject a marked-resolved ticket.
- **Compliance Reference Drawer** — the scoring methodology and framework references,
  for the judges' Q&A round.
"""
)

if inserted:
    st.info(f"Loaded {inserted} seed demo tickets into the database.")

st.divider()
st.subheader("📱 Zero-Install Access via WhatsApp")
st.caption("No app to build or install — citizens click a link and their "
           "own WhatsApp opens with a pre-filled message. This is a real "
           "click-to-chat link, works today, no backend required.")

col_link, col_qr = st.columns([2, 1])
with col_link:
    link = build_click_to_chat_link()
    st.code(link, language=None)
    st.markdown(f"[Open in WhatsApp]({link})")
    st.caption(
        "For the LIVE demo (real send/receive, not just the link), run "
        "`uvicorn webhook_server:app --port 8000` alongside this app and "
        "expose it via ngrok — see README.md 'WhatsApp Channel'. Requires "
        "a free Meta developer test number; no business verification needed."
    )
with col_qr:
    qr_img = qrcode.make(link)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Scan to open WhatsApp", width=160)

with st.expander("⚠️ Setup checklist (remove before final demo)"):
    st.markdown(
        """
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`
3. `streamlit run app.py`
4. Delete `data/jan_awaaz.db` any time to reset the demo to seed data.
"""
    )
