"""
core/ticket_pipeline.py
Multimodal ticket extraction engine using Google Gemini API.
"""

import json
import io
import sqlite3
import uuid
from datetime import datetime
from PIL import Image
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, DB_PATH, GEMINI_MULTIMODAL_MODEL

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are the intake extraction engine for Jan-Awaaz AI, an Indian civic grievance portal.
Analyze the user's grievance input (text, image, or transcribed voice) and output a clean JSON object.

Extract and categorize the issue strictly adhering to these JSON keys:
1. "summary_en": Concise English summary of the civic problem.
2. "department_key": One of ["pwd", "jal_shakti", "ulb", "discom"].
3. "department_display": Official Indian authority name (e.g., "Jal Shakti / Municipal Water Board", "PWD / Road Infrastructure", "State DISCOM / Electricity Board", "Urban Local Bodies (ULB) / Sanitation").
4. "urgency": Integer 1 to 5 (Immediate public threat level).
5. "intensity": Integer 1 to 5 (Structural or physical damage level).
6. "sla_hours": Standard SLA timeline in hours (24, 48, or 72 based on urgency).
7. "rpi_score": Calculated Relative Priority Index (urgency * 10 + intensity * 5).
8. "latitude": Estimated latitude float for the mentioned locality/landmark (or center of district if generic).
9. "longitude": Estimated longitude float for the mentioned locality/landmark.
"""


def extract_ticket_details(user_text: str, state: str, district: str, location_note: str, image_bytes=None):
    """Call Gemini Flash with multimodal inputs to extract structured ticket JSON."""

    full_prompt = f"""
    State: {state}
    District/ULB: {district}
    Detailed Address/Landmark: {location_note}
    User Grievance Text: {user_text}
    """

    content_payload = [SYSTEM_PROMPT, full_prompt]

    if image_bytes:
        if isinstance(image_bytes, dict):
            image_bytes = image_bytes.get("data", b"")

        if isinstance(image_bytes, (bytes, bytearray)) and len(image_bytes) > 0:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                content_payload.append(img)
            except Exception as e:
                print(f"Warning: Failed to convert image bytes: {e}")

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "summary_en": {"type": "STRING"},
            "department_key": {"type": "STRING"},
            "department_display": {"type": "STRING"},
            "urgency": {"type": "INTEGER"},
            "intensity": {"type": "INTEGER"},
            "sla_hours": {"type": "INTEGER"},
            "rpi_score": {"type": "INTEGER"},
            "latitude": {"type": "NUMBER"},
            "longitude": {"type": "NUMBER"}
        },
        "required": ["summary_en", "department_key", "department_display", "urgency", "intensity", "sla_hours", "rpi_score"]
    }

    response = client.models.generate_content(
        model=GEMINI_MULTIMODAL_MODEL,
        contents=content_payload,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2
        )
    )

    return json.loads(response.text)


def create_and_store_ticket(state: str, district: str, location_note: str, user_text: str, image_bytes=None):
    """Extract ticket data via Gemini and persist to SQLite cleanly."""
    extracted = extract_ticket_details(user_text, state, district, location_note, image_bytes)

    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    created_at = datetime.now().isoformat()

    candidate_data = {
        "id": ticket_id,
        "created_at": created_at,
        "state": state,
        "district": district,
        "evidence_note": location_note,
        "raw_text": user_text,
        "description_text": user_text,
        "summary_en": extracted.get("summary_en"),
        "department_key": extracted.get("department_key"),
        "department_display": f"{extracted.get('department_display')} - {district}, {state}",
        "urgency": extracted.get("urgency"),
        "intensity": extracted.get("intensity"),
        "sla_hours": extracted.get("sla_hours"),
        "rpi_score": extracted.get("rpi_score"),
        "latitude": extracted.get("latitude"),
        "longitude": extracted.get("longitude"),
        "status": "open"
    }

    # Dynamically match SQLite table columns so missing/extra keys never throw errors
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(tickets)")
    existing_cols = [row[1] for row in cursor.fetchall()]

    insert_cols = [col for col in existing_cols if col in candidate_data]
    insert_vals = [candidate_data[col] for col in insert_cols]

    placeholders = ", ".join(["?"] * len(insert_cols))
    col_names = ", ".join(insert_cols)

    sql = f"INSERT INTO tickets ({col_names}) VALUES ({placeholders})"
    cursor.execute(sql, insert_vals)

    conn.commit()
    conn.close()

    return ticket_id, extracted