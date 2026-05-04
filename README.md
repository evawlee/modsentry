# modsentry

Multi-tenant LLM-backed content moderation service.

`modsentry` classifies text submissions against configurable moderation policies using a
pluggable LLM backend.  Results are cached per-content to reduce latency on repeated
submissions.

## Installation

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from modsentry import build_moderation_platform, ModerationRequest

platform = build_moderation_platform()

verdict = platform.evaluate(
    ModerationRequest(
        content="The text you want to classify.",
        context_hint="optional context about the submission source",
    ),
    policy_id="strict",
)

print(verdict.label, verdict.confidence, verdict.reason)
```

## Policies

Two policies ship by default:

| `policy_id` | Name | Severity band |
|-------------|------|---------------|
| `"lenient"` | Community Standard | low |
| `"strict"` | Brand Safety | high |

Custom policies can be registered at construction time:

```python
from modsentry.models.policy import Policy

my_policy = Policy(
    id="kids",
    name="Children's Platform",
    severity_band="high",
    hard_block_terms=frozenset({"adult content", "violence"}),
)

platform = build_moderation_platform(extra_policies={"kids": my_policy})
```

## Running tests

```bash
python -m pytest tests/ -v
```

## Architecture

```
ModerationRequest
    │
    ▼
ModerationService.evaluate()
    │
    ├── VerdictCache.get()          ← check cache first
    │
    ├── [cache miss] PromptEngine.build()   ← construct (system, user) pair
    │       └── InputSanitizer.clean()      ← sanitise content
    │
    ├── LLMGateway.complete()       ← call LLM
    │
    ├── parse_llm_response()        ← parse JSON verdict
    │
    └── VerdictCache.put()          ← store result
```
