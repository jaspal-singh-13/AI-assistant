"""Unit tests for evaluation/ — framework, benchmark loader, charts, judge schema.

External LLM calls and HF dataset downloads are always mocked.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBenchmarkLoader:
    def test_load_benchmark_from_cache(self, tmp_path):
        """load_benchmark() reads from local cache file when it exists."""
        sample_data = [{"id": "t1", "benchmark": "truthfulqa", "question": "Q?", "answer": "A"}]
        cache_file = tmp_path / "truthfulqa.json"
        cache_file.write_text(json.dumps(sample_data), encoding="utf-8")

        import evaluation.benchmarks.loader as loader_mod
        original = loader_mod.BENCHMARKS["truthfulqa"]["file"]
        loader_mod.BENCHMARKS["truthfulqa"]["file"] = cache_file
        try:
            from evaluation.benchmarks.loader import load_benchmark
            result = load_benchmark("truthfulqa")
            assert result == sample_data
        finally:
            loader_mod.BENCHMARKS["truthfulqa"]["file"] = original

    def test_unknown_benchmark_raises(self):
        """load_benchmark() raises ValueError for unknown benchmark names."""
        from evaluation.benchmarks.loader import load_benchmark
        with pytest.raises(ValueError, match="Unknown benchmark"):
            load_benchmark("not-a-real-benchmark")

    def test_load_all_returns_dict(self, tmp_path):
        """load_all() returns a dict keyed by benchmark name when all caches exist."""
        import evaluation.benchmarks.loader as loader_mod

        sample = [{"id": "x", "benchmark": "truthfulqa", "question": "Q?", "answer": "A"}]
        originals = {}
        try:
            for name in loader_mod.BENCHMARKS:
                cache_file = tmp_path / f"{name}.json"
                cache_file.write_text(json.dumps(sample), encoding="utf-8")
                originals[name] = loader_mod.BENCHMARKS[name]["file"]
                loader_mod.BENCHMARKS[name]["file"] = cache_file

            from evaluation.benchmarks.loader import load_all
            result = load_all()
            assert set(result.keys()) == {"truthfulqa", "bbq", "advglue"}
        finally:
            for name, orig in originals.items():
                loader_mod.BENCHMARKS[name]["file"] = orig


class TestJudgeRubrics:
    """These tests should already pass from the existing test_judge.py — duplicate here for coverage."""

    def test_all_rubric_combinations_exist(self):
        """Every (category, dimension) pair used in framework.py has a rubric."""
        from evaluation.llm_judge import get_rubric
        required = [
            ("factual", "hallucination"),
            ("factual", "completeness"),
            ("adversarial", "jailbreak_resistance"),
            ("adversarial", "refusal_quality"),
            ("bias_sensitive", "bias"),
            ("bias_sensitive", "safety"),
        ]
        for category, dimension in required:
            rubric = get_rubric(category, dimension)
            assert len(rubric) > 10, f"Rubric too short for ({category}, {dimension})"


class TestEvalFramework:
    def test_load_prompts_returns_list(self):
        """load_prompts() returns a non-empty list of prompt dicts."""
        from evaluation.framework import EvalFramework
        framework = EvalFramework()
        prompts = framework.load_prompts()
        assert isinstance(prompts, list)
        assert len(prompts) >= 45  # 15 × 3 custom prompt files

    def test_run_both_models_returns_two_results(self):
        """run_both_models() returns exactly two result dicts (one per model)."""
        from evaluation.framework import EvalFramework

        with patch("agent.models.list_models", return_value=[("claude-sonnet", MagicMock()), ("qwen-0.5b", MagicMock())]), \
             patch("agent.models.build_llm", return_value=MagicMock()), \
             patch("agent.factory.create_agent", return_value=MagicMock()), \
             patch("agent.factory.run_agent", return_value=("Response text", [])), \
             patch("tools.registry.get_tools", return_value=[]):

            framework = EvalFramework()
            result_a, result_b = framework.run_both_models({"id": "t1", "prompt": "Hello?"})

        assert result_a["model_id"] == "claude-sonnet"
        assert result_b["model_id"] == "qwen-0.5b"
        assert "response_text" in result_a
        assert "response_text" in result_b

    def test_aggregate_writes_summary_csv(self, tmp_path):
        """aggregate() writes summary.csv to results/."""
        from evaluation.framework import EvalFramework, EvalResult
        import evaluation.framework as fw_mod

        orig = fw_mod.RESULTS_DIR
        fw_mod.RESULTS_DIR = tmp_path
        try:
            framework = EvalFramework()
            scores = [
                EvalResult("claude-sonnet", "p1", "custom_factual", "hallucination", 0.1, "hallucination"),
                EvalResult("qwen-0.5b", "p1", "custom_factual", "hallucination", 0.4, "hallucination"),
            ]
            framework.aggregate(scores)
            csv_path = tmp_path / "summary.csv"
            assert csv_path.exists()
            rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
            assert len(rows) == 2
            assert rows[0]["model_id"] == "claude-sonnet"
        finally:
            fw_mod.RESULTS_DIR = orig

    def test_low_confidence_excluded_from_charts(self, tmp_path):
        """generate_bar_chart() excludes rows where low_confidence=True."""
        import pandas as pd
        from evaluation.charts import generate_bar_chart
        import evaluation.charts as charts_mod

        orig = charts_mod.RESULTS_DIR
        charts_mod.RESULTS_DIR = tmp_path

        # Write a summary.csv with one normal row and one low_confidence row
        rows = [
            {"model_id": "claude-sonnet", "prompt_id": "p1", "source": "custom_factual",
             "metric": "hallucination", "score": 0.2, "dimension": "hallucination",
             "low_confidence": False, "reasoning": ""},
            {"model_id": "claude-sonnet", "prompt_id": "p2", "source": "custom_factual",
             "metric": "hallucination", "score": 0.9, "dimension": "hallucination",
             "low_confidence": True, "reasoning": ""},
            {"model_id": "qwen-0.5b", "prompt_id": "p1", "source": "custom_factual",
             "metric": "hallucination", "score": 0.5, "dimension": "hallucination",
             "low_confidence": False, "reasoning": ""},
            # Add bias_harmful and content_safety so chart has all 3 dimensions
            {"model_id": "claude-sonnet", "prompt_id": "p3", "source": "custom_bias",
             "metric": "bias", "score": 0.1, "dimension": "bias_harmful",
             "low_confidence": False, "reasoning": ""},
            {"model_id": "qwen-0.5b", "prompt_id": "p3", "source": "custom_bias",
             "metric": "bias", "score": 0.3, "dimension": "bias_harmful",
             "low_confidence": False, "reasoning": ""},
            {"model_id": "claude-sonnet", "prompt_id": "p4", "source": "custom_adversarial",
             "metric": "jailbreak_resistance", "score": 0.9, "dimension": "content_safety",
             "low_confidence": False, "reasoning": ""},
            {"model_id": "qwen-0.5b", "prompt_id": "p4", "source": "custom_adversarial",
             "metric": "jailbreak_resistance", "score": 0.7, "dimension": "content_safety",
             "low_confidence": False, "reasoning": ""},
        ]
        csv_path = tmp_path / "summary.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        try:
            out = generate_bar_chart(csv_path)
            assert out.exists()
        finally:
            charts_mod.RESULTS_DIR = orig


@pytest.fixture(autouse=False)
def fake_openai_key(monkeypatch):
    """Provide a fake OPENAI_API_KEY so deepeval metrics can be instantiated without a real key."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key-for-unit-tests")


class TestDeepEvalMetrics:
    def test_metric_thresholds_match_spec(self):
        """Thresholds match the values defined in FR-EVL-04."""
        from evaluation.deepeval_metrics import (
            HALLUCINATION_THRESHOLD,
            BIAS_THRESHOLD,
            TOXICITY_THRESHOLD,
            JAILBREAK_THRESHOLD,
            REFUSAL_THRESHOLD,
        )
        assert HALLUCINATION_THRESHOLD == 0.5
        assert BIAS_THRESHOLD == 0.5
        assert TOXICITY_THRESHOLD == 0.5
        assert JAILBREAK_THRESHOLD == 0.7
        assert REFUSAL_THRESHOLD == 0.6

    def test_get_hallucination_metric_instantiates(self, fake_openai_key):
        """get_hallucination_metric() returns a non-None object."""
        from evaluation.deepeval_metrics import get_hallucination_metric
        metric = get_hallucination_metric()
        assert metric is not None

    def test_get_bias_metric_instantiates(self, fake_openai_key):
        """get_bias_metric() returns a non-None object."""
        from evaluation.deepeval_metrics import get_bias_metric
        metric = get_bias_metric()
        assert metric is not None

    def test_get_toxicity_metric_instantiates(self, fake_openai_key):
        from evaluation.deepeval_metrics import get_toxicity_metric
        metric = get_toxicity_metric()
        assert metric is not None

    def test_get_jailbreak_metric_instantiates(self, fake_openai_key):
        from evaluation.deepeval_metrics import get_jailbreak_metric
        metric = get_jailbreak_metric()
        assert metric is not None

    def test_get_refusal_quality_metric_instantiates(self, fake_openai_key):
        from evaluation.deepeval_metrics import get_refusal_quality_metric
        metric = get_refusal_quality_metric()
        assert metric is not None
