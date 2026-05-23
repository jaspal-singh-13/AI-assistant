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


_THINKING_HTML = "<span style='color:#888;font-style:italic'>▪ Thinking…</span>"


def run_pending_response() -> None:
    """
    Stage 2: called on every render when pending_response is True.

    Consumes stream_events() and renders:
      - "▪ Thinking…"  while the LLM is computing
      - "🔧 Calling `tool`…"  while a tool is executing
      - streamed text with a blinking cursor once tokens arrive

    The state panel expander (shown after the response is saved) provides
    the full tool call / tool result detail.
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

    from agent.factory import stream_events
    from agent.models import get_model
    from guardrails.input_guard import CANNED_REFUSAL, message_hash, run_input_pipeline
    from guardrails.output_guard import CANNED_OUTPUT_REFUSAL, run_output_pipeline
    from memory.manager import append_message, get_llm_context, list_threads
    from observability.logger import log_call
    from observability.pricing import compute_cost, fetch_pricing

    config = get_model(model_key)
    lc_messages = get_llm_context(thread)
    msg_dicts = _lc_to_dicts(lc_messages)

    # Fetch / reuse pricing (24hr cache in session state)
    pricing_cache = st.session_state.get("pricing")
    if pricing_cache is None:
        pricing_data, pricing_source, pricing_fetched_at = fetch_pricing()
        st.session_state["pricing"] = {
            "data": pricing_data,
            "source": pricing_source,
            "fetched_at": pricing_fetched_at,
        }
    else:
        pricing_data = pricing_cache["data"]
        pricing_source = pricing_cache["source"]
        pricing_fetched_at = pricing_cache["fetched_at"]

    # Stage 0 — input guardrail check
    user_text = thread["messages"][-1]["content"] if thread.get("messages") else ""
    input_guard = run_input_pipeline(user_text)
    if input_guard.blocked:
        log_call(
            model_id=config.model_id,
            model_type=config.model_type,
            input_tokens=0,
            output_tokens=0,
            input_cost_usd=0.0,
            output_cost_usd=0.0,
            latency_ms=input_guard.latency_ms,
            pricing_source=pricing_source,
            pricing_fetched_at=pricing_fetched_at,
            guardrail_blocked=True,
            block_layer="input",
            block_reason=input_guard.reason,
            block_stage="input_pipeline",
            original_message_hash=message_hash(user_text),
        )
        with st.chat_message("assistant"):
            st.warning(CANNED_REFUSAL)
        assistant_dict = {
            "role": "assistant",
            "content": CANNED_REFUSAL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state_snapshot": [],
            "metadata": {
                "model_label": config.model_label,
                "model_type": config.model_type,
                "latency_ms": round(input_guard.latency_ms, 2),
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "input_guard": {
                    "blocked": True,
                    "reason": input_guard.reason,
                    "pii_count": len(input_guard.pii_entities or []),
                    "latency_ms": round(input_guard.latency_ms, 2),
                    "stages": input_guard.stages,
                },
                "output_guard": None,
            },
        }
        append_message(thread, assistant_dict)
        st.session_state["threads"] = list_threads()
        st.session_state["pending_response"] = False
        st.rerun()
        return

    t_start = time.time()
    snapshot: list[dict] = []
    full_response = ""
    tokens_started = False

    with st.chat_message("assistant"):
        status = st.empty()
        response_area = st.empty()

        status.markdown(_THINKING_HTML, unsafe_allow_html=True)

        for event in stream_events(graph, msg_dicts):
            etype = event.get("type")

            if etype == "tool_call":
                snapshot.append(event)
                tool = event.get("tool", "tool")
                status.markdown(
                    f"<span style='color:#888;font-style:italic'>"
                    f"🔧 Calling <code>{tool}</code>…</span>",
                    unsafe_allow_html=True,
                )

            elif etype == "tool_result":
                snapshot.append(event)
                # Resume "Thinking…" while the LLM digests the result
                status.markdown(_THINKING_HTML, unsafe_allow_html=True)

            elif etype == "token":
                if not tokens_started:
                    status.empty()
                    tokens_started = True
                full_response += event["text"]
                response_area.markdown(full_response + "▌")

            elif etype == "response":
                snapshot.append(event)
                if not full_response:
                    full_response = event.get("content", "")

        # Remove the blinking cursor once streaming finishes
        status.empty()
        if full_response:
            response_area.markdown(full_response)

    latency_ms = (time.time() - t_start) * 1000

    # Output guardrail check
    output_guard = run_output_pipeline(full_response)
    if output_guard.blocked:
        full_response = CANNED_OUTPUT_REFUSAL

    # Compute costs
    input_cost, output_cost = compute_cost(
        model_id=config.model_id,
        input_tokens=0,
        output_tokens=0,
        pricing=pricing_data,
        model_type=config.model_type,
        latency_ms=latency_ms,
    )

    log_call(
        model_id=config.model_id,
        model_type=config.model_type,
        input_tokens=0,
        output_tokens=0,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        latency_ms=latency_ms,
        pricing_source=pricing_source,
        pricing_fetched_at=pricing_fetched_at,
        guardrail_blocked=output_guard.blocked,
        block_layer="output" if output_guard.blocked else None,
        block_reason=output_guard.reason if output_guard.blocked else None,
        block_stage="output_pipeline" if output_guard.blocked else None,
        summary_used=bool(thread.get("summaries")),
        tool_calls=[s["tool"] for s in snapshot if s.get("type") == "tool_call"],
    )

    assistant_dict = {
        "role": "assistant",
        "content": full_response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state_snapshot": snapshot,
        "metadata": {
            "model_label": config.model_label,
            "model_type": config.model_type,
            "latency_ms": round(latency_ms, 2),
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "input_guard": {
                "blocked": False,
                "reason": None,
                "pii_count": len(input_guard.pii_entities or []),
                "latency_ms": round(input_guard.latency_ms, 2),
                "stages": input_guard.stages,
            },
            "output_guard": {
                "blocked": output_guard.blocked,
                "reason": output_guard.reason,
                "latency_ms": round(output_guard.latency_ms, 2),
                "stages": output_guard.stages,
            },
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
