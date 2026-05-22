"""Thread memory manager.

Handles:
  - Thread CRUD (create, read, list, update, delete) backed by JSON files.
  - LLM context construction: sliding window + merged summary SystemMessage.
  - Incremental summarisation trigger and cursor update.

FR-MEM-01 to FR-MEM-06, FR §15.1 (summarisation threshold correction).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage

MEMORY_DIR = Path(__file__).parent
INDEX_PATH = MEMORY_DIR / "index.json"
THREADS_DIR = MEMORY_DIR / "threads"

DEFAULT_CONTEXT_WINDOW = 10


# ── Index helpers ──────────────────────────────────────────────────────────────

def _load_index() -> dict:
    if not INDEX_PATH.exists():
        return {"threads": []}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _save_index(index: dict) -> None:
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Thread CRUD ────────────────────────────────────────────────────────────────

def create_thread(first_message: str = "") -> dict:
    """
    Create a new thread, persist it, update index.json, and return the thread dict.

    Title is auto-generated from the first 6 words of *first_message* (FR-MEM-06).

    TODO (Phase 1): implement.
    """
    thread_id = str(uuid.uuid4())[:8]
    title = " ".join(first_message.split()[:6]) or "New thread"
    now = datetime.now(timezone.utc).isoformat()
    thread = {
        "id": thread_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "context_window_size": DEFAULT_CONTEXT_WINDOW,
        "summary_cursor": 0,
        "summaries": [],
        "messages": [],
    }
    # TODO: save thread to THREADS_DIR/{thread_id}.json
    # TODO: append entry to index.json
    raise NotImplementedError("Phase 1 — create_thread")


def load_thread(thread_id: str) -> dict:
    """Load and return a thread dict from disk. Raises FileNotFoundError if missing."""
    path = THREADS_DIR / f"{thread_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_thread(thread: dict) -> None:
    """Persist a thread dict to disk and update index.json updated_at."""
    thread["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = THREADS_DIR / f"{thread['id']}.json"
    path.write_text(json.dumps(thread, indent=2, ensure_ascii=False), encoding="utf-8")
    # TODO: sync message_count in index.json entry


def list_threads() -> list[dict]:
    """Return all thread index entries, newest first."""
    return sorted(
        _load_index()["threads"],
        key=lambda t: t["updated_at"],
        reverse=True,
    )


def append_message(thread: dict, message: dict) -> None:
    """Append a message dict to thread["messages"] and save."""
    thread["messages"].append(message)
    save_thread(thread)


# ── LLM context construction ───────────────────────────────────────────────────

def get_llm_context(thread: dict) -> list["BaseMessage"]:
    """
    Build and return the LLM context list for the current thread state.

    Structure: [SystemMessage(merged_summary)] + last_N messages

    The context is NOT persisted — rebuilt on every call (FR-MEM-02).
    Summarisation is triggered here if threshold is met (FR §15.1).

    TODO (Phase 1): implement.
    """
    # from memory.converters import dicts_to_messages
    # from memory.summariser import merge, summarise
    #
    # window = thread["context_window_size"]
    # messages = thread["messages"]
    # recent = messages[-window:]
    # older = messages[:-window]
    # new_uncovered = older[thread["summary_cursor"]:]
    #
    # if len(new_uncovered) >= window:
    #     update_summaries(thread, new_uncovered)
    #
    # merged = merge(thread["summaries"])
    # lc_messages = dicts_to_messages(recent)
    # if merged:
    #     from langchain_core.messages import SystemMessage
    #     return [SystemMessage(content=merged)] + lc_messages
    # return lc_messages
    raise NotImplementedError("Phase 1 — get_llm_context")


def update_summaries(thread: dict, new_uncovered: list[dict]) -> None:
    """
    Append a new incremental summary to thread["summaries"] and advance summary_cursor.

    Summary N+1 = summarise(summary_N_text, new_batch) — LLM never re-reads old messages.

    TODO (Phase 1): implement.
    """
    # from memory.summariser import summarise
    # prev_text = thread["summaries"][-1]["text"] if thread["summaries"] else ""
    # start_idx = thread["summary_cursor"] + 1
    # end_idx = thread["summary_cursor"] + len(new_uncovered)
    # new_text = summarise(prev_text, new_uncovered)
    # thread["summaries"].append({"covers": f"{start_idx}-{end_idx}", "text": new_text})
    # thread["summary_cursor"] += len(new_uncovered)
    raise NotImplementedError("Phase 1 — update_summaries")


def get_context_label(thread: dict) -> str:
    """
    Return the dynamic context window label shown below the slider (FR-MEM-04).

    Examples:
      "LLM sees all 8 messages"
      "LLM sees last 10 messages + 2 summaries covering 20 earlier"
    """
    window = thread["context_window_size"]
    total = len(thread["messages"])
    n_summaries = len(thread["summaries"])
    covered = thread["summary_cursor"]

    if total <= window:
        return f"LLM sees all {total} messages"
    return f"LLM sees last {window} messages + {n_summaries} summaries covering {covered} earlier"
