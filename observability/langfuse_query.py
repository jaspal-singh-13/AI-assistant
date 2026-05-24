"""Langfuse integration — callback handler injection and optional query helpers.

FR-OBS-05: LangfuseCallbackHandler passed into every agent.stream() call.
Every agent step, tool call, and token count appears in Langfuse dashboard automatically.
NFR-REL-01: App continues working if Langfuse is unreachable (handler silently drops events).

Langfuse v4 API:
  - CallbackHandler moved from langfuse.callback → langfuse.langchain
  - Credentials (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL) are
    read from environment variables automatically — no constructor args needed
  - A Langfuse() client must be initialised once before creating the handler
"""

from __future__ import annotations

import os
from typing import Any


def get_langfuse_handler():
    """
    Return a LangchainCallbackHandler configured from environment variables.

    Returns None gracefully if langfuse is not installed or keys are missing.

    Usage:
        handler = get_langfuse_handler()
        config = {"callbacks": [handler]} if handler else {}
        graph.stream(input, config, stream_mode=["updates", "messages"])
    """
    try:
        from langfuse import Langfuse  # type: ignore
        from langfuse.langchain import CallbackHandler  # type: ignore

        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

        if not public_key or not secret_key:
            return None

        Langfuse()
        return CallbackHandler()
    except ImportError:
        return None
    except Exception:
        return None


def build_run_config(thread_id: str, model_label: str, model_id: str = "") -> dict[str, Any]:
    """
    Build the LangGraph run config dict with Langfuse callbacks and LangSmith metadata.

    Pass the returned dict as the *config* argument to graph.stream().
    """
    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    return {
        "callbacks": callbacks,
        "run_name": f"{model_label} | thread:{thread_id}",
        "tags": [model_label, thread_id],
        "metadata": {
            "model_label": model_label,
            "model_id": model_id,
            "thread_id": thread_id,
        },
    }
