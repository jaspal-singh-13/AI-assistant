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

from observability.logger import get_logger

logger = get_logger(__name__)

MEMORY_DIR = Path(__file__).parent
INDEX_PATH = MEMORY_DIR / "index.json"
THREADS_DIR = MEMORY_DIR / "threads"

DEFAULT_CONTEXT_WINDOW = 10
DEFAULT_SUMMARY_TRIGGER = 10   # summarise when this many messages fall outside the window


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
        "summary_trigger": DEFAULT_SUMMARY_TRIGGER,
        "summary_cursor": 0,
        "summaries": [],
        "messages": [],
    }
    THREADS_DIR.mkdir(parents=True, exist_ok=True)
    path = THREADS_DIR / f"{thread_id}.json"
    path.write_text(json.dumps(thread, indent=2, ensure_ascii=False), encoding="utf-8")
    index = _load_index()
    index["threads"].append({
        "id": thread_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    })
    _save_index(index)
    logger.debug("create_thread | id=%s title=%r", thread_id, title)
    return thread


def load_thread(thread_id: str) -> dict:
    """Load and return a thread dict from disk. Raises FileNotFoundError if missing."""
    path = THREADS_DIR / f"{thread_id}.json"
    logger.debug("load_thread | id=%s", thread_id)
    return json.loads(path.read_text(encoding="utf-8"))


def save_thread(thread: dict) -> None:
    """Persist a thread dict to disk and sync message_count + updated_at in index.json."""
    thread["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = THREADS_DIR / f"{thread['id']}.json"
    try:
        path.write_text(json.dumps(thread, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logger.warning("save_thread | disk write failed | id=%s path=%s", thread["id"], path, exc_info=True)
        raise
    index = _load_index()
    for entry in index["threads"]:
        if entry["id"] == thread["id"]:
            entry["updated_at"] = thread["updated_at"]
            entry["message_count"] = len(thread["messages"])
    _save_index(index)
    logger.debug("save_thread | id=%s msg_count=%d", thread["id"], len(thread["messages"]))


def list_threads() -> list[dict]:
    """Return all thread index entries, newest first."""
    return sorted(
        _load_index()["threads"],
        key=lambda t: t["updated_at"],
        reverse=True,
    )


def delete_thread(thread_id: str) -> None:
    """Delete thread JSON file and remove from index."""
    path = THREADS_DIR / f"{thread_id}.json"
    if path.exists():
        path.unlink()
    index = _load_index()
    index["threads"] = [t for t in index["threads"] if t["id"] != thread_id]
    _save_index(index)
    logger.debug("delete_thread | id=%s", thread_id)


def rename_thread(thread: dict, new_title: str) -> None:
    """Update thread title and persist."""
    thread["title"] = new_title.strip() or "New thread"
    save_thread(thread)


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
    """
    from memory.converters import dicts_to_messages
    from memory.summariser import merge, summarise

    window = thread["context_window_size"]
    messages = thread["messages"]
    recent = messages[-window:]
    older = messages[:-window]
    new_uncovered = older[thread["summary_cursor"]:]

    logger.debug(
        "get_llm_context | window=%d total=%d recent=%d summary_cursor=%d",
        window, len(messages), len(recent), thread["summary_cursor"],
    )

    min_trigger = window + 5
    trigger = max(thread.get("summary_trigger", DEFAULT_SUMMARY_TRIGGER), min_trigger)
    if len(new_uncovered) >= trigger:
        logger.info("get_llm_context | summarisation triggered | uncovered=%d", len(new_uncovered))
        update_summaries(thread, new_uncovered)

    merged = merge(thread["summaries"])
    lc_messages = dicts_to_messages(recent)
    if merged:
        from langchain_core.messages import SystemMessage
        return [SystemMessage(content=merged)] + lc_messages
    return lc_messages


def update_summaries(thread: dict, new_uncovered: list[dict]) -> None:
    """
    Append a new incremental summary to thread["summaries"] and advance summary_cursor.

    Summary N+1 = summarise(summary_N_text, new_batch) — LLM never re-reads old messages.
    """
    from memory.summariser import summarise
    prev_text = thread["summaries"][-1]["text"] if thread["summaries"] else ""
    start_idx = thread["summary_cursor"] + 1
    end_idx = thread["summary_cursor"] + len(new_uncovered)
    new_text = summarise(prev_text, new_uncovered)
    thread["summaries"].append({"covers": f"{start_idx}-{end_idx}", "text": new_text})
    thread["summary_cursor"] += len(new_uncovered)


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
