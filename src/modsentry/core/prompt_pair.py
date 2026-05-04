from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPair:
    """A (system, user) message pair ready to send to the LLM gateway."""

    system: str
    user: str
