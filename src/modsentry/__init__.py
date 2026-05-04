"""
modsentry — Multi-tenant LLM content moderation service.

Public surface:
    build_moderation_platform()  — factory; accepts an optional llm_gateway
                                   for dependency injection in tests.
    ModerationRequest            — request dataclass
    Verdict                      — result dataclass
    PolicyNotFound               — raised when policy_id is unknown
"""

from .bootstrap import build_moderation_platform
from .models.request import ModerationRequest
from .models.verdict import Verdict
from .core.moderation import PolicyNotFound

__all__ = [
    "build_moderation_platform",
    "ModerationRequest",
    "Verdict",
    "PolicyNotFound",
]
