"""Evaluation entry point.

Usage:
  python evaluation/run_eval.py [--seed 42] [--models claude-sonnet qwen-0.5b]

FR-EVL-06 + NFR-REP-02 (--seed for reproducibility).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AI assistant evaluation suite")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["claude-sonnet", "qwen-0.5b"],
        help="Model keys to evaluate",
    )
    parser.add_argument(
        "--skip-benchmarks",
        action="store_true",
        help="Skip public benchmark loading (faster local runs)",
    )
    parser.add_argument(
        "--prompt-category",
        choices=["factual", "adversarial", "bias_sensitive", "all"],
        default="all",
        help="Limit evaluation to a specific prompt category",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"Seed: {args.seed} | Models: {args.models}")

    # TODO (Phase 4): implement full pipeline
    # from evaluation.framework import EvalFramework
    # framework = EvalFramework(seed=args.seed)
    # prompts = framework.load_prompts()
    # all_scores = []
    # for prompt in prompts:
    #     claude_result, qwen_result = framework.run_both_models(prompt)
    #     scores = framework.score_with_deepeval(claude_result["response"], prompt)
    #     scores += framework.score_with_deepeval(qwen_result["response"], prompt)
    #     comparative = framework.score_with_judge(claude_result["response"], qwen_result["response"], prompt)
    #     all_scores.extend(scores)
    # framework.aggregate(all_scores)
    # framework.report()
    # print("Evaluation complete. Results written to evaluation/results/")

    raise NotImplementedError("Phase 4 — run_eval main()")


if __name__ == "__main__":
    main()
