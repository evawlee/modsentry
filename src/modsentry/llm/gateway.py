from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from ..core.prompt_pair import PromptPair
from ..models.verdict import Verdict, VerdictLabel


class LLMGateway(ABC):
    """Abstract interface for the LLM completion backend."""

    @abstractmethod
    def complete(self, prompt: PromptPair) -> str:
        """
        Send *prompt* to the LLM and return the raw response string.

        Implementations must raise ``LLMError`` on connectivity or quota
        failures.
        """
        ...


class LLMError(RuntimeError):
    """Raised when the LLM backend returns an error or unexpected response."""


class StubLLMGateway(LLMGateway):
    """
    Placeholder gateway for environments without LLM credentials.

    Always returns SAFE — do not use in production or security-sensitive tests.
    """

    def complete(self, prompt: PromptPair) -> str:  # pragma: no cover
        return '{"verdict": "SAFE", "confidence": 0.5, "reason": "stub response"}'


# ---------------------------------------------------------------------------
# Response parsing utility (shared by gateway implementations and tests)
# ---------------------------------------------------------------------------

_JSON_EXTRACT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_llm_response(raw: str) -> Verdict:
    """
    Parse a raw LLM response string into a ``Verdict``.

    Raises ``LLMError`` if the response cannot be parsed or is missing
    required fields.
    """
    match = _JSON_EXTRACT_RE.search(raw)
    if not match:
        raise LLMError(f"No JSON object found in LLM response: {raw!r}")

    try:
        data: dict[str, Any] = json.loads(match.group())
    except json.JSONDecodeError as exc:
        raise LLMError(f"Malformed JSON in LLM response: {exc}") from exc

    raw_label = data.get("verdict", "")
    try:
        label = VerdictLabel(raw_label.upper())
    except (ValueError, AttributeError) as exc:
        raise LLMError(f"Unknown verdict label {raw_label!r}") from exc

    confidence = float(data.get("confidence", 0.5))
    reason = str(data.get("reason", ""))

    return Verdict(label=label, confidence=confidence, reason=reason)
