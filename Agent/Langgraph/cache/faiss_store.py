from __future__ import annotations

import sys
import os
# Ensure backend is importable regardless of working directory
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from difflib import SequenceMatcher
from typing import Any, Dict, Optional

from backend import store
from backend.config import settings


CACHE_VERSION = "v2"


def _normalize(prompt: str) -> str:
    return " ".join(prompt.lower().split())


def _cache_key(prompt: str) -> str:
    return f"{CACHE_VERSION}::{_normalize(prompt)}"


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def lookup(prompt: str) -> Optional[Dict[str, Any]]:
    """Return best cache hit for prompt, or None."""
    best: Optional[Dict[str, Any]] = None
    for row in store.get_cache_entries(limit=settings.cache_max_size):
        # The stored key is "v2::<normalized_prompt>"; strip the prefix to get the original normalized text
        stored_key = row.get("prompt", "")
        prefix = f"{CACHE_VERSION}::"
        if not stored_key.startswith(prefix):
            continue
        stored_normalized = stored_key[len(prefix):]
        similarity = _similarity(prompt, stored_normalized)
        if similarity < settings.cache_similarity_threshold:
            continue
        candidate = dict(row)
        candidate["similarity"] = round(similarity, 4)
        if best is None or candidate["similarity"] > best["similarity"]:
            best = candidate
    return best


def add(prompt: str, response: str, model_id: str, model_label: str, similarity: float, cost_saved: float) -> int:
    return store.create_cache_entry(_cache_key(prompt), response, model_id, model_label, similarity, cost_saved)


def increment_hit(entry_id: int) -> None:
    store.increment_cache_hit(entry_id)
