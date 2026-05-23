"""LlamaGuard 3 wrapper — classify text across 13 harm categories.

FR-GRD-02: S1–S13 category classification via HF Inference API.
Model: meta-llama/LlamaGuard-3-8B
Response format: "safe" | "unsafe\nS{N}"
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


@dataclass
class GuardResult:
    """Result from any guardrail stage. FR §6.4."""

    blocked: bool
    reason: str | None = None
    """e.g. 'prompt_injection', 'S10_hate', 'output_toxic'"""
    category: str | None = None
    """Human-readable category name if blocked by LlamaGuard."""
    pii_entities: list | None = None
    """Presidio entities detected (even if not blocked)."""
    latency_ms: float = 0.0
    stages: list = field(default_factory=list)
    """Per-stage breakdown: [{"name": str, "passed": bool, "latency_ms": float, "detail": str|None}]"""


# Maps LlamaGuard category codes → readable names
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

_LLAMAGUARD_PROMPT_TEMPLATE = """[INST] Task: Check if there is unsafe content in the '{role}' messages in the below conversation.

<BEGIN CONVERSATION>
{role}: {text}
<END CONVERSATION>

Provide your safety assessment for the content in the above conversation:
- First line must read 'safe' or 'unsafe'.
- If unsafe, a second line must include a comma-separated list of violated categories. [/INST]"""


def classify(text: str, role: str = "user") -> GuardResult:
    """
    Call LlamaGuard 3 via HF Inference API and return a GuardResult.

    role: "user" for input check, "assistant" for output check.
    Returns GuardResult(blocked=False) gracefully if HF token is missing.
    """
    import requests

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN", "")
    if not hf_token:
        return GuardResult(blocked=False, reason="llamaguard_skipped_no_token")

    api_url = "https://router.huggingface.co/hf-inference/models/meta-llama/LlamaGuard-3-8B"
    headers = {"Authorization": f"Bearer {hf_token}"}
    prompt = _LLAMAGUARD_PROMPT_TEMPLATE.format(role=role, text=text)

    t0 = time.perf_counter()
    try:
        resp = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=15)
        resp.raise_for_status()
        result_text = resp.json()[0]["generated_text"].strip().lower()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("LlamaGuard API error: %s", exc)
        return GuardResult(blocked=False, reason="llamaguard_error")
    latency_ms = (time.perf_counter() - t0) * 1000

    if result_text.startswith("unsafe"):
        parts = result_text.split("\n")
        raw_code = parts[1].strip().upper() if len(parts) > 1 else "UNKNOWN"
        # The response may return comma-separated codes; take the first
        code = raw_code.split(",")[0].strip()
        category = CATEGORY_MAP.get(code, code)
        reason = f"{code}_{'_'.join(category.split())}"
        return GuardResult(blocked=True, reason=reason, category=category, latency_ms=latency_ms)

    return GuardResult(blocked=False, latency_ms=latency_ms)
