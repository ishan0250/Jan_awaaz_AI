"""
core/ai_ingestion.py

Turns raw citizen input (text, or audio bytes, or image bytes) into
structured English JSON using Gemini 2.5 Flash's multimodal understanding.

This is the ONLY module that talks to Gemini for extraction. Everything
downstream (routing, scoring, clustering) works off the structured dict
this returns, and doesn't care whether the original input was Hindi audio,
a photo, or English text.
"""

import json
import os
from google import genai
from config import GEMINI_MULTIMODAL_MODEL

_EXTRACTION_PROMPT = """You are the intake engine for a civic grievance platform.
Given the citizen's input (text, and/or an attached audio note, and/or an
attached photo), produce a structured extraction.

Respond ONLY with JSON, no markdown fences, in this exact shape:
{
  "summary_en": "one or two sentence English summary of the issue",
  "original_language": "ISO language name, e.g. Hindi, Tamil, English",
  "detected_hazard_type": "short phrase, e.g. 'sparking transformer'",
  "suggested_intensity": 1-5,
  "suggested_urgency": 1-5
}

Guidance for suggested_intensity (physical/structural damage scale):
1 = cosmetic/negligible, 2 = localized minor, 3 = neighborhood-level,
4 = major infrastructure rupture, 5 = mass structural/critical.

Guidance for suggested_urgency (threat-to-life/time-criticality scale):
1 = no safety threat, 2 = minor discomfort, 3 = potential hazard if
unaddressed, 4 = direct public health/safety hazard, 5 = imminent threat
to life (e.g. live sparking wire, road collapse).

If audio is in a language other than English, transcribe and translate it
into summary_en. Be conservative: don't inflate severity without cause.
"""


def get_client() -> "genai.Client":
    """Central place to construct the Gemini client so tests can monkeypatch it."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=api_key)


def extract_from_input(client: "genai.Client", *, text: str = "",
                        audio_bytes: bytes | None = None,
                        audio_mime_type: str = "audio/ogg",
                        image_bytes: bytes | None = None,
                        image_mime_type: str = "image/jpeg") -> dict:
    """
    Calls Gemini with whatever combination of text/audio/image is provided
    and returns the structured extraction dict described in the prompt.

    Raises RuntimeError with a readable message on failure, so the calling
    Streamlit page can show a clean error instead of a raw traceback.
    """
    parts: list[dict] = []
    if text:
        parts.append({"text": f"Citizen text input: {text}"})
    if audio_bytes:
        parts.append({"inline_data": {"mime_type": audio_mime_type, "data": audio_bytes}})
    if image_bytes:
        parts.append({"inline_data": {"mime_type": image_mime_type, "data": image_bytes}})

    if not parts:
        raise ValueError("At least one of text, audio_bytes, or image_bytes is required.")

    parts.insert(0, {"text": _EXTRACTION_PROMPT})

    try:
        response = client.models.generate_content(
            model=GEMINI_MULTIMODAL_MODEL,
            contents=parts,
        )
        raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Gemini extraction failed: {exc}") from exc

    # Defensive defaults in case the model omits a field
    parsed.setdefault("summary_en", text or "")
    parsed.setdefault("original_language", "English")
    parsed.setdefault("detected_hazard_type", "")
    parsed.setdefault("suggested_intensity", 2)
    parsed.setdefault("suggested_urgency", 2)
    parsed["suggested_intensity"] = max(1, min(5, int(parsed["suggested_intensity"])))
    parsed["suggested_urgency"] = max(1, min(5, int(parsed["suggested_urgency"])))
    return parsed
