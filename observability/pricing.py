"""LiteLLM pricing — fetch, cache (24hr), and compute call costs.

FR-OBS-02: Fetched from GitHub raw at startup, cached 24hr, fallback to config/pricing_fallback.json.
FR-OBS-03: Frontier cost = input_tokens × input_price + output_tokens × output_price.
FR-OBS-04: OSS cost = equivalent compute (never NA).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guardrails.llamaguard import GuardResult

LITELLM_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
FALLBACK_PATH = Path(__file__).parent.parent / "config" / "pricing_fallback.json"
CACHE_TTL_SECONDS = 86_400  # 24 hours

# Modal compute rates (confirmed from modal.com/pricing, May 2026)
MODAL_A10G_PER_SECOND_USD = 0.000306        # A10G GPU — Qwen inference server
MODAL_CPU_PER_SECOND_USD = 0.0000131 * 0.125  # CPU @ default 0.125 cores — NeMo, Presidio

# Stage names that map to Modal CPU services
_MODAL_CPU_STAGES = {"NeMo Guardrails", "Presidio PII"}


def fetch_pricing(force: bool = False) -> tuple[dict, str, str]:
    """
    Return (pricing_dict, source_label, fetched_at_iso).

    Tries the LiteLLM GitHub URL first; falls back to local JSON on any error.
    Result should be cached in st.session_state["pricing"] for 24hr (FR-OBS-02).
    """
    import requests

    try:
        resp = requests.get(LITELLM_PRICING_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        fetched_at = datetime.now(timezone.utc).isoformat()
        return data, "litellm_json", fetched_at
    except Exception:
        pass
    return _load_fallback()


def _load_fallback() -> tuple[dict, str, str]:
    data = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
    fetched_at = datetime.now(timezone.utc).isoformat()
    return data, "fallback", fetched_at


def compute_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    pricing: dict,
    model_type: str = "frontier",
    latency_ms: float = 0.0,
) -> tuple[float, float]:
    """
    Return (input_cost_usd, output_cost_usd).

    For 'frontier': uses LiteLLM pricing JSON.
    For 'oss': Modal A10G wall-clock cost (never NA — FR-OBS-04).
    """
    if model_type == "oss":
        equiv = (latency_ms / 1_000) * MODAL_A10G_PER_SECOND_USD
        return 0.0, equiv

    entry = pricing.get(model_id, {})
    input_price = entry.get("input_cost_per_token", 0.0)
    output_price = entry.get("output_cost_per_token", 0.0)
    return input_tokens * input_price, output_tokens * output_price


def compute_guardrail_cost(
    input_guard: GuardResult,
    output_guard: GuardResult,
    pricing: dict,
) -> float:
    """
    Return total USD cost for all guardrail services in one conversation turn.

    Cost components:
    - LlamaGuard calls: Claude Haiku token-based pricing (tokens on GuardResult).
    - NeMo Guardrails:  Modal CPU wall-clock cost (from stage latency_ms).
    - Presidio PII:     Modal CPU wall-clock cost (from stage latency_ms).
    - Injection check:  local regex, free.

    Note: NeMo makes an internal Anthropic call we cannot observe; the NeMo
    figure here covers only the Modal CPU container cost (a known lower bound).
    """
    haiku = pricing.get("claude-haiku-4-5-20251001", {})
    in_price = haiku.get("input_cost_per_token", 0.0)
    out_price = haiku.get("output_cost_per_token", 0.0)

    total = 0.0
    for guard in (input_guard, output_guard):
        total += guard.input_tokens * in_price + guard.output_tokens * out_price
        for stage in guard.stages:
            if stage["name"] in _MODAL_CPU_STAGES:
                total += (stage["latency_ms"] / 1_000) * MODAL_CPU_PER_SECOND_USD
    return total


def hours_since_fetch(fetched_at_iso: str) -> float:
    """Return hours elapsed since *fetched_at_iso* (for the UI label FR-OBS-02)."""
    fetched = datetime.fromisoformat(fetched_at_iso)
    now = datetime.now(timezone.utc)
    delta = now - fetched.replace(tzinfo=timezone.utc) if fetched.tzinfo is None else now - fetched
    return delta.total_seconds() / 3600
