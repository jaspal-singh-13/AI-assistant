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

# TODO (Phase 1): uncomment once deps installed
# import nest_asyncio
# nest_asyncio.apply()  # enables async streaming from within Streamlit's event loop


def create_agent(llm: "BaseChatModel", tools: list["BaseTool"]) -> "CompiledGraph":
    """
    Build and return a compiled LangGraph ReAct agent.

    The graph is recreated on every model switch — cheap because it's just a
    graph compile, not a model download.

    TODO (Phase 1): implement.
    """
    # from langgraph.prebuilt import create_react_agent
    # return create_react_agent(llm, tools)
    raise NotImplementedError("Phase 1 — create_agent")


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

    TODO (Phase 1): implement streaming loop.
    """
    # steps: list[dict] = []
    # final_response = ""
    #
    # for chunk in graph.stream({"messages": messages}, config, stream_mode="updates"):
    #     for node_name, state in chunk.items():
    #         for msg in state.get("messages", []):
    #             step = _parse_message_to_step(msg)
    #             if step:
    #                 steps.append(step)
    #                 if step["type"] == "response":
    #                     final_response = step["content"]
    #
    # return final_response, steps
    raise NotImplementedError("Phase 1 — run_agent")


def _parse_message_to_step(msg: Any) -> dict | None:
    """
    Convert a LangGraph message object into a state_snapshot step dict.

    Step types:
      - "tool_call": {type, tool, args, call_id, latency_ms}
      - "tool_result": merged into matching tool_call step
      - "response": {type, content}

    TODO (Phase 1): implement using AIMessage / ToolMessage isinstance checks.
    """
    raise NotImplementedError("Phase 1 — _parse_message_to_step")
