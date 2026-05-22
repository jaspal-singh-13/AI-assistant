"""Unit tests for tools — time, weather (mocked), search (mocked), metrics.

FR §15.4.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestTimeTool:
    def test_returns_string(self):
        """get_current_time returns a non-empty string."""
        from tools.time_tool import get_current_time
        result = get_current_time()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_year(self):
        """Result contains the current year."""
        from tools.time_tool import get_current_time
        import datetime
        result = get_current_time()
        assert str(datetime.datetime.now().year) in result


class TestWeatherTool:
    def test_returns_temperature(self):
        """get_weather returns temperature string for a known city (mocked)."""
        pytest.skip("Phase 1 — needs @tool decorator and requests mock")

    def test_graceful_city_not_found(self):
        """Returns error string instead of raising exception."""
        pytest.skip("Phase 1")


class TestSearchTool:
    def test_returns_results(self):
        """web_search returns top 5 result strings (mocked DDGS)."""
        pytest.skip("Phase 1 — needs @tool decorator and DDGS mock")

    def test_empty_query_handled(self):
        pytest.skip("Phase 1")


class TestMetricsTool:
    def test_no_data_returns_message(self, tmp_path):
        """Returns a descriptive message when calls.jsonl is empty."""
        pytest.skip("Phase 1")

    def test_reads_existing_log(self, tmp_path):
        """Parses calls.jsonl and returns summary string."""
        pytest.skip("Phase 1")
