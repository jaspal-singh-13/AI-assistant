"""Unit tests for evaluation/ — framework, benchmark loader, charts, judge schema.

External LLM calls and HF dataset downloads are always mocked.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestBenchmarkLoader:
    def test_load_benchmark_from_cache(self, tmp_path):
        """load_benchmark() reads from local cache file when it exists."""
        import json
        from unittest.mock import patch

        sample_data = [{"id": "t1", "benchmark": "truthfulqa", "question": "Q?", "answer": "A"}]
        cache_file = tmp_path / "truthfulqa.json"
        cache_file.write_text(json.dumps(sample_data), encoding="utf-8")

        with patch.dict(
            "evaluation.benchmarks.loader.BENCHMARKS",
            {"truthfulqa": {**pytest.importorskip("evaluation.benchmarks.loader").BENCHMARKS["truthfulqa"], "file": cache_file}},
        ):
            from evaluation.benchmarks.loader import load_benchmark
            result = load_benchmark("truthfulqa")
            assert result == sample_data

    def test_unknown_benchmark_raises(self):
        """load_benchmark() raises ValueError for unknown benchmark names."""
        from evaluation.benchmarks.loader import load_benchmark
        with pytest.raises(ValueError, match="Unknown benchmark"):
            load_benchmark("not-a-real-benchmark")

    def test_load_all_returns_dict(self, tmp_path):
        """load_all() returns a dict with all three benchmark keys."""
        pytest.skip("Phase 4 — needs cache files to exist")


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
        pytest.skip("Phase 4 — implement load_prompts first")

    def test_run_both_models_returns_two_results(self):
        """run_both_models() returns exactly two result dicts (one per model)."""
        pytest.skip("Phase 4 — implement run_both_models first")

    def test_aggregate_writes_summary_csv(self, tmp_path):
        """aggregate() writes summary.csv to results/."""
        pytest.skip("Phase 4 — implement aggregate first")

    def test_low_confidence_excluded_from_charts(self):
        """generate_bar_chart() excludes rows where low_confidence=True."""
        pytest.skip("Phase 4 — implement charts.py first")


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

    def test_get_hallucination_metric_instantiates(self):
        """get_hallucination_metric() returns a non-None object."""
        pytest.skip("Phase 4 — needs deepeval installed")
