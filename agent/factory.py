"""LangGraph ReAct agent factory.

One compiled graph is created per model. Both models receive the same tool list.
Streaming uses graph.stream(stream_mode=["updates", "messages"]).

FR-AGT-01: Single create_react_agent graph for both models.
FR-AGT-02: Streaming via graph.stream with updates + messages modes.
FR-AGT-03: state_snapshot captured per run with call_id per tool step.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from langgraph.graph.graph import CompiledGraph

import nest_asyncio
nest_asyncio.apply()  # enables async streaming from within Streamlit's event loop


def create_agent(llm: "BaseChatModel", tools: list["BaseTool"]) -> "CompiledGraph":
    """
    Build and return a compiled LangGraph ReAct agent.

    The graph is recreated on every model switch — cheap because it's just a
    graph compile, not a model download.
    """
    from langgraph.prebuilt import create_react_agent
    return create_react_agent(llm, tools)


def run_agent(
    graph: "CompiledGraph",
    messages: list[dict],
    config: dict | None = None,
) -> tuple[str, list[dict]]:
    """
    Stream the agent graph and collect:
      - final_response: the last AIMessage content string
      - state_snapshot: list of step dicts (FR-AGT-03)

    Each tool_call step includes call_id (FR §15.2).

    Returns (final_response, state_snapshot).
    """
    steps: list[dict] = []
    final_response = ""

    for chunk in graph.stream({"messages": messages}, config, stream_mode="updates"):
        for node_name, state in chunk.items():
            for msg in state.get("messages", []):
                step = _parse_message_to_step(msg)
                if step:
                    steps.append(step)
                    if step["type"] == "response":
                        final_response = step["content"]

    return final_response, steps


def stream_and_collect(
    graph: "CompiledGraph",
    messages: list[dict],
    config: dict | None = None,
) -> "tuple[Generator[str, None, None], list[dict]]":
    """
    Single-pass stream that:
      - yields token strings for st.write_stream() display
      - accumulates and returns the full state_snapshot

    Uses stream_mode=['updates','messages'] so one LLM call feeds both.
    Returns (token_generator, snapshot_list).
    snapshot_list is populated in-place as the generator is consumed.
    """
    from typing import Generator
    from langchain_core.messages import AIMessageChunk

    snapshot: list[dict] = []

    def _gen() -> "Generator[str, None, None]":
        from langchain_core.messages import AIMessageChunk
        for item in graph.stream(
            {"messages": messages}, config, stream_mode=["updates", "messages"]
        ):
            mode, payload = item
            if mode == "updates":
                for _node, state in payload.items():
                    for msg in state.get("messages", []):
                        step = _parse_message_to_step(msg)
                        if step:
                            snapshot.append(step)
            elif mode == "messages":
                chunk, metadata = payload
                if (
                    isinstance(chunk, AIMessageChunk)
                    and metadata.get("langgraph_node") == "agent"
                ):
                    text = _extract_text(chunk.content)
                    if text:
                        yield text

    return _gen(), snapshot


def stream_events(
    graph: "CompiledGraph",
    messages: list[dict],
    config: dict | None = None,
) -> "Generator[dict, None, None]":
    """
    Yield unified event dicts for live UI rendering.

    Event shapes:
      {"type": "token",       "text": "..."}
      {"type": "tool_call",   "tool": "...", "args": {...}, "call_id": "..."}
      {"type": "tool_result", "content": "...", "call_id": "..."}
      {"type": "response",    "content": "..."}

    The caller decides how each event type is presented (spinner, status chip,
    streamed text, etc.) so factory.py stays UI-agnostic.
    """
    from typing import Generator
    from langchain_core.messages import AIMessageChunk

    for item in graph.stream(
        {"messages": messages}, config, stream_mode=["updates", "messages"]
    ):
        mode, payload = item
        if mode == "updates":
            for _node, state in payload.items():
                for msg in state.get("messages", []):
                    step = _parse_message_to_step(msg)
                    if step:
                        yield step
        elif mode == "messages":
            chunk, metadata = payload
            if (
                isinstance(chunk, AIMessageChunk)
                and metadata.get("langgraph_node") == "agent"
            ):
                text = _extract_text(chunk.content)
                if text:
                    yield {"type": "token", "text": text}


def _extract_text(content: Any) -> str:
    """Return plain text from a message content value (str or list of content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block["text"] if isinstance(block, dict) else str(block)
            for block in content
            if not isinstance(block, dict) or block.get("type") == "text"
        )
    return str(content)


def _parse_message_to_step(msg: Any) -> dict | None:
    """
    Convert a LangGraph message object into a state_snapshot step dict.

    Step types:
      - "tool_call": {type, tool, args, call_id, latency_ms}
      - "tool_result": {type, content, call_id}
      - "response": {type, content}
    """
    from langchain_core.messages import AIMessage, ToolMessage

    if isinstance(msg, AIMessage):
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            return {
                "type": "tool_call",
                "tool": tc["name"],
                "args": tc["args"],
                "call_id": tc["id"],
                "latency_ms": 0,
            }
        return {"type": "response", "content": _extract_text(msg.content)}

    if isinstance(msg, ToolMessage):
        return {"type": "tool_result", "content": _extract_text(msg.content), "call_id": msg.tool_call_id}

    return None
