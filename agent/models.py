"""Model registry — NFR-EXT-01: adding a new model = one entry in MODELS dict."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ModelType = Literal["frontier", "oss"]


@dataclass
class ModelConfig:
    """Configuration for a single LLM."""

    model_id: str
    """LangChain / HuggingFace model identifier."""
    model_label: str
    """Human-readable display name shown in the UI badge."""
    model_type: ModelType
    """'frontier' (blue badge) or 'oss' (coral badge)."""
    hf_repo: str | None = None
    """HuggingFace repo ID — required when model_type == 'oss'."""
    extra_kwargs: dict = field(default_factory=dict)
    """Extra kwargs forwarded to the LangChain LLM constructor."""


# ── Registry ──────────────────────────────────────────────────────────────────
# NFR-EXT-01: To add a new model, append one entry here. No other file changes.

MODELS: dict[str, ModelConfig] = {
    "claude-sonnet": ModelConfig(
        model_id="claude-sonnet-4-20250514",
        model_label="Claude Sonnet",
        model_type="frontier",
    ),
    "qwen-0.5b": ModelConfig(
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        model_label="Qwen 2.5 0.5B",
        model_type="oss",
        hf_repo="Qwen/Qwen2.5-0.5B-Instruct",
    ),
}

DEFAULT_MODEL_KEY = "claude-sonnet"


def get_model(key: str) -> ModelConfig:
    """Return ModelConfig for *key*, raising ValueError on unknown keys."""
    if key not in MODELS:
        raise ValueError(f"Unknown model key: {key!r}. Available: {list(MODELS)}")
    return MODELS[key]


def list_models() -> list[tuple[str, ModelConfig]]:
    """Return all (key, config) pairs for the UI dropdown."""
    return list(MODELS.items())


def build_llm(key: str):
    """
    Instantiate and return the LangChain LLM for *key*.

    - Frontier (Claude): ChatAnthropic using ANTHROPIC_API_KEY from env.
    - OSS (Qwen): ChatHuggingFace via HuggingFaceEndpoint using HUGGINGFACE_TOKEN.

    TODO (Phase 1): implement full LLM construction.
    """
    config = get_model(key)
    if config.model_type == "frontier":
        # TODO: from langchain_anthropic import ChatAnthropic
        # return ChatAnthropic(model=config.model_id, **config.extra_kwargs)
        raise NotImplementedError("Phase 1 — build_llm frontier")
    else:
        # TODO: from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        # endpoint = HuggingFaceEndpoint(repo_id=config.hf_repo, ...)
        # return ChatHuggingFace(llm=endpoint, **config.extra_kwargs)
        raise NotImplementedError("Phase 1 — build_llm oss")
