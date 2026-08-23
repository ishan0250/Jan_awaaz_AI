"""
tests/test_whatsapp_gateway.py

Tests the parts of the WhatsApp integration that don't need a live Meta
API call: payload parsing, click-to-chat link construction, and the
pending-report pairing logic used by webhook_server.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.whatsapp_gateway import build_click_to_chat_link, parse_incoming_webhook


def _wrap(message: dict) -> dict:
    """Wraps a single message in Meta's real webhook envelope shape."""
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def test_click_to_chat_link_contains_number_and_encoded_text():
    link = build_click_to_chat_link("Hello world")
    assert link.startswith("https://wa.me/")
    assert "Hello" in link or "Hello%20world" in link or "Hello+world" in link


def test_parse_text_message():
    payload = _wrap({"from": "919999999999", "type": "text",
                      "text": {"body": "Pothole on main road"}})
    parsed = parse_incoming_webhook(payload)
    assert parsed["from_number"] == "919999999999"
    assert parsed["message_type"] == "text"
    assert parsed["text"] == "Pothole on main road"


def test_parse_image_message():
    payload = _wrap({"from": "919999999999", "type": "image",
                      "image": {"id": "media123", "caption": "broken pipe"}})
    parsed = parse_incoming_webhook(payload)
    assert parsed["message_type"] == "image"
    assert parsed["media_id"] == "media123"
    assert parsed["text"] == "broken pipe"


def test_parse_location_message():
    payload = _wrap({"from": "919999999999", "type": "location",
                      "location": {"latitude": 28.61, "longitude": 77.20}})
    parsed = parse_incoming_webhook(payload)
    assert parsed["message_type"] == "location"
    assert parsed["latitude"] == 28.61
    assert parsed["longitude"] == 77.20


def test_parse_status_callback_returns_none():
    # Meta sends delivery/read receipts to the same webhook — no "messages" key
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    assert parse_incoming_webhook(payload) is None


def test_parse_malformed_payload_returns_none_not_crash():
    assert parse_incoming_webhook({}) is None
    assert parse_incoming_webhook({"entry": []}) is None


def test_pending_report_pairing_flow():
    # Import inside the test to avoid loading FastAPI app at collection
    # time if fastapi isn't installed in a given environment.
    from webhook_server import store_pending_report, pop_pending_report, has_pending_report

    number = "919999999999"
    assert has_pending_report(number) is False

    store_pending_report(number, text="Streetlight broken")
    assert has_pending_report(number) is True

    pending = pop_pending_report(number)
    assert pending["text"] == "Streetlight broken"
    assert has_pending_report(number) is False  # popped, not just peeked

    # Popping again should return None, not raise
    assert pop_pending_report(number) is None
