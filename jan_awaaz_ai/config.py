"""
config.pyz
Single place for every constant the rest of the app depends on.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DB_PATH = BASE_DIR / "data" / "jan_awaaz.db"
SEED_JSON_PATH = BASE_DIR / "data" / "mock_tickets.json"

# Updated active Gemini models
GEMINI_MULTIMODAL_MODEL = "gemini-3.6-flash"
GEMINI_EMBEDDING_MODEL = "text-embedding-004"

MAX_CROWD_BOOST = 5

SLA_TIERS = [
    (20, "CRITICAL EMERGENCY", 4, "4 Hours",
     "Immediate SMS/Email alert to District Magistrate & Chief Engineer."),
    (12, "HIGH PRIORITY", 24, "24 Hours",
     "Escalates to Executive Engineer if unassigned within 12 hours."),
    (6, "MEDIUM PRIORITY", 72, "72 Hours (3 Days)",
     "Queued in Assistant Engineer department dashboard."),
    (0, "ROUTINE CIVIC ISSUE", 168, "7 Days",
     "Scheduled in regular weekly maintenance plan."),
]

MIN_CONFIDENCE_FOR_FULL_PRIORITY = "medium"

DEPARTMENTS = {
    "PWD_CPWD_NHAI": {
        "display_name": "PWD / CPWD / NHAI",
        "keywords": ["pothole", "footpath", "road damage", "bridge crack",
                     "highway", "road crack", "broken road"],
    },
    "JAL_SHAKTI": {
        "display_name": "Jal Shakti / Municipal Water Board",
        "keywords": ["water pipe", "pipe burst", "contaminated water",
                      "sewer overflow", "sewage", "no water supply", "leak"],
    },
    "DISCOM": {
        "display_name": "State DISCOM / Electricity Board",
        "keywords": ["power line", "transformer", "sparking", "electric pole",
                      "blackout", "live wire", "electricity", "short circuit"],
    },
    "ULB_SANITATION": {
        "display_name": "Urban Local Bodies (ULB) / Sanitation",
        "keywords": ["garbage", "dead animal", "public toilet", "waste",
                      "trash", "dump"],
    },
    "TRAFFIC_TRANSPORT": {
        "display_name": "Traffic Police & Transport Dept",
        "keywords": ["traffic signal", "blocked road", "hazard sign",
                      "traffic light", "signal not working"],
    },
    "HEALTH_VECTOR_CONTROL": {
        "display_name": "Health & Family Welfare / Vector Control",
        "keywords": ["stagnant water", "mosquito", "dengue", "malaria"],
    },
    "FOREST_ENVIRONMENT": {
        "display_name": "Forest & Environment / SPCB",
        "keywords": ["tree cutting", "illegal logging", "toxic dumping",
                      "air pollution", "industrial waste"],
    },
}

FALLBACK_DEPARTMENT = {
    "display_name": "District Nodal Grievance Officer (DM Office)",
    "reassignment_window_hours": 24,
    "note": ("Unclassified complaints are routed here per escalation policy."),
}