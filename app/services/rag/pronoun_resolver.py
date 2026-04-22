"""Multi-turn pronoun / elided-subject resolution helpers.

These pure functions drive the "no-LLM" reference resolution strategy:

- `has_medicine_reference` decides whether the current query already
  points to a concrete medicine, using the existing pgvector top-1
  similarity (no extra embedding call).
- `collect_recent_medicine_names` walks stored message metadata newest
  first and extracts distinct medicine names so the pipeline can prepend
  them to an ambiguous query.

When both signals fail (no strong match now + no history mention), the
pipeline falls back to policy 2: ask the user to clarify which medicine
they mean (system-prompt driven, no extra LLM beyond the primary reply).
"""

from typing import Any

from app.dtos.rag import SearchResult

DEFAULT_MEDICINE_REFERENCE_THRESHOLD: float = 0.5


def has_medicine_reference(
    search_results: list[SearchResult],
    threshold: float = DEFAULT_MEDICINE_REFERENCE_THRESHOLD,
) -> bool:
    """Return True if the top-1 search result is confident enough to be "the" medicine.

    Args:
        search_results: Output of `HybridRetriever.retrieve` for the current query.
        threshold: Minimum vector similarity of the top-1 result required to
            treat the query as already referring to a specific medicine.

    Returns:
        True when at least one result meets the threshold; False otherwise.
    """
    if not search_results:
        return False
    return search_results[0].vector_score >= threshold


def collect_recent_medicine_names(
    history_metadata: list[dict[str, Any]],
    limit: int = 3,
) -> list[str]:
    """Collect distinct medicine names from history metadata, newest first.

    Args:
        history_metadata: List of `messages.metadata` dicts in chronological
            order (oldest first), matching the pipeline's history convention.
        limit: Maximum number of distinct names to return.

    Returns:
        Distinct medicine names ordered by most-recent mention, capped at `limit`.
    """
    if not history_metadata:
        return []

    names: list[str] = []
    seen: set[str] = set()

    for entry in reversed(history_metadata):
        retrieval = entry.get("retrieval") if isinstance(entry, dict) else None
        if not isinstance(retrieval, dict):
            continue
        candidates = retrieval.get("medicine_names")
        if not isinstance(candidates, list):
            continue
        for name in candidates:
            if not isinstance(name, str) or not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
            if len(names) >= limit:
                return names

    return names
