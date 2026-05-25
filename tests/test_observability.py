"""Unit tests for observability/logger.py and observability/pricing.py.

External HTTP calls (LiteLLM pricing fetch) are always mocked.
File system writes use tmp_path fixture.
"""

from __future__ import annotations

import json
import logging
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
        """total_cost_usd = llm_cost + guardrail_cost (no guardrail → same as llm_cost)."""
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
                assert abs(record["llm_cost_usd"] - 0.0105) < 1e-8
                assert abs(record["guardrail_cost_usd"] - 0.0) < 1e-8
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


class TestAppLogger:
    def setup_method(self):
        """Clear root logger handlers before each test for isolation."""
        logging.getLogger().handlers.clear()

    def test_configure_logging_installs_handlers(self, tmp_path):
        """configure_logging() installs a RotatingFileHandler on the root logger."""
        import logging.handlers as lh
        from observability.logger import configure_logging
        with patch("observability.logger.APP_LOG", tmp_path / "app.log"):
            with patch("observability.logger.LOGS_DIR", tmp_path):
                configure_logging(level="DEBUG")
                root = logging.getLogger()
                handler_types = [type(h) for h in root.handlers]
                assert lh.RotatingFileHandler in handler_types

    def test_configure_logging_is_idempotent(self, tmp_path):
        """Calling configure_logging() twice must not add a second RotatingFileHandler."""
        import logging.handlers as lh
        from observability.logger import configure_logging
        with patch("observability.logger.APP_LOG", tmp_path / "app.log"):
            with patch("observability.logger.LOGS_DIR", tmp_path):
                configure_logging()
                n_rotating = sum(
                    1 for h in logging.getLogger().handlers
                    if isinstance(h, lh.RotatingFileHandler)
                )
                configure_logging()
                n_rotating_after = sum(
                    1 for h in logging.getLogger().handlers
                    if isinstance(h, lh.RotatingFileHandler)
                )
                assert n_rotating == n_rotating_after == 1

    def test_log_duration_logs_elapsed(self, tmp_path, caplog):
        """log_duration emits a 'done in' DEBUG message on normal exit."""
        from observability.logger import log_duration, get_logger
        log = get_logger("test.duration")
        with caplog.at_level(logging.DEBUG, logger="test.duration"):
            with log_duration(log, "my_operation"):
                pass
        messages = [r.message for r in caplog.records]
        assert any("my_operation" in m for m in messages)
        assert any("done in" in m for m in messages)

    def test_log_duration_logs_on_exception(self, caplog):
        """log_duration emits an ERROR record when the block raises."""
        from observability.logger import log_duration, get_logger
        log = get_logger("test.exc")
        with caplog.at_level(logging.ERROR, logger="test.exc"):
            with pytest.raises(ValueError):
                with log_duration(log, "bad_op"):
                    raise ValueError("boom")
        assert any("raised" in r.message for r in caplog.records)


class TestPricing:
    def test_hours_since_fetch_positive(self):
        """hours_since_fetch returns a positive float for a past timestamp."""
        from observability.pricing import hours_since_fetch
        result = hours_since_fetch("2026-01-01T00:00:00+00:00")
        assert result > 0

    def test_oss_cost_never_na(self):
        """compute_cost for OSS model returns (0.0, positive_float) using Modal A10G rate."""
        from observability.pricing import compute_cost, MODAL_A10G_PER_SECOND_USD
        latency_ms = 5000.0
        input_cost, output_cost = compute_cost(
            model_id="Qwen/Qwen2.5-7B-Instruct",
            input_tokens=100,
            output_tokens=50,
            pricing={},
            model_type="oss",
            latency_ms=latency_ms,
        )
        assert input_cost == 0.0
        expected = (latency_ms / 1_000) * MODAL_A10G_PER_SECOND_USD
        assert abs(output_cost - expected) < 1e-10

    def test_compute_guardrail_cost_llamaguard_tokens(self):
        """compute_guardrail_cost charges Claude Haiku token rates for LlamaGuard calls."""
        from guardrails.llamaguard import GuardResult
        from observability.pricing import compute_guardrail_cost

        pricing = {
            "claude-haiku-4-5-20251001": {
                "input_cost_per_token": 0.0000008,
                "output_cost_per_token": 0.000004,
            }
        }
        input_guard = GuardResult(blocked=False, latency_ms=300.0, stages=[], input_tokens=50, output_tokens=3)
        output_guard = GuardResult(blocked=False, latency_ms=280.0, stages=[], input_tokens=48, output_tokens=2)

        cost = compute_guardrail_cost(input_guard, output_guard, pricing)
        expected = (50 + 48) * 0.0000008 + (3 + 2) * 0.000004
        assert abs(cost - expected) < 1e-10

    def test_compute_guardrail_cost_nemo_presidio_cpu(self):
        """compute_guardrail_cost adds Modal CPU cost for NeMo and Presidio stages."""
        from guardrails.llamaguard import GuardResult
        from observability.pricing import compute_guardrail_cost, MODAL_CPU_PER_SECOND_USD

        pricing = {"claude-haiku-4-5-20251001": {"input_cost_per_token": 0.0, "output_cost_per_token": 0.0}}

        nemo_latency = 200.0   # ms
        presidio_latency = 30.0  # ms
        input_guard = GuardResult(
            blocked=False, latency_ms=250.0,
            stages=[
                {"name": "NeMo Guardrails", "passed": True, "latency_ms": nemo_latency, "skipped": False},
                {"name": "Presidio PII", "passed": True, "latency_ms": presidio_latency, "skipped": False},
            ],
        )
        output_guard = GuardResult(blocked=False, latency_ms=180.0, stages=[
            {"name": "NeMo Guardrails", "passed": True, "latency_ms": nemo_latency, "skipped": False},
        ])

        cost = compute_guardrail_cost(input_guard, output_guard, pricing)
        expected = (nemo_latency + presidio_latency + nemo_latency) / 1_000 * MODAL_CPU_PER_SECOND_USD
        assert abs(cost - expected) < 1e-12

    def test_log_call_total_includes_guardrail_cost(self, tmp_path):
        """total_cost_usd = llm_cost + guardrail_cost_usd when guardrail_cost_usd is provided."""
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
                    guardrail_cost_usd=0.0005,
                    latency_ms=500.0,
                    pricing_source="fallback",
                    pricing_fetched_at="2026-05-22T00:00:00+00:00",
                )
                record = json.loads(log_path.read_text().strip())
                assert abs(record["llm_cost_usd"] - 0.0105) < 1e-8
                assert abs(record["guardrail_cost_usd"] - 0.0005) < 1e-8
                assert abs(record["total_cost_usd"] - 0.011) < 1e-8

    def test_frontier_cost_uses_litellm_prices(self):
        """compute_cost for frontier model multiplies token counts by per-token prices."""
        from observability.pricing import compute_cost
        pricing = {
            "claude-sonnet-4-20250514": {
                "input_cost_per_token": 0.000003,
                "output_cost_per_token": 0.000015,
            }
        }
        input_cost, output_cost = compute_cost(
            model_id="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            pricing=pricing,
            model_type="frontier",
        )
        assert abs(input_cost - 0.003) < 1e-8
        assert abs(output_cost - 0.0075) < 1e-8

    def test_fetch_pricing_falls_back_on_network_error(self):
        """fetch_pricing() returns fallback data when HTTP request fails."""
        import requests
        from unittest.mock import patch
        from observability.pricing import fetch_pricing

        with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            data, source, fetched_at = fetch_pricing()
        assert source == "fallback"
        assert isinstance(data, dict)
        assert len(fetched_at) > 0
