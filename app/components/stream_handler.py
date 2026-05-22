"""Stream handler — wraps graph.stream() to feed tokens and steps to the UI.

Uses sync graph.stream(stream_mode=["updates", "messages"]) (Option A from PRD §3).
Token streaming delivered via st.write_stream().

FR-AGT-02, FR-AGT-03.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Generator

import streamlit as st

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph


def handle_send(user_message: str) -> None:
    """
    Full pipeline for one user message send:
      1. Run input guardrails
      2. Build LLM context from thread
      3. Stream agent graph → collect tokens + state_snapshot
      4. Run output guardrails on final response
      5. Log the call to calls.jsonl
      6. Append user + assistant messages to thread and save

    TODO (Phase 2): implement.
    """
    thread = st.session_state.get("active_thread")
    model_key = st.session_state.get("model_key", "claude-sonnet")
    graph = st.session_state.get("agent_graph")

    if thread is None or graph is None:
        st.error("No active thread or agent graph. Please create a thread first.")
        return

    # TODO Phase 2:
    # 1. from guardrails.input_guard import run_input_pipeline, CANNED_REFUSAL, message_hash
    # 2. from memory.manager import get_llm_context, append_message
    # 3. stream_and_collect(graph, lc_messages, config) -> (response, snapshot)
    # 4. from guardrails.output_guard import run_output_pipeline, CANNED_OUTPUT_REFUSAL
    # 5. from observability.logger import log_call
    # 6. append_message(thread, user_dict); append_message(thread, assistant_dict)
    raise NotImplementedError("Phase 2 — handle_send")


def stream_tokens(
    graph: "CompiledGraph",
    messages: list,
    config: dict,
) -> Generator[str, None, list[dict]]:
    """
    Yield token strings from the agent graph stream for display via st.write_stream().
    Also accumulates and returns the state_snapshot list.

    TODO (Phase 2): implement.
    """
    # steps: list[dict] = []
    # for chunk in graph.stream({"messages": messages}, config, stream_mode=["updates", "messages"]):
    #     ...parse and yield tokens, collect steps...
    raise NotImplementedError("Phase 2 — stream_tokens")
