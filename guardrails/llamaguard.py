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

    TODO (Phase 3): implement HF Inference API call.
    """
    # import requests
    # HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")
    # API_URL = "https://api-inference.huggingface.co/models/meta-llama/LlamaGuard-3-8B"
    # headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    #
    # prompt = _LLAMAGUARD_PROMPT_TEMPLATE.format(role=role, text=text)
    # t0 = time.perf_counter()
    # resp = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=15)
    # latency_ms = (time.perf_counter() - t0) * 1000
    #
    # result_text = resp.json()[0]["generated_text"].strip().lower()
    # if result_text.startswith("unsafe"):
    #     parts = result_text.split("\n")
    #     code = parts[1].strip().upper() if len(parts) > 1 else "UNKNOWN"
    #     category = CATEGORY_MAP.get(code, code)
    #     return GuardResult(blocked=True, reason=f"{code}_{'_'.join(category.split())}", category=category, latency_ms=latency_ms)
    # return GuardResult(blocked=False, latency_ms=latency_ms)
    raise NotImplementedError("Phase 3 — classify")
