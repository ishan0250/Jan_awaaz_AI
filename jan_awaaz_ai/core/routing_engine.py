"""
core/routing_engine.py

Two-tier department resolver.

Tier 1: match the (English, translated) complaint text against keyword
sets defined in config.DEPARTMENTS. This is intentionally simple —
substring matching — because for a 36-hour build it's fast, explainable
in front of judges, and easy to extend. If you have time later, swap
`match_department()`'s internals for a Gemini structured-output call
(ask it to pick from the exact department list) without touching any
caller — that's why routing is isolated in one function.

Tier 2: anything that matches nothing falls back to the District Nodal
Grievance Officer (DM Office), guaranteeing zero dropped tickets.
"""

from config import DEPARTMENTS, FALLBACK_DEPARTMENT


def match_department(summary_en: str) -> dict:
    """
    Returns:
        {
          "department_code": str,
          "department_display": str,
          "is_fallback_routed": bool,
          "note": str,
        }
    """
    text = (summary_en or "").lower()

    best_code = None
    best_hits = 0
    for code, dept in DEPARTMENTS.items():
        hits = sum(1 for kw in dept["keywords"] if kw in text)
        if hits > best_hits:
            best_hits = hits
            best_code = code

    if best_code:
        dept = DEPARTMENTS[best_code]
        return {
            "department_code": best_code,
            "department_display": dept["display_name"],
            "is_fallback_routed": False,
            "note": f"Matched on {best_hits} keyword(s).",
        }

    # Tier 2 fail-safe — nothing dropped, ever
    return {
        "department_code": "DM_OFFICE_FALLBACK",
        "department_display": FALLBACK_DEPARTMENT["display_name"],
        "is_fallback_routed": True,
        "note": FALLBACK_DEPARTMENT["note"],
    }
