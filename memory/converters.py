"""Converters between thread JSON message dicts and LangChain message objects.

Used by memory.manager.get_llm_context() to build the LLM input list.
"""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage


def dicts_to_messages(messages: list[dict]) -> list[BaseMessage]:
    """
    Convert thread JSON message dicts → LangChain message objects.

    Mapping:
      role "user"      → HumanMessage(content=...)
      role "assistant" → AIMessage(content=...)
      role "tool"      → ToolMessage(content=..., tool_call_id=...)
    """
    result = []
    for m in messages:
        role = m["role"]
        content = m.get("content", "")
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        elif role == "tool":
            result.append(ToolMessage(content=content, tool_call_id=m.get("tool_call_id", "")))
    return result


def message_to_dict(message: BaseMessage, **extra) -> dict:
    """
    Convert a LangChain BaseMessage → a thread JSON message dict.

    Always includes: role, content, timestamp (ISO UTC).
    *extra* kwargs are merged in (e.g. metadata, state_snapshot, token_count).
    """
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    return {
        "role": role,
        "content": message.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
