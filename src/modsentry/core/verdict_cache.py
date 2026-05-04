from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from ..models.verdict import Verdict


@dataclass
class _CacheEntry:
    verdict: Verdict
    # Stored for traceability — lets callers confirm which policy produced
    # the cached result when auditing cache contents.
    policy_id: str


class VerdictCache:
    """
    In-process LRU-style verdict cache.

    Keys are derived from the evaluated content so that identical submissions
    do not require a round-trip to the LLM on subsequent requests.

    Policy awareness: callers supply ``policy_id`` to ``get`` and ``put`` so
    that cached entries carry policy provenance metadata.  The ``policy_id``
    is stored alongside the verdict in the cache entry and is available for
    downstream audit and logging.

    Thread-safety: this implementation is single-threaded; no locking is
    applied.  Callers that require concurrent access must add their own
    synchronisation.
    """

    def __init__(self, max_size: int = 1_024) -> None:
        self._max_size = max_size
        self._store: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_key(self, content: str) -> str:
        """
        Derive a stable cache key from *content*.

        SHA-256 produces a fixed-length, collision-resistant key.  The raw
        content string is not stored directly to avoid unbounded memory growth
        from long submissions.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, content: str, policy_id: str) -> Optional[Verdict]:
        """
        Return a cached ``Verdict`` for *content* evaluated under *policy_id*,
        or ``None`` on a cache miss.
        """
        key = self._make_key(content)
        entry = self._store.get(key)
        if entry is None:
            return None
        return entry.verdict

    def put(self, content: str, policy_id: str, verdict: Verdict) -> None:
        """
        Store *verdict* for *content* evaluated under *policy_id*.

        Silently evicts the oldest entry when the cache is full.
        """
        if len(self._store) >= self._max_size:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

        key = self._make_key(content)
        self._store[key] = _CacheEntry(verdict=verdict, policy_id=policy_id)

    def invalidate(self, content: str) -> bool:
        """Remove the cache entry for *content*.  Returns True if an entry existed."""
        key = self._make_key(content)
        return self._store.pop(key, None) is not None

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
