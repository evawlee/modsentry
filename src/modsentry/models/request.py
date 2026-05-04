from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ModerationRequest:
    """
    A content moderation request submitted by an API caller.

    Parameters
    ----------
    content:
        The text payload to evaluate.  Required.
    context_hint:
        Optional free-text context provided by the requester to help the
        classifier (e.g. "educational science platform" or "adult fiction site").
        This field is caller-supplied and should be treated as untrusted input.
    request_id:
        Optional opaque identifier for correlation in logs.
    """

    content: str
    context_hint: str | None = field(default=None)
    request_id: str | None = field(default=None)
