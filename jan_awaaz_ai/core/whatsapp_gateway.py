"""
core/whatsapp_gateway.py

Two independent capabilities, deliberately kept separate so you can use
either one without the other:

1. `build_click_to_chat_link()` — zero backend, zero API key, works
   instantly. This is the "click a link instead of building an Android
   app" piece. Put this on a poster/QR code and it works today.

2. `send_text_reply()` / `download_media()` — real calls to Meta's
   WhatsApp Cloud API, for the live webhook demo (see webhook_server.py).
   Requires WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in your
   .env, both of which you get free from a Meta developer test number —
   no business verification needed for testing with up to 5 approved
   recipient numbers. Token expires every 24h on the free tier; regenerate
   before demo day.
"""

import os
import urllib.parse

import requests

from config import WHATSAPP_DISPLAY_NUMBER, WHATSAPP_PREFILLED_TEXT

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


# ---------------------------------------------------------------------
# Tier 1: click-to-chat link. No API key, no network call, no backend.
# ---------------------------------------------------------------------
def build_click_to_chat_link(prefilled_text: str | None = None) -> str:
    text = prefilled_text or WHATSAPP_PREFILLED_TEXT
    encoded = urllib.parse.quote(text)
    return f"https://wa.me/{WHATSAPP_DISPLAY_NUMBER}?text={encoded}"


# ---------------------------------------------------------------------
# Tier 2: live Cloud API calls (requires .env credentials)
# ---------------------------------------------------------------------
def _get_credentials() -> tuple[str, str]:
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        raise RuntimeError(
            "WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set in .env. "
            "The click-to-chat link still works without these — only live "
            "send/receive needs them. See README.md 'WhatsApp Channel'."
        )
    return token, phone_number_id


def send_text_reply(to_number: str, message: str) -> dict:
    """Sends a plain text WhatsApp message back to a citizen via Cloud API."""
    token, phone_number_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def download_media(media_id: str) -> tuple[bytes, str]:
    """
    Two-step download per Meta's API: first resolve the media_id to a
    temporary URL, then fetch the bytes from that URL.
    Returns (raw_bytes, mime_type).
    """
    token, _ = _get_credentials()
    headers = {"Authorization": f"Bearer {token}"}

    meta_resp = requests.get(f"{GRAPH_API_BASE}/{media_id}", headers=headers, timeout=15)
    meta_resp.raise_for_status()
    meta = meta_resp.json()

    file_resp = requests.get(meta["url"], headers=headers, timeout=30)
    file_resp.raise_for_status()
    return file_resp.content, meta.get("mime_type", "application/octet-stream")


def parse_incoming_webhook(payload: dict) -> dict | None:
    """
    Extracts the useful bits from Meta's webhook JSON shape.
    Returns None if this payload isn't an inbound user message (e.g. it's
    a delivery-status callback, which Meta also sends to the same webhook).

    Returned shape:
        {
          "from_number": str,
          "message_type": "text" | "image" | "audio",
          "text": str | None,
          "media_id": str | None,
        }
    """
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        messages = change.get("messages")
        if not messages:
            return None  # likely a status callback, not a new message

        msg = messages[0]
        from_number = msg["from"]
        msg_type = msg["type"]

        if msg_type == "text":
            return {"from_number": from_number, "message_type": "text",
                     "text": msg["text"]["body"], "media_id": None}
        if msg_type == "image":
            return {"from_number": from_number, "message_type": "image",
                     "text": msg.get("image", {}).get("caption", ""),
                     "media_id": msg["image"]["id"]}
        if msg_type == "audio":
            return {"from_number": from_number, "message_type": "audio",
                     "text": "", "media_id": msg["audio"]["id"]}
        if msg_type == "location":
            loc = msg["location"]
            return {"from_number": from_number, "message_type": "location",
                     "text": None, "media_id": None,
                     "latitude": loc["latitude"], "longitude": loc["longitude"]}
        return None  # unsupported type (video, sticker, etc.)
    except (KeyError, IndexError, TypeError):
        return None
