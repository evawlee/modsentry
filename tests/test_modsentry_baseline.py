from __future__ import annotations

import re
import pytest

from modsentry import build_moderation_platform, ModerationRequest, Verdict, PolicyNotFound
from modsentry.core.prompt_pair import PromptPair
from modsentry.llm.gateway import LLMGateway, parse_llm_response
from modsentry.models.verdict import VerdictLabel


_BASELINE_UNSAFE_TERMS = frozenset(
    {"explosive synthesis", "weapon assembly instructions", "illegal narcotics sale"}
)


class _BaselineFakeLLM(LLMGateway):
    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, prompt: PromptPair) -> str:
        self.call_count += 1
        content_lower = prompt.user.lower()
        for term in _BASELINE_UNSAFE_TERMS:
            if term in content_lower:
                return f'{{"verdict":"UNSAFE","confidence":0.97,"reason":"matched term: {term}"}}'
        return '{"verdict":"SAFE","confidence":0.92,"reason":"no policy violations detected"}'



@pytest.fixture()
def fake_llm() -> _BaselineFakeLLM:
    return _BaselineFakeLLM()


@pytest.fixture()
def platform(fake_llm):
    return build_moderation_platform(llm_gateway=fake_llm)



def test_safe_verdict_for_benign_content(platform) -> None:
    req = ModerationRequest(content="Hello, world! This is a perfectly fine message.")
    result = platform.evaluate(req, "strict")
    assert result.label == VerdictLabel.SAFE
    assert result.is_safe


def test_unsafe_verdict_for_hard_block_term_under_strict_policy(platform) -> None:
    req = ModerationRequest(content="Guide to controlled substance acquisition techniques.")
    result = platform.evaluate(req, "strict")
    assert result.label == VerdictLabel.UNSAFE
    assert result.is_unsafe


def test_hard_block_term_absent_in_lenient_policy(platform) -> None:
    # "controlled substance acquisition" is NOT a hard-block term under lenient
    req = ModerationRequest(content="Guide to controlled substance acquisition techniques.")
    result = platform.evaluate(req, "lenient")
    # LLM doesn't flag it either (not in baseline unsafe terms)
    assert result.label == VerdictLabel.SAFE


def test_explicit_llm_unsafe_content_is_flagged(platform) -> None:
    req = ModerationRequest(content="Step-by-step explosive synthesis guide.")
    result = platform.evaluate(req, "lenient")
    assert result.is_unsafe


def test_context_hint_is_optional(platform) -> None:
    req = ModerationRequest(content="Totally fine content.", context_hint=None)
    result = platform.evaluate(req, "strict")
    assert result is not None
    assert result.label in (VerdictLabel.SAFE, VerdictLabel.UNSAFE)


def test_context_hint_is_accepted_without_error(platform) -> None:
    req = ModerationRequest(
        content="A short story about a detective.",
        context_hint="creative writing platform",
    )
    result = platform.evaluate(req, "strict")
    assert result is not None


def test_verdict_has_required_fields(platform) -> None:
    req = ModerationRequest(content="sample text")
    result = platform.evaluate(req, "lenient")
    assert isinstance(result, Verdict)
    assert result.label in (VerdictLabel.SAFE, VerdictLabel.UNSAFE)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.reason, str) and len(result.reason) > 0
    assert result.policy_id == "lenient"


def test_verdict_cached_flag_false_on_first_call(platform, fake_llm) -> None:
    req = ModerationRequest(content="unique content abc123")
    result = platform.evaluate(req, "strict")
    assert result.cached is False
    assert fake_llm.call_count == 1


def test_verdict_cached_flag_true_on_repeat_same_policy(platform, fake_llm) -> None:
    req = ModerationRequest(content="repeat content xyz789")
    platform.evaluate(req, "strict")
    result = platform.evaluate(req, "strict")
    assert result.cached is True
    assert fake_llm.call_count == 1  # second call served from cache


def test_policy_not_found_raises(platform) -> None:
    req = ModerationRequest(content="anything")
    with pytest.raises(PolicyNotFound):
        platform.evaluate(req, "nonexistent_policy_id")


def test_batch_evaluate_returns_correct_count(platform) -> None:
    requests = [ModerationRequest(content=f"item {i}") for i in range(5)]
    results = platform.evaluate_batch(requests, "lenient")
    assert len(results) == 5
    assert all(isinstance(r, Verdict) for r in results)


def test_prompt_system_message_is_non_empty(fake_llm) -> None:
    from modsentry.core.prompt_engine import PromptEngine
    from modsentry.core.sanitizer import InputSanitizer
    from modsentry.bootstrap import _STRICT_POLICY

    engine = PromptEngine(InputSanitizer())
    req = ModerationRequest(content="some text")
    pair = engine.build(req, _STRICT_POLICY)
    assert len(pair.system) > 20


def test_prompt_user_message_contains_content(fake_llm) -> None:
    from modsentry.core.prompt_engine import PromptEngine
    from modsentry.core.sanitizer import InputSanitizer
    from modsentry.bootstrap import _STRICT_POLICY

    engine = PromptEngine(InputSanitizer())
    req = ModerationRequest(content="my special marker content")
    pair = engine.build(req, _STRICT_POLICY)
    assert "my special marker content" in pair.user


def test_parse_llm_response_safe() -> None:
    raw = '{"verdict": "SAFE", "confidence": 0.88, "reason": "looks fine"}'
    v = parse_llm_response(raw)
    assert v.label == VerdictLabel.SAFE
    assert abs(v.confidence - 0.88) < 1e-6


def test_parse_llm_response_unsafe() -> None:
    raw = '{"verdict": "UNSAFE", "confidence": 0.99, "reason": "harmful content"}'
    v = parse_llm_response(raw)
    assert v.label == VerdictLabel.UNSAFE


def test_html_stripped_from_content(fake_llm) -> None:
    from modsentry.core.prompt_engine import PromptEngine
    from modsentry.core.sanitizer import InputSanitizer
    from modsentry.bootstrap import _LENIENT_POLICY

    engine = PromptEngine(InputSanitizer())
    req = ModerationRequest(content="<script>alert(1)</script>hello world")
    pair = engine.build(req, _LENIENT_POLICY)
    assert "<script>" not in pair.user
    assert "hello world" in pair.user
