"""Output guardrail pipeline.

Two stages run on the agent's final response:
  Stage 1: Guardrails AI validators (ToxicLanguage, DetectPII, RestrictToTopic)
  Stage 2: LlamaGuard 3 re-check on output
  + NeMo declarative rails applied at conversation level (separate config).

FR-GRD-03, FR-GRD-04.
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

    TODO (Phase 3): implement both stages.
    """
    # Stage 1 — Guardrails AI validators
    # guard_result = _check_guardrails_ai(response_text)
    # if guard_result.blocked:
    #     return guard_result

    # Stage 2 — LlamaGuard 3 re-check on output
    # from guardrails.llamaguard import classify
    # lg_result = classify(response_text, role="assistant")
    # if lg_result.blocked:
    #     return lg_result

    # return GuardResult(blocked=False)
    raise NotImplementedError("Phase 3 — run_output_pipeline")


def _check_guardrails_ai(response_text: str) -> GuardResult:
    """
    Run Guardrails AI ToxicLanguage + DetectPII + RestrictToTopic validators.

    TODO (Phase 3): implement using guardrails-ai Guard pipeline.
    """
    # from guardrails import Guard
    # from guardrails.validators import ToxicLanguage, DetectPII, RestrictToTopic
    # guard = Guard().use_many(ToxicLanguage(), DetectPII(), RestrictToTopic())
    # result = guard.validate(response_text)
    # if not result.validation_passed:
    #     return GuardResult(blocked=True, reason="output_guardrails_ai")
    # return GuardResult(blocked=False)
    raise NotImplementedError("Phase 3 — _check_guardrails_ai")
