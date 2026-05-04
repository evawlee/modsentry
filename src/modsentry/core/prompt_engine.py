from __future__ import annotations

from ..models.policy import Policy
from ..models.request import ModerationRequest
from .prompt_pair import PromptPair
from .sanitizer import InputSanitizer

# ---------------------------------------------------------------------------
# System-message template.
#
# {policy_name}   — internal value, safe to interpolate.
# {severity_band} — internal value, safe to interpolate.
# {context_hint}  — caller-supplied context from ModerationRequest.context_hint.
#                   Inserted so the classifier has requester context when
#                   making borderline decisions (e.g. "adult fiction platform"
#                   may change how mature-but-legal content is treated).
# ---------------------------------------------------------------------------
_SYSTEM_TEMPLATE = """\
You are a content safety classifier operating under the {policy_name!r} policy.
Severity band: {severity_band}
Requester context: {context_hint}
---
Evaluate the content in the user message.
Respond with ONLY a JSON object — no prose, no markdown:
{{"verdict": "SAFE" or "UNSAFE", "confidence": <float 0.0-1.0>, "reason": "<one sentence>"}}\
"""


class PromptEngine:
    """
    Builds (system, user) prompt pairs for the LLM gateway.

    The *system* message encodes policy configuration and request context.
    The *user* message carries the sanitized content to be evaluated.
    """

    def __init__(self, sanitizer: InputSanitizer) -> None:
        self._sanitizer = sanitizer

    def build(self, request: ModerationRequest, policy: Policy) -> PromptPair:
        """
        Construct a ``PromptPair`` for *request* under *policy*.

        The content field is passed through ``InputSanitizer.clean`` before
        being placed in the user message.
        """
        clean_content = self._sanitizer.clean(request.content)

        # context_hint is an optional free-text field from the API caller that
        # provides context about the submission source.
        system = _SYSTEM_TEMPLATE.format(
            policy_name=policy.name,
            severity_band=policy.severity_band,
            context_hint=request.context_hint or "not provided",
        )

        user = f"Content to evaluate:\n{clean_content}"
        return PromptPair(system=system, user=user)
