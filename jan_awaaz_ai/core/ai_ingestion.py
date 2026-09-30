"""
core/ai_ingestion.py
Extracts grievance details, target local bodies, and geocodes coordinates via Gemini.
"""

import json
import os
from google import genai
from config import GEMINI_MULTIMODAL_MODEL

_EXTRACTION_PROMPT = """You are the intake engine for a Indian civic grievance platform.
Given citizen input (text, state/district/landmark details, audio, or image), extract structured output.

Respond ONLY with JSON, no markdown fences:
{
  "summary_en": "1-2 sentence English summary of issue and specific location",
  "original_language": "ISO language name (e.g. English, Hindi)",
  "detected_hazard_type": "e.g. pothole, broken pipeline, transformer issue",
  "department_display": "Specific department, e.g. 'PWD / Road Infrastructure', 'Jal Shakti / Water Board', 'State DISCOM Electricity'",
  "department_code": "SHORT_CODE e.g. PWD, JAL_SHAKTI, DISCOM, SANITATION",
  "suggested_intensity": 1-5,
  "suggested_urgency": 1-5,
  "latitude": float approx latitude for landmark/district in India,
  "longitude": float approx longitude for landmark/district in India
}

Guidance:
Intensity = physical structural severity (1-5).
Urgency = public safety threat level (1-5).
Provide accurate approximate coordinates (latitude/longitude) for the mentioned district/city/landmark in India.
"""


def get_client() -> "genai.Client":
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)


def extract_from_input(client: "genai.Client", *, text: str = "",
                        audio_bytes: bytes | None = None,
                        audio_mime_type: str = "audio/wav",
                        image_bytes: bytes | None = None,
                        image_mime_type: str = "image/jpeg") -> dict:
    
    contents = [_EXTRACTION_PROMPT]

    if text:
        contents.append(f"Input: {text}")
    if audio_bytes:
        contents.append({"mime_type": audio_mime_type, "data": audio_bytes})
    if image_bytes:
        contents.append({"mime_type": image_mime_type, "data": image_bytes})

    try:
        response = client.models.generate_content(
            model=GEMINI_MULTIMODAL_MODEL,
            contents=contents,
        )
        raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"Gemini extraction failed: {exc}") from exc

    parsed.setdefault("summary_en", text or "Civic Complaint")
    parsed.setdefault("original_language", "English")
    parsed.setdefault("department_display", "Municipal Public Works Department")
    parsed.setdefault("department_code", "MUNI_PWD")
    parsed.setdefault("suggested_intensity", 2)
    parsed.setdefault("suggested_urgency", 2)
    parsed.setdefault("latitude", 28.6692)
    parsed.setdefault("longitude", 77.4538)

    return parsed