"""Unit tests for memory.manager — thread CRUD, llm_context, summarisation trigger.

FR §15.4 + AC §9.1.
"""

from __future__ import annotations

import pytest


class TestSummarisationThreshold:
    """FR §15.1 + §15.7 — summarisation trigger threshold."""

    def test_no_trigger_when_uncovered_less_than_window(self):
        """Summarisation must NOT trigger when len(new_uncovered) < context_window_size."""
        # TODO (Phase 1): implement test
        pytest.skip("Phase 1")

    def test_triggers_exactly_once_per_batch(self):
        """Summarisation triggers exactly once per window-sized batch of new uncovered messages."""
        pytest.skip("Phase 1")

    def test_summary_cursor_advances_correctly(self):
        """After summarisation, summary_cursor advances by exactly len(new_uncovered)."""
        pytest.skip("Phase 1")


class TestThreadCRUD:
    """FR-MEM-06 — thread create, list, load."""

    def test_create_thread_auto_title(self):
        """Thread title is generated from first 6 words of first message."""
        pytest.skip("Phase 1")

    def test_thread_persists_across_reload(self, tmp_path):
        """Thread JSON is loadable after a save."""
        pytest.skip("Phase 1")

    def test_list_threads_ordered_by_updated_at(self, tmp_path):
        """list_threads returns newest first."""
        pytest.skip("Phase 1")


class TestLLMContext:
    """FR-MEM-02 — LLM context is sliding window + merged summary."""

    def test_context_never_exceeds_window_plus_summary(self):
        """LLM context never exceeds context_window_size + 1 summary SystemMessage."""
        pytest.skip("Phase 1")

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
