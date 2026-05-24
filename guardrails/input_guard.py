"""Input guardrail pipeline.

Three stages run in sequence. First block wins (later stages not called).
Order chosen for cost efficiency — cheapest check first.

Stage 1: Heuristic injection detection (~1ms, regex + keyword patterns)
          Note: rebuff (0.1.1) requires langchain<0.2 and is incompatible with
          this project's langchain>=0.3 dependency, so a local heuristic is used.
Stage 2: LlamaGuard 3 — 13 harm categories (~300ms, HF Inference API)
Stage 3: Presidio — PII detection (local, ~20ms, NEVER blocks — redacts only)

FR-GRD-01, FR-GRD-02, FR-GRD-06, NFR-PERF-01 (total < 400ms).
"""

from __future__ import annotations

import hashlib
import os
import re
import time

import requests as _requests

from guardrails.llamaguard import GuardResult
from observability.logger import get_logger, log_duration

logger = get_logger(__name__)

# Patterns that signal prompt injection attempts (DAN, jailbreaks, nested injections)
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above)\s+instructions?|"
    r"disregard\s+(all\s+)?instructions?|"
    r"you\s+are\s+now\s+(dan|an?\s+unrestricted|free\s+from)|"
    r"do\s+anything\s+now|jailbreak|"
    r"pretend\s+(you\s+have\s+no\s+restrictions?|to\s+be\s+evil)|"
    r"act\s+as\s+if\s+you\s+have\s+no\s+(guidelines?|restrictions?|rules?)|"
    r"system\s*:\s*(you\s+are|ignore|forget)|"
    r"<\|im_start\|>|<\|system\|>|<\|endoftext\|>)",
    re.IGNORECASE,
)

# Base64-encoded "ignore previous" and common b64-wrapped jailbreak markers
_B64_INJECTION = re.compile(
    r"\b[A-Za-z0-9+/]{20,}={0,2}\b"  # any substantial base64 blob is suspicious
)


def run_input_pipeline(text: str) -> GuardResult:
    """
    Run the full input guardrail pipeline on user *text*.

    Returns a GuardResult. If blocked=True, the message must NOT be forwarded
    to the agent — return a canned refusal string to the user instead.

    PII entities are always returned in result.pii_entities (may be empty list).
    result.stages contains per-stage breakdown for UI display.
    """
    logger.info("input_pipeline | start | text_len=%d", len(text))
    stages: list[dict] = []

    # Stage 1 — Heuristic injection detection
    with log_duration(logger, "input_pipeline.injection_check"):
        rebuff_result = _check_injection(text)
    stages.append({
        "name": "Injection check",
        "passed": not rebuff_result.blocked,
        "latency_ms": rebuff_result.latency_ms,
        "detail": rebuff_result.reason if rebuff_result.blocked else None,
    })
    if rebuff_result.blocked:
        logger.warning("input_pipeline | BLOCKED | stage=injection reason=%s", rebuff_result.reason)
        rebuff_result.stages = stages
        return rebuff_result

    # Stage 2 — LlamaGuard 3
    from guardrails.llamaguard import classify
    with log_duration(logger, "input_pipeline.llamaguard"):
        lg_result = classify(text, role="user")
    _SKIP_REASONS = {"llamaguard_skipped_no_token", "llamaguard_error"}
    lg_skipped = lg_result.reason in _SKIP_REASONS
    stages.append({
        "name": "LlamaGuard 3 (13 categories)",
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
        logger.warning("input_pipeline | BLOCKED | stage=llamaguard category=%s", lg_result.category)
        lg_result.stages = stages
        return lg_result

    # Stage 3 — Presidio (redact only, never blocks)
    with log_duration(logger, "input_pipeline.presidio"):
        t0 = time.perf_counter()
        pii_entities = _detect_pii(text)
        pii_latency = (time.perf_counter() - t0) * 1000
    pii_count = len(pii_entities)
    stages.append({
        "name": "Presidio PII",
        "passed": True,
        "latency_ms": pii_latency,
        "detail": f"{pii_count} {'entity' if pii_count == 1 else 'entities'} detected (redacted from logs)" if pii_count else None,
    })
    # Stage 4 — NeMo Guardrails (declarative rails, optional Modal service)
    from guardrails import nemo_client
    with log_duration(logger, "input_pipeline.nemo"):
        t0 = time.perf_counter()
        nemo_blocked, nemo_rail = nemo_client.check_input(text)
        nemo_latency = (time.perf_counter() - t0) * 1000
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
        logger.warning("input_pipeline | BLOCKED | stage=nemo rail=%s", nemo_rail)
        result = GuardResult(blocked=True, reason=f"nemo:{nemo_rail}", latency_ms=nemo_latency)
        result.stages = stages
        return result

    total_latency = sum(s["latency_ms"] for s in stages)
    logger.info("input_pipeline | PASSED | pii_detected=%s", pii_count > 0)
    return GuardResult(blocked=False, pii_entities=pii_entities, latency_ms=total_latency, stages=stages)


def _check_injection(text: str) -> GuardResult:
    """
    Detect prompt injection via regex heuristics.

    Catches: "ignore previous instructions", DAN patterns, nested injections,
    role-override attempts, and special tokens.
    Latency target: ~1ms (pure regex, no model call).
    """
    t0 = time.perf_counter()
    if _INJECTION_PATTERNS.search(text):
        latency_ms = (time.perf_counter() - t0) * 1000
        return GuardResult(blocked=True, reason="prompt_injection", latency_ms=latency_ms)
    latency_ms = (time.perf_counter() - t0) * 1000
    return GuardResult(blocked=False, latency_ms=latency_ms)


_PII_PATTERNS: dict[str, re.Pattern] = {
    "EMAIL":       re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "PHONE":       re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "SSN":         re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "IP_ADDRESS":  re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "PASSPORT":    re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
}


def _detect_pii(text: str) -> list:
    """
    Detect PII entities. Tries the Modal Presidio service first (full NER —
    PERSON, LOCATION, ORGANIZATION, etc.), falls back to local regex patterns
    if PRESIDIO_SERVE_URL is unset or the call fails.

    Returns list of entity dicts. Does NOT block the message.
    """
    url = os.environ.get("PRESIDIO_SERVE_URL")
    if url:
        try:
            resp = _requests.post(
                f"{url.rstrip('/')}/detect",
                json={"text": text},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json().get("entities", [])
        except Exception:
            pass  # fall through to regex

    # Regex fallback — covers structured PII with no external deps
    entities = []
    for entity_type, pattern in _PII_PATTERNS.items():
        for m in pattern.finditer(text):
            entities.append({
                "entity_type": entity_type,
                "start": m.start(),
                "end": m.end(),
                "score": 1.0,
            })
    return entities


def message_hash(text: str) -> str:
    """Return SHA-256 hex digest of *text* for safe logging of blocked messages (FR-GRD-05)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CANNED_REFUSAL = (
    "I'm not able to respond to that request. "
    "If you have a genuine question, please rephrase it and I'll be happy to help."
)
