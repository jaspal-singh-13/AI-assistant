"""Content safety classifier using Claude Haiku.

FR-GRD-02: S1–S13 category classification via Anthropic API.
Model: claude-haiku-4-5-20251001
Response format: "safe" | "unsafe\nS{N}"
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from observability.logger import get_logger

logger = get_logger(__name__)

_GUARD_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """You are a content safety classifier. Classify the given text across these harm categories:

S1: Violent Crimes
S2: Non-Violent Crimes
S3: Sex Crimes
S4: Child Exploitation
S5: Defamation
S6: Specialised Advice (medical/legal/financial without disclaimer)
S7: Privacy (personal data exposure)
S8: Intellectual Property
S9: Weapons
S10: Hate
S11: Self-Harm
S12: Sexual Content
S13: Elections (voter suppression, misinformation)

Reply with ONLY one of:
- safe
- unsafe
  S{N}

No explanation. No other text."""


@dataclass
class GuardResult:
    """Result from any guardrail stage. FR §6.4."""

    blocked: bool
    reason: str | None = None
    """e.g. 'prompt_injection', 'S10_hate', 'output_toxic'"""
    category: str | None = None
    """Human-readable category name if blocked."""
    pii_entities: list | None = None
    """Presidio entities detected (even if not blocked)."""
    latency_ms: float = 0.0
    stages: list = field(default_factory=list)
    """Per-stage breakdown: [{"name": str, "passed": bool, "latency_ms": float, "detail": str|None}]"""
    input_tokens: int = 0
    """Input tokens consumed by the LlamaGuard (Claude Haiku) classify() call."""
    output_tokens: int = 0
    """Output tokens consumed by the LlamaGuard (Claude Haiku) classify() call."""


# Maps category codes → readable names
CATEGORY_MAP: dict[str, str] = {
    "S1": "Violent Crimes",
    "S2": "Non-Violent Crimes",
    "S3": "Sex Crimes",
    "S4": "Child Exploitation",
    "S5": "Defamation",
    "S6": "Specialised Advice",
    "S7": "Privacy",
    "S8": "Intellectual Property",
    "S9": "Weapons",
    "S10": "Hate",
    "S11": "Self-Harm",
    "S12": "Sexual Content",
    "S13": "Elections",
}


def classify(text: str, role: str = "user") -> GuardResult:
    """
    Classify text safety using Claude Haiku via the Anthropic API.

    role: "user" for input check, "assistant" for output check.
    Returns GuardResult(blocked=False) gracefully if API key is missing or call fails.
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return GuardResult(blocked=False, reason="guard_skipped_no_key")

    client = anthropic.Anthropic(api_key=api_key)
    user_content = f"Classify this {role} message:\n\n{text}"

    t0 = time.perf_counter()
    try:
        msg = client.messages.create(
            model=_GUARD_MODEL,
            max_tokens=20,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        result_text = msg.content[0].text.strip().lower()
    except Exception as exc:
        logger.warning("Safety classifier error: %s", exc)
        return GuardResult(blocked=False, reason="guard_error")
    latency_ms = (time.perf_counter() - t0) * 1000

    in_tok = getattr(msg.usage, "input_tokens", 0)
    out_tok = getattr(msg.usage, "output_tokens", 0)

    if result_text.startswith("unsafe"):
        parts = result_text.split("\n")
        raw_code = parts[1].strip().upper() if len(parts) > 1 else "UNKNOWN"
        code = raw_code.split(",")[0].strip()
        category = CATEGORY_MAP.get(code, code)
        reason = f"{code}_{'_'.join(category.split())}"
        logger.info("classify | UNSAFE | role=%s category=%s latency_ms=%.0f", role, category, latency_ms)
        return GuardResult(
            blocked=True, reason=reason, category=category,
            latency_ms=latency_ms, input_tokens=in_tok, output_tokens=out_tok,
        )

    logger.info("classify | safe | role=%s latency_ms=%.0f", role, latency_ms)
    return GuardResult(blocked=False, latency_ms=latency_ms, input_tokens=in_tok, output_tokens=out_tok)
