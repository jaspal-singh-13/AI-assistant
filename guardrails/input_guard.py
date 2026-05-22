"""Input guardrail pipeline.

Three stages run in sequence. First block wins (later stages not called).
Order chosen for cost efficiency — cheapest check first.

Stage 1: Rebuff   — prompt injection (~5ms, heuristic, no LLM call)
Stage 2: LlamaGuard 3 — 13 harm categories (~300ms, HF Inference API)
Stage 3: Presidio — PII detection (local, ~20ms, NEVER blocks — redacts only)

FR-GRD-01, FR-GRD-02, FR-GRD-06, NFR-PERF-01 (total < 400ms).
"""

from __future__ import annotations

import hashlib
import time

from guardrails.llamaguard import GuardResult


def run_input_pipeline(text: str) -> GuardResult:
    """
    Run the full input guardrail pipeline on user *text*.

    Returns a GuardResult. If blocked=True, the message must NOT be forwarded
    to the agent — return a canned refusal string to the user instead.

    PII entities are always returned in result.pii_entities (may be empty list).

    TODO (Phase 3): implement all three stages.
    """
    # Stage 1 — Rebuff
    # rebuff_result = _check_rebuff(text)
    # if rebuff_result.blocked:
    #     return rebuff_result

    # Stage 2 — LlamaGuard 3
    # from guardrails.llamaguard import classify
    # lg_result = classify(text, role="user")
    # if lg_result.blocked:
    #     return lg_result

    # Stage 3 — Presidio (redact only, never blocks)
    # pii_entities = _detect_pii(text)
    # return GuardResult(blocked=False, pii_entities=pii_entities)

    raise NotImplementedError("Phase 3 — run_input_pipeline")


def _check_rebuff(text: str) -> GuardResult:
    """
    Detect prompt injection via Rebuff.

    Catches: "ignore previous instructions", nested injections, base64-encoded payloads.
    Latency target: ~5ms (heuristic, no model call).

    TODO (Phase 3): implement using rebuff library.
    """
    # from rebuff import RebuffSdk
    # rb = RebuffSdk(...)
    # result = rb.detect_injection(text)
    # if result.injection_detected:
    #     return GuardResult(blocked=True, reason="prompt_injection", latency_ms=result.run_time_ms)
    # return GuardResult(blocked=False, latency_ms=result.run_time_ms)
    raise NotImplementedError("Phase 3 — _check_rebuff")


def _detect_pii(text: str) -> list:
    """
    Detect PII entities via Presidio (local inference, no API call).

    Returns list of entity dicts. Does NOT block the message.

    TODO (Phase 3): implement using presidio-analyzer.
    """
    # from presidio_analyzer import AnalyzerEngine
    # analyzer = AnalyzerEngine()
    # results = analyzer.analyze(text=text, language="en")
    # return [{"entity_type": r.entity_type, "start": r.start, "end": r.end, "score": r.score} for r in results]
    raise NotImplementedError("Phase 3 — _detect_pii")


def message_hash(text: str) -> str:
    """Return SHA-256 hex digest of *text* for safe logging of blocked messages (FR-GRD-05)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CANNED_REFUSAL = (
    "I'm not able to respond to that request. "
    "If you have a genuine question, please rephrase it and I'll be happy to help."
)
