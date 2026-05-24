"""Output guardrail pipeline.

Two stages run on the agent's final response:
  Stage 1: Heuristic validators (ToxicLanguage, RestrictToTopic)
  Stage 2: LlamaGuard 3 re-check on output

FR-GRD-03, FR-GRD-04.
Note: guardrails-ai is not installable (broken dep chain on PyPI), so
Stage 1 uses the project's own heuristic validators instead.
"""

from __future__ import annotations

import os

from guardrails.llamaguard import GuardResult
from observability.logger import get_logger, log_duration

logger = get_logger(__name__)

CANNED_OUTPUT_REFUSAL = (
    "I'm sorry, I can't provide that response. "
    "Please ask me something else and I'll do my best to help."
)


def run_output_pipeline(response_text: str) -> GuardResult:
    """
    Run the full output guardrail pipeline on the agent's *response_text*.

    Returns GuardResult. If blocked=True, replace response with CANNED_OUTPUT_REFUSAL.
    result.stages contains per-stage breakdown for UI display.
    """
    import time
    logger.info("output_pipeline | start | text_len=%d", len(response_text))
    stages: list[dict] = []

    # Stage 1 — heuristic validators
    with log_duration(logger, "output_pipeline.validators"):
        t0 = time.perf_counter()
        guard_result = _check_validators(response_text)
        val_latency = (time.perf_counter() - t0) * 1000
    stages.append({
        "name": "Heuristic validators",
        "passed": not guard_result.blocked,
        "latency_ms": val_latency,
        "detail": guard_result.reason if guard_result.blocked else None,
    })
    if guard_result.blocked:
        logger.warning("output_pipeline | BLOCKED | stage=validators reason=%s", guard_result.reason)
        guard_result.stages = stages
        return guard_result

    # Stage 2 — LlamaGuard 3 re-check on output
    from guardrails.llamaguard import classify
    with log_duration(logger, "output_pipeline.llamaguard"):
        lg_result = classify(response_text, role="assistant")
    _SKIP_REASONS = {"llamaguard_skipped_no_token", "llamaguard_error"}
    lg_skipped = lg_result.reason in _SKIP_REASONS
    stages.append({
        "name": "LlamaGuard 3 re-check",
        "passed": not lg_result.blocked,
        "skipped": lg_skipped,
        "latency_ms": lg_result.latency_ms,
        "detail": (
            "no HF token — skipped" if lg_result.reason == "llamaguard_skipped_no_token"
            else "API error — skipped" if lg_result.reason == "llamaguard_error"
            else lg_result.category if lg_result.blocked
            else None
        ),
    })
    if lg_result.blocked:
        logger.warning("output_pipeline | BLOCKED | stage=llamaguard category=%s", lg_result.category)
        lg_result.stages = stages
        return lg_result

    # Stage 3 — NeMo Guardrails (declarative rails, optional Modal service)
    import time as _time
    from guardrails import nemo_client
    with log_duration(logger, "output_pipeline.nemo"):
        t0 = _time.perf_counter()
        nemo_blocked, nemo_rail = nemo_client.check_output(response_text)
        nemo_latency = (_time.perf_counter() - t0) * 1000
    nemo_skipped = not bool(os.environ.get("NEMO_SERVE_URL"))
    stages.append({
        "name": "NeMo Guardrails",
        "passed": not nemo_blocked,
        "skipped": nemo_skipped,
        "latency_ms": nemo_latency,
        "detail": (
            "NEMO_SERVE_URL not set — skipped" if nemo_skipped
            else nemo_rail if nemo_blocked
            else None
        ),
    })
    if nemo_blocked:
        logger.warning("output_pipeline | BLOCKED | stage=nemo rail=%s", nemo_rail)
        result = GuardResult(blocked=True, reason=f"nemo:{nemo_rail}", latency_ms=nemo_latency)
        result.stages = stages
        return result

    total_latency = sum(s["latency_ms"] for s in stages)
    logger.info("output_pipeline | PASSED")
    return GuardResult(blocked=False, latency_ms=total_latency, stages=stages)


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
