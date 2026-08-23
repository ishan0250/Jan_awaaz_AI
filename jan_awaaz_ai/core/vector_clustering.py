"""
core/vector_clustering.py

Duplicate suppression: when a new ticket comes in, check if any existing
open ticket is (a) within DUPLICATE_RADIUS_METERS and (b) semantically
similar above DUPLICATE_SIMILARITY_THRESHOLD using text-embedding-004
cosine similarity. If both hold, merge into that ticket's cluster instead
of creating a new one.

This module only computes — it doesn't touch the DB directly except via
data_store.db's read helper, so it stays testable with fake ticket lists.
"""

import numpy as np
from google import genai
from config import (GEMINI_EMBEDDING_MODEL, DUPLICATE_RADIUS_METERS,
                     DUPLICATE_SIMILARITY_THRESHOLD)
from utils.geo import haversine_meters


def embed_text(client: "genai.Client", text: str) -> list[float]:
    result = client.models.embed_content(model=GEMINI_EMBEDDING_MODEL, contents=text)
    # google-genai returns .embeddings[0].values for the embed_content call
    return list(result.embeddings[0].values)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = (np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def find_duplicate_match(new_lat: float, new_lon: float, new_embedding: list[float],
                          candidates: list[tuple["Ticket", list[float] | None]]
                          ) -> "Ticket | None":
    """
    candidates: list of (Ticket, embedding) pairs for currently-open tickets,
    e.g. from data_store.db.list_open_tickets_with_location().

    Returns the best-matching master Ticket if one clears both the distance
    and similarity thresholds, else None.
    """
    best_ticket = None
    best_similarity = 0.0

    for ticket, embedding in candidates:
        if embedding is None or ticket.latitude is None or ticket.longitude is None:
            continue
        distance = haversine_meters(new_lat, new_lon, ticket.latitude, ticket.longitude)
        if distance > DUPLICATE_RADIUS_METERS:
            continue
        similarity = cosine_similarity(new_embedding, embedding)
        if similarity >= DUPLICATE_SIMILARITY_THRESHOLD and similarity > best_similarity:
            best_similarity = similarity
            best_ticket = ticket

    return best_ticket
