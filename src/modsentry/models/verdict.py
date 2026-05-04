from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class VerdictLabel(str, Enum):
    SAFE = "SAFE"
    UNSAFE = "UNSAFE"


@dataclass(frozen=True)
class Verdict:
    """
    The result of evaluating a ``ModerationRequest``.

    Attributes
    ----------
    label:
        ``SAFE`` or ``UNSAFE``.
    confidence:
        LLM-reported confidence score in [0.0, 1.0].
    reason:
        One-sentence explanation from the classifier.
    cached:
        True if this verdict was served from cache without consulting the LLM.
    policy_id:
        The policy under which this verdict was produced.
    """

    label: VerdictLabel
    confidence: float
    reason: str
    cached: bool = False
    policy_id: str = ""

    @property
    def is_safe(self) -> bool:
        return self.label == VerdictLabel.SAFE

    @property
    def is_unsafe(self) -> bool:
        return self.label == VerdictLabel.UNSAFE
