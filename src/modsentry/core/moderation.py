from __future__ import annotations

from ..models.policy import Policy
from ..models.request import ModerationRequest
from ..models.verdict import Verdict, VerdictLabel
from ..llm.gateway import LLMGateway, parse_llm_response
from .prompt_engine import PromptEngine
from .verdict_cache import VerdictCache


class PolicyNotFound(KeyError):
    """Raised when a requested policy_id is not registered."""


class ModerationService:
    """
    Orchestrates the full moderation pipeline:
      1. Resolve policy by id.
      2. Check verdict cache.
      3. On miss: build prompt → call LLM → parse response.
      4. Store result in cache.
      5. Apply hard-block overrides from policy config.
    """

    def __init__(
        self,
        policies: dict[str, Policy],
        prompt_engine: PromptEngine,
        cache: VerdictCache,
        llm: LLMGateway,
    ) -> None:
        self._policies = policies
        self._engine = prompt_engine
        self._cache = cache
        self._llm = llm

    def evaluate(self, request: ModerationRequest, policy_id: str) -> Verdict:
        policy = self._policies.get(policy_id)
        if policy is None:
            raise PolicyNotFound(f"Unknown policy {policy_id!r}")

        cached = self._cache.get(request.content, policy_id)
        if cached is not None:
            return Verdict(
                label=cached.label,
                confidence=cached.confidence,
                reason=cached.reason,
                cached=True,
                policy_id=policy_id,
            )

        prompt = self._engine.build(request, policy)
        raw = self._llm.complete(prompt)
        verdict = parse_llm_response(raw)

        # Hard-block override: certain terms are always UNSAFE regardless of LLM opinion.
        if any(term in request.content.lower() for term in policy.hard_block_terms):
            verdict = Verdict(
                label=VerdictLabel.UNSAFE,
                confidence=1.0,
                reason="hard-block term matched",
                policy_id=policy_id,
            )
        else:
            verdict = Verdict(
                label=verdict.label,
                confidence=verdict.confidence,
                reason=verdict.reason,
                cached=False,
                policy_id=policy_id,
            )

        self._cache.put(request.content, policy_id, verdict)
        return verdict

    def evaluate_batch(
        self, requests: list[ModerationRequest], policy_id: str
    ) -> list[Verdict]:
        return [self.evaluate(req, policy_id) for req in requests]
