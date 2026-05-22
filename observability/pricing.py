"""LiteLLM pricing — fetch, cache (24hr), and compute call costs.

FR-OBS-02: Fetched from GitHub raw at startup, cached 24hr, fallback to config/pricing_fallback.json.
FR-OBS-03: Frontier cost = input_tokens × input_price + output_tokens × output_price.
FR-OBS-04: OSS cost = equivalent compute (never NA).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LITELLM_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
FALLBACK_PATH = Path(__file__).parent.parent / "config" / "pricing_fallback.json"
CACHE_TTL_SECONDS = 86_400  # 24 hours

# OSS equivalent compute rates
HF_SPACES_CPU_HOURLY_USD = 0.03
MODAL_GPU_PER_SECOND_USD = 0.000583


def fetch_pricing(force: bool = False) -> tuple[dict, str, str]:
    """
    Return (pricing_dict, source_label, fetched_at_iso).

    Tries the LiteLLM GitHub URL first; falls back to local JSON on any error.
    Result should be cached in st.session_state["pricing"] for 24hr (FR-OBS-02).

    TODO (Phase 3): implement with requests + cache logic.
    """
    # import requests
    # try:
    #     resp = requests.get(LITELLM_PRICING_URL, timeout=10)
    #     resp.raise_for_status()
    #     data = resp.json()
    #     fetched_at = datetime.now(timezone.utc).isoformat()
    #     return data, "litellm_json", fetched_at
    # except Exception:
    #     pass
    # return _load_fallback()
    raise NotImplementedError("Phase 3 — fetch_pricing")


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
    For 'oss': returns equivalent compute cost (never NA — FR-OBS-04).

    TODO (Phase 3): implement lookup.
    """
    if model_type == "oss":
        equiv = (latency_ms / 3_600_000) * HF_SPACES_CPU_HOURLY_USD
        return 0.0, equiv

    # TODO: look up model_id in pricing dict, extract input_cost_per_token + output_cost_per_token
    # entry = pricing.get(model_id, {})
    # input_price = entry.get("input_cost_per_token", 0.0)
    # output_price = entry.get("output_cost_per_token", 0.0)
    # return input_tokens * input_price, output_tokens * output_price
    raise NotImplementedError("Phase 3 — compute_cost frontier")


def hours_since_fetch(fetched_at_iso: str) -> float:
    """Return hours elapsed since *fetched_at_iso* (for the UI label FR-OBS-02)."""
    fetched = datetime.fromisoformat(fetched_at_iso)
    now = datetime.now(timezone.utc)
    delta = now - fetched.replace(tzinfo=timezone.utc) if fetched.tzinfo is None else now - fetched
    return delta.total_seconds() / 3600
