"""Unit tests for tools — time, weather (mocked), search (mocked), observability, evaluation.

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


class TestObservabilityTool:
    def _make_entry(self, model_id: str, latency_ms: float, cost: float, blocked: bool = False) -> dict:
        return {
            "model_id": model_id,
            "model_type": "frontier",
            "latency_ms": latency_ms,
            "total_cost_usd": cost,
            "input_tokens": 100,
            "output_tokens": 50,
            "cost_per_1k_tokens": 0.001,
            "guardrail_blocked": blocked,
            "tool_calls": [],
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

    def test_no_data_returns_message(self, tmp_path):
        """Returns a descriptive message when calls.jsonl is absent."""
        empty_log = tmp_path / "calls.jsonl"
        with patch("tools.observability_tool.CALLS_LOG", empty_log):
            from tools.observability_tool import get_observability_summary
            result = get_observability_summary.invoke({"model_id": ""})
        assert "No call data" in result

    def test_reads_existing_log(self, tmp_path):
        """Parses calls.jsonl and returns summary with latency and cost."""
        log_file = tmp_path / "calls.jsonl"
        entry = self._make_entry("claude-haiku-20240307", 500.0, 0.002)
        log_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        with patch("tools.observability_tool.CALLS_LOG", log_file):
            from tools.observability_tool import get_observability_summary
            result = get_observability_summary.invoke({"model_id": ""})
        assert "claude-haiku" in result
        assert "500" in result
        assert "$0.0020" in result

    def test_two_models_both_shown(self, tmp_path):
        """When two models are present, both appear in the output."""
        log_file = tmp_path / "calls.jsonl"
        lines = [
            json.dumps(self._make_entry("claude-haiku-20240307", 400.0, 0.001)),
            json.dumps(self._make_entry("Qwen/Qwen2.5-7B-Instruct", 800.0, 0.0005)),
        ]
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with patch("tools.observability_tool.CALLS_LOG", log_file):
            from tools.observability_tool import get_observability_summary
            result = get_observability_summary.invoke({"model_id": ""})
        assert "claude-haiku" in result
        assert "Qwen" in result

    def test_model_id_filter(self, tmp_path):
        """model_id parameter narrows output to matching model."""
        log_file = tmp_path / "calls.jsonl"
        lines = [
            json.dumps(self._make_entry("claude-haiku-20240307", 400.0, 0.001)),
            json.dumps(self._make_entry("Qwen/Qwen2.5-7B-Instruct", 800.0, 0.0005)),
        ]
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with patch("tools.observability_tool.CALLS_LOG", log_file):
            from tools.observability_tool import get_observability_summary
            result = get_observability_summary.invoke({"model_id": "claude"})
        assert "claude" in result
        assert "Qwen" not in result


class TestEvaluationTool:
    def _make_scores(self, models: list[str]) -> dict:
        return {
            "generated_at": "2026-01-01T00:00:00",
            "models": {
                mid: {
                    "hallucination": {"pass_rate": 0.8, "low_confidence_excluded": 0},
                    "bias_harmful": {"pass_rate": 0.9, "low_confidence_excluded": 1},
                    "content_safety": {"pass_rate": 0.95, "low_confidence_excluded": 0},
                }
                for mid in models
            },
        }

    def test_missing_file_returns_friendly_message(self, tmp_path):
        """Returns a friendly fallback when model_scores.json is absent."""
        missing = tmp_path / "model_scores.json"
        with patch("tools.evaluation_tool.SCORES_FILE", missing):
            from tools.evaluation_tool import get_evaluation_summary
            result = get_evaluation_summary.invoke({"model_id": ""})
        assert "No evaluation results" in result
        assert "make eval" in result

    def test_reads_existing_scores(self, tmp_path):
        """Parses model_scores.json and returns hallucination / bias / safety lines."""
        scores_file = tmp_path / "model_scores.json"
        scores_file.write_text(
            json.dumps(self._make_scores(["claude-haiku-20240307"])), encoding="utf-8"
        )
        with patch("tools.evaluation_tool.SCORES_FILE", scores_file):
            from tools.evaluation_tool import get_evaluation_summary
            result = get_evaluation_summary.invoke({"model_id": ""})
        assert "claude-haiku" in result
        assert "Hallucination" in result
        assert "Content Safety" in result

    def test_model_id_filter(self, tmp_path):
        """model_id parameter limits output to matching model."""
        scores_file = tmp_path / "model_scores.json"
        scores_file.write_text(
            json.dumps(self._make_scores(["claude-haiku-20240307", "Qwen/Qwen2.5-7B-Instruct"])),
            encoding="utf-8",
        )
        with patch("tools.evaluation_tool.SCORES_FILE", scores_file):
            from tools.evaluation_tool import get_evaluation_summary
            result = get_evaluation_summary.invoke({"model_id": "claude"})
        assert "claude" in result
        assert "Qwen" not in result
