"""Stream handler — wraps graph.stream() to feed tokens and steps to the UI.

Uses stream_mode=['updates','messages'] so tokens display live via st.write_stream()
and the state_snapshot is collected in the same pass.

FR-AGT-02, FR-AGT-03.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph


def handle_send(user_message: str) -> None:
    """
    Stage 1: append user message, auto-rename thread if this is the first message,
    set pending flag, rerun so the user message appears immediately.
    """
    thread = st.session_state.get("active_thread")
    if thread is None:
        st.error("No active thread. Please create a thread first.")
        return

    from memory.manager import append_message, list_threads, save_thread

    now = datetime.now(timezone.utc).isoformat()
    user_dict = {"role": "user", "content": user_message, "timestamp": now, "metadata": {}}

    # Auto-rename: update title from first user message if still default
    if thread.get("title") in ("New thread", "", None):
        thread["title"] = " ".join(user_message.split()[:6])
        save_thread(thread)

    append_message(thread, user_dict)
    st.session_state["threads"] = list_threads()
    st.session_state["pending_response"] = True
    st.rerun()


def run_pending_response() -> None:
    """
    Stage 2: called on every render when pending_response is True.
    Streams tokens live into the assistant bubble, collects snapshot, saves, reruns.
    """
    if not st.session_state.get("pending_response"):
        return

    thread = st.session_state.get("active_thread")
    model_key = st.session_state.get("model_key", "claude-haiku")
    graph = st.session_state.get("agent_graph")

    if graph is None:
        st.error("Agent failed to initialise — check your API keys in .env and restart.")
        st.session_state["pending_response"] = False
        return

    from agent.factory import stream_and_collect
    from agent.models import get_model
    from memory.manager import append_message, get_llm_context, list_threads
    from observability.logger import log_call

    config = get_model(model_key)
    lc_messages = get_llm_context(thread)
    msg_dicts = _lc_to_dicts(lc_messages)

    t_start = time.time()
    token_gen, snapshot = stream_and_collect(graph, msg_dicts)

    with st.chat_message("assistant"):
        response = st.write_stream(token_gen)

    latency_ms = (time.time() - t_start) * 1000

    # Fallback: if write_stream returned nothing (e.g. tool-only response), read snapshot
    if not response:
        response = next(
            (s["content"] for s in reversed(snapshot) if s.get("type") == "response"), ""
        )

    log_call(
        model_id=config.model_id,
        model_type=config.model_type,
        input_tokens=0,
        output_tokens=0,
        input_cost_usd=0.0,
        output_cost_usd=0.0,
        latency_ms=latency_ms,
        pricing_source="unavailable",
        pricing_fetched_at="",
        summary_used=bool(thread.get("summaries")),
        tool_calls=[s["tool"] for s in snapshot if s.get("type") == "tool_call"],
    )

    assistant_dict = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state_snapshot": snapshot,
        "metadata": {
            "model_label": config.model_label,
            "model_type": config.model_type,
            "latency_ms": round(latency_ms, 2),
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        },
    }
    append_message(thread, assistant_dict)
    st.session_state["threads"] = list_threads()
    st.session_state["pending_response"] = False
    st.rerun()


def _lc_to_dicts(messages: list) -> list[dict]:
    """Convert LangChain message objects to plain dicts for run_agent / stream_and_collect."""
    result = []
    for m in messages:
        cls = m.__class__.__name__
        if cls == "SystemMessage":
            result.append({"role": "system", "content": m.content})
        elif cls == "HumanMessage":
            result.append({"role": "user", "content": m.content})
        else:
            result.append({"role": "assistant", "content": m.content})
    return result
