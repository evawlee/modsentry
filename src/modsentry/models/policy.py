from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    """Immutable policy configuration record."""

    id: str
    name: str
    # "low" | "medium" | "high" — controls how much context the classifier receives
    severity_band: str
    # Terms that *always* trigger UNSAFE under this policy, regardless of LLM response.
    # Used by the enforcement layer to hard-block known-bad content.
    hard_block_terms: frozenset[str] = frozenset()

    def __str__(self) -> str:
        return f"Policy({self.id!r}, severity={self.severity_band})"
