"""Model registry — loaded entirely from .env MODELS_<key> entries.

To add a model: add one line to .env, nothing else.
  MODELS_<key>=<model_id>|<label>|<type>   (type = frontier or oss)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

ModelType = Literal["frontier", "oss"]


@dataclass
class ModelConfig:
    model_id: str
    model_label: str
    model_type: ModelType
    hf_repo: str | None = None
    extra_kwargs: dict = field(default_factory=dict)


def _load_models() -> dict[str, ModelConfig]:
    from dotenv import load_dotenv
    load_dotenv()
    models: dict[str, ModelConfig] = {}
    for env_key, value in os.environ.items():
        if not env_key.startswith("MODELS_"):
            continue
        key = env_key[len("MODELS_"):].lower()
        parts = value.split("|")
        if len(parts) != 3:
            raise ValueError(f"{env_key} must be 'model_id|label|type', got {value!r}")
        model_id, label, model_type = (p.strip() for p in parts)
        if model_type not in ("frontier", "oss"):
            raise ValueError(f"{env_key}: type must be 'frontier' or 'oss', got {model_type!r}")
        models[key] = ModelConfig(
            model_id=model_id,
            model_label=label,
            model_type=model_type,  # type: ignore[arg-type]
            hf_repo=model_id if model_type == "oss" else None,
        )
    return models


MODELS: dict[str, ModelConfig] = _load_models()
DEFAULT_MODEL_KEY = os.environ.get("DEFAULT_MODEL_KEY", next(iter(MODELS)) if MODELS else "")


def get_model(key: str) -> ModelConfig:
    if key not in MODELS:
        raise ValueError(f"Unknown model key: {key!r}. Available: {list(MODELS)}")
    return MODELS[key]


def list_models() -> list[tuple[str, ModelConfig]]:
    return list(MODELS.items())


def build_llm(key: str):
    config = get_model(key)
    if config.model_type == "frontier":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=config.model_id, **config.extra_kwargs)
    else:
        from agent.local_llm import LocalTransformersChatModel
        return LocalTransformersChatModel(
            model_name=config.hf_repo,
            **config.extra_kwargs,
        )
