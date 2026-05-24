"""Unit tests for memory.manager — thread CRUD, llm_context, summarisation trigger.

FR §15.4 + AC §9.1.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestSummarisationThreshold:
    """FR §15.1 + §15.7 — summarisation trigger threshold."""

    def test_no_trigger_when_uncovered_less_than_window(self):
        """Summarisation must NOT trigger when len(new_uncovered) < context_window_size."""
        from memory.manager import get_llm_context
        # 15 messages, window=10 → older=5, new_uncovered=5 < 10, no trigger
        thread = {
            "context_window_size": 10,
            "messages": [{"role": "user", "content": f"msg{i}"} for i in range(15)],
            "summaries": [],
            "summary_cursor": 0,
        }
        with patch("memory.manager.update_summaries") as mock_update:
            get_llm_context(thread)
            mock_update.assert_not_called()

    def test_triggers_exactly_once_per_batch(self):
        """Summarisation triggers exactly once when len(new_uncovered) >= window."""
        from memory.manager import get_llm_context
        # 25 messages, window=10 → older=15, new_uncovered=15 >= 10, triggers once
        thread = {
            "context_window_size": 10,
            "messages": [{"role": "user", "content": f"msg{i}"} for i in range(25)],
            "summaries": [],
            "summary_cursor": 0,
        }
        with patch("memory.manager.update_summaries") as mock_update:
            get_llm_context(thread)
            mock_update.assert_called_once()

    def test_summary_cursor_advances_correctly(self):
        """After summarisation, summary_cursor advances by exactly len(new_uncovered)."""
        from memory.manager import update_summaries
        thread = {
            "context_window_size": 10,
            "messages": [],
            "summaries": [],
            "summary_cursor": 0,
        }
        new_uncovered = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        with patch("memory.summariser.summarise", return_value="summary text"):
            update_summaries(thread, new_uncovered)
        assert thread["summary_cursor"] == 10
        assert len(thread["summaries"]) == 1
        assert thread["summaries"][0]["covers"] == "1-10"


class TestThreadCRUD:
    """FR-MEM-06 — thread create, list, load."""

    def test_create_thread_auto_title(self, tmp_path):
        """Thread title is generated from first 6 words of first message."""
        with patch("memory.manager.THREADS_DIR", tmp_path / "threads"), \
             patch("memory.manager.INDEX_PATH", tmp_path / "index.json"):
            from memory.manager import create_thread
            thread = create_thread("Hello world how are you doing today")
            assert thread["title"] == "Hello world how are you doing"

    def test_thread_persists_across_reload(self, tmp_path):
        """Thread JSON is loadable after a save."""
        with patch("memory.manager.THREADS_DIR", tmp_path / "threads"), \
             patch("memory.manager.INDEX_PATH", tmp_path / "index.json"):
            from memory.manager import create_thread, load_thread
            thread = create_thread("Persisted thread test message")
            loaded = load_thread(thread["id"])
            assert loaded["title"] == thread["title"]
            assert loaded["id"] == thread["id"]

    def test_list_threads_ordered_by_updated_at(self, tmp_path):
        """list_threads returns newest first."""
        import time
        with patch("memory.manager.THREADS_DIR", tmp_path / "threads"), \
             patch("memory.manager.INDEX_PATH", tmp_path / "index.json"):
            from memory.manager import create_thread, list_threads
            t1 = create_thread("First thread message here")
            time.sleep(0.01)
            t2 = create_thread("Second thread message here")
            threads = list_threads()
            assert threads[0]["id"] == t2["id"]
            assert threads[1]["id"] == t1["id"]


class TestLLMContext:
    """FR-MEM-02 — LLM context is sliding window + merged summary."""

    def test_context_never_exceeds_window_plus_summary(self):
        """LLM context never exceeds app SystemMessage + 1 summary SystemMessage + context_window_size."""
        from memory.manager import get_llm_context
        thread = {
            "context_window_size": 10,
            "messages": [{"role": "user", "content": f"msg{i}"} for i in range(25)],
            "summaries": [{"covers": "1-15", "text": "existing summary"}],
            "summary_cursor": 15,
        }
        # new_uncovered = older[15:] = messages[0:15][15:] = [] — no trigger
        with patch("memory.manager.update_summaries"):
            result = get_llm_context(thread)
        # app SystemMessage + summary SystemMessage + 10 recent = 12 max
        assert len(result) <= 12

    def test_context_label_all_messages(self):
        """Label shows 'LLM sees all N messages' when total <= window."""
        from memory.manager import get_context_label
        thread = {
            "context_window_size": 10,
            "messages": [{}] * 5,
            "summaries": [],
            "summary_cursor": 0,
        }
        assert "all 5" in get_context_label(thread)

    def test_context_label_with_summaries(self):
        """Label shows correct summary count and covered message count."""
        from memory.manager import get_context_label
        thread = {
            "context_window_size": 10,
            "messages": [{}] * 25,
            "summaries": [{"covers": "1-10", "text": "x"}, {"covers": "11-15", "text": "y"}],
            "summary_cursor": 15,
        }
        label = get_context_label(thread)
        assert "last 10" in label
        assert "2 summaries" in label
