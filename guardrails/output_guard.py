"""Output guardrail pipeline.

Two stages run on the agent's final response:
  Stage 1: Heuristic validators (ToxicLanguage, RestrictToTopic)
  Stage 2: LlamaGuard 3 re-check on output

FR-GRD-03, FR-GRD-04.
Note: guardrails-ai is not installable (broken dep chain on PyPI), so
Stage 1 uses the project's own heuristic validators instead.
"""

from __future__ import annotations

from guardrails.llamaguard import GuardResult

CANNED_OUTPUT_REFUSAL = (
    "I'm sorry, I can't provide that response. "
    "Please ask me something else and I'll do my best to help."
)


def run_output_pipeline(response_text: str) -> GuardResult:
    """
    Run the full output guardrail pipeline on the agent's *response_text*.

    Returns GuardResult. If blocked=True, replace response with CANNED_OUTPUT_REFUSAL.
    """
    # Stage 1 — heuristic validators
    guard_result = _check_validators(response_text)
    if guard_result.blocked:
        return guard_result

    # Stage 2 — LlamaGuard 3 re-check on output
    from guardrails.llamaguard import classify
    lg_result = classify(response_text, role="assistant")
    if lg_result.blocked:
        return lg_result

    return GuardResult(blocked=False)


def _check_validators(response_text: str) -> GuardResult:
    """Run ToxicLanguage and RestrictToTopic validators on output."""
    from guardrails.validators import ToxicLanguage, RestrictToTopic

    passed, reason = ToxicLanguage().validate(response_text)
    if not passed:
        return GuardResult(blocked=True, reason=f"output_{reason}")

    passed, reason = RestrictToTopic().validate(response_text)
    if not passed:
        return GuardResult(blocked=True, reason=f"output_{reason}")

    return GuardResult(blocked=False)
