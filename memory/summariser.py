"""Incremental summarisation — summary-of-summary approach.

The LLM never re-reads already-summarised messages.
Summary N+1 = summarise(summary_N_text + new_batch_messages).

FR-MEM-05, FR §15.1.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

_SUMMARISE_PROMPT = """You are a conversation summariser. Produce a concise paragraph
(under 150 words) that captures the key facts, user preferences, and decisions from the
messages below. Merge with the existing summary if provided.

Existing summary:
{prev_summary}

New messages to incorporate:
{messages_text}

Return only the updated summary paragraph — no preamble, no bullet points."""


def summarise(prev_text: str, messages: list[dict], llm: BaseChatModel | None = None) -> str:
    """
    Produce an updated summary string from *prev_text* + *messages*.

    *llm* defaults to a lightweight Claude call if None.
    """
    if llm is None:
        from agent.models import build_llm
        llm = build_llm("claude-sonnet")

    messages_text = "\n".join(
        f"[{m['role'].upper()}] {m['content']}" for m in messages
    )
    prompt = _SUMMARISE_PROMPT.format(
        prev_summary=prev_text or "(none)",
        messages_text=messages_text,
    )
    return llm.invoke([HumanMessage(content=prompt)]).content


def merge(summaries: list[dict]) -> str:
    """
    Merge all summary dicts into a single SystemMessage content string.

    Format:
        [Conversation context — {covered} earlier messages]
        Round 1 (msgs {covers}): {text}
        Round 2 (msgs {covers}): {text}
        ...

    Returns empty string if no summaries exist.
    """
    if not summaries:
        return ""
    lines = [f"[Conversation context — earlier messages]"]
    for i, s in enumerate(summaries, start=1):
        lines.append(f"Round {i} (msgs {s['covers']}): {s['text']}")
    return "\n".join(lines)
