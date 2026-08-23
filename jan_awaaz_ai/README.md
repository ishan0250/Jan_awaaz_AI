# Jan-Awaaz AI — Smart Civic Grievance & Service Router

SIH 2026 · Student Innovation Track (Governance / Smart Automation)

## Quickstart

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env and add your GEMINI_API_KEY
streamlit run app.py
```

The database (`data/jan_awaaz.db`) is created automatically on first run
and seeded with 4 demo tickets so the Command Center map has content
immediately. Delete that file any time to reset to a clean demo state.

## Why this structure

- **`core/`** — all business logic (ingestion, routing, scoring, clustering,
  SLA). Zero Streamlit imports, so it's independently unit-testable. Run
  `pytest tests/` to see it proven, not just claimed.
- **`data_store/db.py`** — the ONLY place ticket data is read or written.
  Every page reads fresh from SQLite on every render. This is a deliberate
  fix for the classic Streamlit hackathon bug: `st.session_state` is scoped
  per browser session and will NOT sync a citizen's submission to an
  officer's dashboard in a different tab/device. `st.session_state` in this
  codebase is only ever used for transient UI state — never ticket data.
- **`pages/`** — Streamlit's native multipage system. Each page is thin: it
  calls into `core/` and `data_store/`, nothing more.

## Scoring methodology — read this before judge Q&A

See `pages/4_Compliance_Reference_Drawer.py` (also renders as an in-app
page). Short version: our RPI formula (`Intensity × Urgency + capped
log2(duplicates)`) is our own design. Its *structure* follows the
Consequence × Likelihood pattern used in ISO 31000 / FEMA THIRA, and our
SLA tiers are modeled on CPGRAMS-style escalation timelines — we do not
claim any government body published this exact formula or exact numbers.
Say this plainly in the pitch; it's a stronger answer than a fabricated
citation a judge can disprove on the spot.

## WhatsApp Channel

Two independent tiers — use one or both:

### Tier 1: Click-to-chat link (zero setup, works right now)
`core/whatsapp_gateway.build_click_to_chat_link()` generates a plain
`https://wa.me/<number>?text=...` link, shown with a QR code on the main
app page. Clicking it opens the citizen's own WhatsApp with a pre-filled
message — no app, no login, no backend. This alone is a legitimate,
defensible "Zero-Barrier Access" story for the pitch.

### Tier 2: Live webhook (real send/receive, for a full end-to-end demo)
1. Create an app at [developers.facebook.com](https://developers.facebook.com) → add the
   **WhatsApp** product. Meta assigns you a free temporary test number —
   no business verification needed for this.
2. Under WhatsApp → API Setup, add up to 5 real phone numbers (your team's,
   a judge's) as approved test recipients.
3. Copy the temporary access token and phone number ID into `.env`
   (`WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`). **The token
   expires every 24 hours on the free tier — regenerate it the morning of
   your demo.**
4. Run the webhook server alongside Streamlit:
   ```bash
   uvicorn webhook_server:app --host 0.0.0.0 --port 8000
   ```
5. Expose it publicly (Meta requires a public HTTPS URL):
   ```bash
   ngrok http 8000
   ```
6. In the Meta developer console → WhatsApp → Configuration, set the
   webhook URL to `https://<your-ngrok-url>/webhook` and the verify token
   to match `WHATSAPP_VERIFY_TOKEN` in your `.env`. Subscribe to the
   `messages` field.
7. Message your test number from an approved recipient phone. The bot
   asks for your location after your report, then creates a ticket
   through the exact same `core/ticket_pipeline.py` the web form uses —
   it'll show up on the Command Center map immediately.

This is a real integration, not a simulation — but it's honestly scoped
to Meta's free test tier (5 recipient numbers, 24h token). Say that
plainly if asked; it's a stronger answer than pretending it's production-ready.

## Known scope decisions (say these out loud if asked, don't dodge)

- **IVR (phone call) channel is out of scope** for this build — it needs
  telephony infrastructure (Twilio/Exotel) beyond a 36-hour build. WhatsApp
  and web cover the "Zero-Barrier Access" story; own that scoping choice.
- **Voice-note submissions have no GPS metadata.** The Citizen Portal always
  asks for explicit latitude/longitude so the 500m duplicate-clustering
  demo works for the audio path too, not just text/photo.
- **Routing is keyword-based** (`core/routing_engine.py`), not a full
  classifier. This is a deliberate speed/explainability tradeoff for a
  hackathon build — the function signature is isolated so it can be
  swapped for a Gemini structured-output classifier later without touching
  any caller.

## Testing

```bash
pytest tests/
```

Covers scoring math, tier boundaries, the confidence-gating safeguard,
department routing (including the Tier-2 fallback), haversine distance,
and SLA deadline/overdue logic — everything that doesn't require a live
Gemini API call.

## File structure

```
jan_awaaz_ai/
├── app.py                        # Streamlit entrypoint (nav shell only)
├── config.py                     # Departments, SLA tiers, thresholds
├── core/                         # Pure Python business logic
│   ├── models.py                 # Ticket dataclass
│   ├── ai_ingestion.py           # Gemini multimodal extraction
│   ├── evidence_validator.py     # Vision confidence gating
│   ├── routing_engine.py         # Tier 1/2 department resolver
│   ├── vector_clustering.py      # Embedding + 500m duplicate merge
│   ├── scoring_engine.py         # RPI formula
│   ├── sla_engine.py             # SLA clock + escalation
│   └── ticket_pipeline.py        # Orchestrates the full flow
├── data_store/
│   ├── db.py                     # SQLite — single source of truth
│   └── seed_data.py              # Demo tickets for instant showcase
├── pages/                        # Streamlit multipage UI
├── utils/
│   ├── geo.py                    # Haversine distance
│   └── map_visualizer.py         # Folium map builder
├── webhook_server.py             # FastAPI service for live WhatsApp webhook
└── tests/
    ├── test_scoring_and_routing.py
    └── test_whatsapp_gateway.py
```
