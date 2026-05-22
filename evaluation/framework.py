"""Own evaluation framework — orchestrates all 4 evaluation methods.

FR-EVL-06: EvalFramework class with the required public interface.

Three evaluation dimensions (see EVALUATION.md for full definitions):
  1. Hallucination Rate   — factual prompts + TruthfulQA + AdvGLUE
                            metrics: HallucinationMetric, judge rubric "hallucination"
  2. Bias & Harmful       — bias_sensitive prompts + BBQ benchmark
                            metrics: BiasMetric, ToxicityMetric, judge rubric "bias"/"safety"
  3. Content Safety       — adversarial prompts + Promptfoo redteam
                            metrics: GEval(jailbreak), GEval(refusal_quality), guardrail block rate

Score storage for both models:
  evaluation/results/model_scores.json  — aggregated per-model per-dimension scorecard
  evaluation/results/summary.csv        — raw (model, prompt, metric, score) rows
  evaluation/results/comparative.csv    — LLM-as-judge comparative results
  logs/calls.jsonl                      — runtime guardrail block events (content safety only)

Public interface:
  load_prompts()                → loads 45 custom + benchmark samples
  run_both_models(prompt)       → calls each agent, records response + metadata
  score_with_deepeval(...)      → runs DeepEval metrics
  score_with_judge(...)         → runs LLM-as-judge (full design with position swap)
  score_against_benchmark(...)  → exact match + semantic similarity
  aggregate(all_scores)         → writes summary.csv + model_scores.json, flags low_confidence
  report()                      → bar chart (3 dims × 2 models), radar chart, benchmark table
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).parent / "results"
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class EvalResult:
    model_id: str
    prompt_id: str
    source: str       # "custom_factual" | "custom_adversarial" | "custom_bias" | "truthfulqa" | "bbq" | "advglue"
    metric: str       # "hallucination" | "bias" | "toxicity" | "jailbreak_resistance" | "refusal_quality"
    score: float
    dimension: str    # "hallucination" | "bias_harmful" | "content_safety" — top-level assignment dimension
    low_confidence: bool = False
    reasoning: str = ""


class EvalFramework:
    """Orchestration layer over DeepEval + LLM-as-judge + public benchmarks."""

    def load_prompts(self) -> list[dict]:
        """
        Load all evaluation prompts:
          - 45 custom prompts from evaluation/prompts/*.json
          - Benchmark samples from evaluation/benchmarks/samples/*.json

        TODO (Phase 4): implement.
        """
        raise NotImplementedError("Phase 4 — load_prompts")

    def run_both_models(self, prompt: dict) -> tuple[dict, dict]:
        """
        Run both models on a single prompt dict.
        Returns (claude_result, qwen_result) where each result contains:
          {model_id, response_text, input_tokens, output_tokens, latency_ms}

        TODO (Phase 4): implement by calling agent.factory.run_agent for each model.
        """
        raise NotImplementedError("Phase 4 — run_both_models")

    def score_with_deepeval(self, response: str, prompt: dict) -> list[EvalResult]:
        """
        Run DeepEval metrics (Hallucination, Bias, Toxicity, GEval×2) on *response*.
        Returns one EvalResult per metric.

        TODO (Phase 4): implement using evaluation.deepeval_metrics.
        """
        raise NotImplementedError("Phase 4 — score_with_deepeval")

    def score_with_judge(
        self,
        response_a: str,
        response_b: str,
        prompt: dict,
        model_a_id: str = "claude-sonnet",
        model_b_id: str = "qwen-0.5b",
    ) -> dict:
        """
        Run LLM-as-judge with position swap + CoT + dimension-specific rubrics.
        Returns a ComparativeResult dict conforming to FR-EVL-05f schema.

        TODO (Phase 4): implement using evaluation.llm_judge.
        """
        raise NotImplementedError("Phase 4 — score_with_judge")

    def score_against_benchmark(self, response: str, expected_answer: str) -> dict:
        """
        Compute exact match + semantic similarity against ground truth.
        Returns {exact_match: bool, similarity: float}.

        TODO (Phase 4): implement using sentence-transformers or simple string match.
        """
        raise NotImplementedError("Phase 4 — score_against_benchmark")

    def aggregate(self, all_scores: list[EvalResult]) -> None:
        """
        Combine all scores, flag low_confidence, write:
          - results/summary.csv          (model, prompt_id, source, metric, score, dimension, low_confidence)
          - results/model_scores.json    (per-model per-dimension aggregated scorecard)

        model_scores.json schema defined in results/model_scores.schema.json.
        Low-confidence results are excluded from charts but retained in comparative.csv.

        TODO (Phase 4): implement.
        """
        raise NotImplementedError("Phase 4 — aggregate")

    def report(self) -> None:
        """
        Generate bar_chart.png (3 metrics × 2 models) and radar_chart.png.
        Calls evaluation.charts.generate_bar_chart() and generate_radar_chart().

        TODO (Phase 4): implement.
        """
        raise NotImplementedError("Phase 4 — report")
