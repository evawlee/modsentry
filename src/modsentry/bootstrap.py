from __future__ import annotations

from .core.moderation import ModerationService
from .core.prompt_engine import PromptEngine
from .core.sanitizer import InputSanitizer
from .core.verdict_cache import VerdictCache
from .llm.gateway import LLMGateway, StubLLMGateway
from .models.policy import Policy

# ---------------------------------------------------------------------------
# Built-in policy registry
# ---------------------------------------------------------------------------
_LENIENT_POLICY = Policy(
    id="lenient",
    name="Community Standard",
    severity_band="low",
    hard_block_terms=frozenset({"explosive synthesis", "weapon assembly instructions"}),
)

_STRICT_POLICY = Policy(
    id="strict",
    name="Brand Safety",
    severity_band="high",
    hard_block_terms=frozenset(
        {
            "explosive synthesis",
            "weapon assembly instructions",
            "controlled substance acquisition",
        }
    ),
)

_DEFAULT_POLICIES: dict[str, Policy] = {
    p.id: p for p in (_LENIENT_POLICY, _STRICT_POLICY)
}


def build_moderation_platform(
    *,
    llm_gateway: LLMGateway | None = None,
    extra_policies: dict[str, Policy] | None = None,
    cache_max_size: int = 1_024,
) -> ModerationService:
    """
    Assemble and return a fully wired ``ModerationService``.

    Parameters
    ----------
    llm_gateway:
        LLM backend to use.  Defaults to ``StubLLMGateway`` (always-SAFE stub).
        Pass a ``FakeLLMGateway`` or a real gateway implementation here.
    extra_policies:
        Additional ``Policy`` objects to register alongside the built-in
        ``"lenient"`` and ``"strict"`` policies.
    cache_max_size:
        Maximum number of verdict entries to hold in the in-process cache.
    """
    gateway = llm_gateway if llm_gateway is not None else StubLLMGateway()

    policies = dict(_DEFAULT_POLICIES)
    if extra_policies:
        policies.update(extra_policies)

    sanitizer = InputSanitizer()
    engine = PromptEngine(sanitizer)
    cache = VerdictCache(max_size=cache_max_size)

    return ModerationService(
        policies=policies,
        prompt_engine=engine,
        cache=cache,
        llm=gateway,
    )
