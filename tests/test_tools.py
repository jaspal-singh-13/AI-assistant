"""Unit tests for tools — time, weather (mocked), search (mocked), metrics.

FR §15.4.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestTimeTool:
    def test_returns_string(self):
        """get_current_time returns a non-empty string."""
        from tools.time_tool import get_current_time
        result = get_current_time.invoke({})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_year(self):
        """Result contains the current year."""
        from tools.time_tool import get_current_time
        import datetime
        result = get_current_time.invoke({})
        assert str(datetime.datetime.now().year) in result


class TestWeatherTool:
    def test_returns_temperature(self):
        """get_weather returns temperature string for a known city (mocked)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "current_condition": [{
                "temp_C": "20",
                "weatherDesc": [{"value": "Sunny"}],
                "humidity": "50",
            }]
        }
        mock_response.raise_for_status = MagicMock()
        with patch("tools.weather_tool.requests.get", return_value=mock_response):
            from tools.weather_tool import get_weather
            result = get_weather.invoke({"city": "London"})
        assert "20°C" in result
        assert "Sunny" in result
        assert "50%" in result

    def test_graceful_city_not_found(self):
        """Returns error string instead of raising exception."""
        http_err = requests.exceptions.HTTPError()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        http_err.response = mock_resp
        with patch("tools.weather_tool.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = http_err
            from tools.weather_tool import get_weather
            result = get_weather.invoke({"city": "FakeCity12345"})
        assert "City not found" in result


class TestSearchTool:
    def test_returns_results(self):
        """web_search returns top 5 result strings (mocked DDGS)."""
        fake_results = [
            {"title": f"Title {i}", "body": f"Body {i}", "href": f"http://example.com/{i}"}
            for i in range(5)
        ]
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = fake_results
        with patch("tools.search_tool.DDGS", return_value=mock_ddgs):
            from tools.search_tool import web_search
            result = web_search.invoke({"query": "test query"})
        assert "1." in result
        assert "Title 0" in result

    def test_empty_query_handled(self):
        """Returns 'No results found.' when DDG returns nothing."""
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = []
        with patch("tools.search_tool.DDGS", return_value=mock_ddgs):
            from tools.search_tool import web_search
            result = web_search.invoke({"query": ""})
        assert "No results found." in result


class TestMetricsTool:
    def test_no_data_returns_message(self, tmp_path):
        """Returns a descriptive message when calls.jsonl is empty."""
        empty_log = tmp_path / "calls.jsonl"
        with patch("tools.metrics_tool.CALLS_LOG", empty_log):
            from tools.metrics_tool import get_metrics
            result = get_metrics.invoke({})
        assert "No call data" in result

    def test_reads_existing_log(self, tmp_path):
        """Parses calls.jsonl and returns summary string."""
        log_file = tmp_path / "calls.jsonl"
        entry = {
            "model_key": "claude-sonnet",
            "latency_ms": 500,
            "total_cost": 0.002,
            "blocked": False,
        }
        log_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        with patch("tools.metrics_tool.CALLS_LOG", log_file):
            from tools.metrics_tool import get_metrics
            result = get_metrics.invoke({})
        assert "claude-sonnet" in result
        assert "500ms" in result
