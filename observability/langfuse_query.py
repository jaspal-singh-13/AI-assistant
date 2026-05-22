"""Langfuse integration — callback handler injection and optional query helpers.

FR-OBS-05: LangfuseCallbackHandler passed into every agent.stream() call.
Every agent step, tool call, and token count appears in Langfuse dashboard automatically.
NFR-REL-01: App continues working if Langfuse is unreachable (handler silently drops events).
"""

from __future__ import annotations

import os
from typing import Any


def get_langfuse_handler():
    """
    Return a LangfuseCallbackHandler configured from environment variables.

    Returns None gracefully if langfuse is not installed or keys are missing.

    Usage:
        handler = get_langfuse_handler()
        config = {"callbacks": [handler]} if handler else {}
        graph.stream(input, config, stream_mode=["updates", "messages"])

    TODO (Phase 3): implement.
    """
    try:
        from langfuse.callback import CallbackHandler  # type: ignore

        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
        base_url = os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

        if not public_key or not secret_key:
            return None

        return CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=base_url,
        )
    except ImportError:
        return None
    except Exception:
        return None


def build_run_config(thread_id: str, model_label: str) -> dict[str, Any]:
    """
    Build the LangGraph run config dict with Langfuse + LangSmith callbacks.

    Pass the returned dict as the *config* argument to graph.stream().

    TODO (Phase 3): implement.
    """
    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    return {
        "callbacks": callbacks,
        "run_name": f"{model_label} | thread:{thread_id}",
        "tags": [model_label, thread_id],
    }
