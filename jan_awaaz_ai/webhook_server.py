"""
webhook_server.py

A small, separate FastAPI service that Meta's WhatsApp Cloud API calls
directly when a citizen sends a real WhatsApp message. This runs
alongside (not inside) the Streamlit app — Streamlit isn't built to
receive external webhooks, so this is a second lightweight process.

Run with:
    uvicorn webhook_server:app --host 0.0.0.0 --port 8000

Then expose it publicly for Meta to reach (during the hackathon, ngrok is
the fastest path):
    ngrok http 8000

Paste the ngrok HTTPS URL + your WHATSAPP_VERIFY_TOKEN into the Meta
developer console's webhook configuration. See README.md "WhatsApp
Channel" for the full step-by-step.

Important: Meta sends TEXT, IMAGE, AUDIO, and LOCATION messages to the
SAME /webhook POST endpoint — they arrive as separate messages with
different `type` fields, not separate routes. A citizen reporting an
issue therefore sends two messages in sequence (their report, then their
location), and this handler pairs them using `_pending_by_number` before
calling the shared ticket pipeline.

This file hands off to the SAME core/ticket_pipeline.py the Streamlit
Citizen Portal uses — so a ticket submitted via WhatsApp and a ticket
submitted via the web form go through identical routing/scoring/
clustering logic and land in the identical SQLite database the Command
Center reads from.
"""

import os

from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

from data_store.db import init_db
from core.ai_ingestion import get_client
from core.ticket_pipeline import submit_ticket
from core.whatsapp_gateway import parse_incoming_webhook, download_media, send_text_reply

load_dotenv()
init_db()

app = FastAPI(title="Jan-Awaaz AI — WhatsApp Webhook")

VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "jan_awaaz_verify")

# In-memory pending-report store, keyed by WhatsApp number. Holds a
# citizen's report content while we wait for their location message.
# Fine for a hackathon demo; move to the DB (with a TTL) for production.
_pending_by_number: dict[str, dict] = {}


def store_pending_report(from_number: str, *, text: str = "",
                          image_bytes: bytes | None = None, image_mime: str = "image/jpeg",
                          audio_bytes: bytes | None = None, audio_mime: str = "audio/ogg") -> None:
    """Pure state-mutation, pulled out of the route handler so it's unit-testable."""
    _pending_by_number[from_number] = {
        "text": text, "image_bytes": image_bytes, "image_mime": image_mime,
        "audio_bytes": audio_bytes, "audio_mime": audio_mime,
    }


def pop_pending_report(from_number: str) -> dict | None:
    return _pending_by_number.pop(from_number, None)


def has_pending_report(from_number: str) -> bool:
    return from_number in _pending_by_number


@app.get("/webhook")
def verify_webhook(request: Request):
    """Meta calls this once, at setup time, to confirm you own the endpoint."""
    params = request.query_params
    if (params.get("hub.mode") == "subscribe"
            and params.get("hub.verify_token") == VERIFY_TOKEN):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    """Meta POSTs every inbound message type (text/image/audio/location) here."""
    payload = await request.json()
    parsed = parse_incoming_webhook(payload)

    if parsed is None:
        return {"status": "ignored"}  # status callback or unsupported type

    from_number = parsed["from_number"]

    try:
        # --- Location message: try to complete a pending report ---
        if parsed["message_type"] == "location":
            pending = pop_pending_report(from_number)
            if pending is None:
                send_text_reply(from_number,
                                 "Thanks for the location! Please send your "
                                 "report (text, photo, or voice note) first.")
                return {"status": "no_pending_report"}

            client = get_client()
            ticket, was_merged = submit_ticket(
                client, text=pending["text"] or "", input_channel="whatsapp",
                input_modality=("image" if pending["image_bytes"] else
                                 "audio" if pending["audio_bytes"] else "text"),
                image_bytes=pending["image_bytes"], image_mime_type=pending["image_mime"],
                audio_bytes=pending["audio_bytes"], audio_mime_type=pending["audio_mime"],
                latitude=parsed["latitude"], longitude=parsed["longitude"],
            )
            reply = (
                f"Thanks! This matches an existing report — merged, priority "
                f"now {ticket.priority_label}."
                if was_merged else
                f"Ticket {ticket.id} created, routed to {ticket.department_display}. "
                f"Priority: {ticket.priority_label} (target response: {ticket.sla_hours}h)."
            )
            send_text_reply(from_number, reply)
            return {"status": "processed", "ticket_id": ticket.id}

        # --- Text/image/audio message: stash it, ask for location ---
        image_bytes = audio_bytes = None
        image_mime, audio_mime = "image/jpeg", "audio/ogg"

        if parsed["message_type"] == "image" and parsed["media_id"]:
            image_bytes, image_mime = download_media(parsed["media_id"])
        elif parsed["message_type"] == "audio" and parsed["media_id"]:
            audio_bytes, audio_mime = download_media(parsed["media_id"])

        store_pending_report(from_number, text=parsed["text"] or "",
                              image_bytes=image_bytes, image_mime=image_mime,
                              audio_bytes=audio_bytes, audio_mime=audio_mime)

        send_text_reply(from_number,
                         "Got it! Please share your location now "
                         "(paperclip -> Location) so we can check for "
                         "nearby duplicate reports.")
        return {"status": "awaiting_location"}

    except Exception as exc:  # noqa: BLE001 - webhook must not crash on bad input
        try:
            send_text_reply(from_number,
                             "Sorry, something went wrong processing your report. "
                             "Please try again in a moment.")
        except Exception:
            pass
        return {"status": "error", "detail": str(exc)}
