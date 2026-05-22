"""Unit tests for observability/logger.py and observability/pricing.py.

External HTTP calls (LiteLLM pricing fetch) are always mocked.
File system writes use tmp_path fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestCallLogger:
    def test_log_call_creates_file(self, tmp_path):
        """log_call() creates calls.jsonl if it does not exist."""
        from observability.logger import log_call
        with patch("observability.logger.LOGS_DIR", tmp_path):
            with patch("observability.logger.CALLS_LOG", tmp_path / "calls.jsonl"):
                log_call(
                    model_id="claude-sonnet-4-20250514",
                    model_type="frontier",
                    input_tokens=100,
                    output_tokens=50,
                    input_cost_usd=0.0003,
                    output_cost_usd=0.00075,
                    latency_ms=1200.0,
                    pricing_source="litellm_json",
                    pricing_fetched_at="2026-05-22T00:00:00+00:00",
                )
                assert (tmp_path / "calls.jsonl").exists()

    def test_log_call_writes_valid_json(self, tmp_path):
        """Each log_call() line is valid JSON with all required fields."""
        from observability.logger import log_call
        log_path = tmp_path / "calls.jsonl"
        with patch("observability.logger.LOGS_DIR", tmp_path):
            with patch("observability.logger.CALLS_LOG", log_path):
                log_call(
                    model_id="claude-sonnet-4-20250514",
                    model_type="frontier",
                    input_tokens=100,
                    output_tokens=50,
                    input_cost_usd=0.0003,
                    output_cost_usd=0.00075,
                    latency_ms=1200.0,
                    pricing_source="litellm_json",
                    pricing_fetched_at="2026-05-22T00:00:00+00:00",
                )
                line = log_path.read_text().strip()
                record = json.loads(line)
                assert record["model_id"] == "claude-sonnet-4-20250514"
                assert record["input_tokens"] == 100
                assert "total_cost_usd" in record
                assert "cost_per_1k_tokens" in record
                assert "timestamp" in record

    def test_log_call_computes_total_cost(self, tmp_path):
        """total_cost_usd = input_cost + output_cost."""
        from observability.logger import log_call
        log_path = tmp_path / "calls.jsonl"
        with patch("observability.logger.LOGS_DIR", tmp_path):
            with patch("observability.logger.CALLS_LOG", log_path):
                log_call(
                    model_id="test-model",
                    model_type="frontier",
                    input_tokens=1000,
                    output_tokens=500,
                    input_cost_usd=0.003,
                    output_cost_usd=0.0075,
                    latency_ms=500.0,
                    pricing_source="fallback",
                    pricing_fetched_at="2026-05-22T00:00:00+00:00",
                )
                record = json.loads(log_path.read_text().strip())
                assert abs(record["total_cost_usd"] - 0.0105) < 1e-8

    def test_log_call_blocked_stores_hash_not_content(self, tmp_path):
        """Blocked calls store original_message_hash, not raw message content."""
        from observability.logger import log_call
        log_path = tmp_path / "calls.jsonl"
        with patch("observability.logger.LOGS_DIR", tmp_path):
            with patch("observability.logger.CALLS_LOG", log_path):
                log_call(
                    model_id="test-model",
                    model_type="frontier",
                    input_tokens=0,
                    output_tokens=0,
                    input_cost_usd=0.0,
                    output_cost_usd=0.0,
                    latency_ms=5.0,
                    pricing_source="fallback",
                    pricing_fetched_at="2026-05-22T00:00:00+00:00",
                    guardrail_blocked=True,
                    block_layer="input",
                    block_reason="prompt_injection",
                    block_stage="rebuff",
                    original_message_hash="abc123hash",
                )
                record = json.loads(log_path.read_text().strip())
                assert record["guardrail_blocked"] is True
                assert record["original_message_hash"] == "abc123hash"
                assert record["block_reason"] == "prompt_injection"

    def test_read_calls_returns_all_records(self, tmp_path):
        """read_calls() returns all valid JSONL records."""
        from observability.logger import log_call, read_calls
        log_path = tmp_path / "calls.jsonl"
        with patch("observability.logger.LOGS_DIR", tmp_path):
            with patch("observability.logger.CALLS_LOG", log_path):
                for _ in range(3):
                    log_call(
                        model_id="test", model_type="frontier",
                        input_tokens=10, output_tokens=5,
                        input_cost_usd=0.0, output_cost_usd=0.0,
                        latency_ms=100.0, pricing_source="fallback",
                        pricing_fetched_at="2026-05-22T00:00:00+00:00",
                    )
                records = read_calls()
                assert len(records) == 3

    def test_read_calls_empty_when_no_file(self, tmp_path):
        """read_calls() returns [] when calls.jsonl does not exist."""
        from observability.logger import read_calls
        with patch("observability.logger.CALLS_LOG", tmp_path / "nonexistent.jsonl"):
            assert read_calls() == []


class TestPricing:
    def test_hours_since_fetch_positive(self):
        """hours_since_fetch returns a positive float for a past timestamp."""
        from observability.pricing import hours_since_fetch
        result = hours_since_fetch("2026-01-01T00:00:00+00:00")
        assert result > 0

    def test_oss_cost_never_na(self):
        """compute_cost for OSS model returns (0.0, positive_float), never (0, 0)."""
        pytest.skip("Phase 3 — implement compute_cost first")

    def test_frontier_cost_uses_litellm_prices(self):
        """compute_cost for frontier model multiplies token counts by per-token prices."""
        pytest.skip("Phase 3 — implement compute_cost frontier path first")

    def test_fetch_pricing_falls_back_on_network_error(self):
        """fetch_pricing() returns fallback data when HTTP request fails."""
        pytest.skip("Phase 3 — implement fetch_pricing first")
