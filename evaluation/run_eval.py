"""Evaluation entry point.

Usage:
  python evaluation/run_eval.py [--seed 42] [--models claude-sonnet qwen-0.5b]
                                [--workers 3] [--skip-judge] [--skip-benchmarks]
                                [--prompt-category all]

FR-EVL-06 + NFR-REP-02 (--seed for reproducibility).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

_CACHE_FILE = Path(__file__).parent / "results" / "_partial_cache.json"


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
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip LLM-as-judge (faster, avoids extra API calls)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of prompts to process concurrently (default: 3)",
    )
    return parser.parse_args()


def _load_cache() -> dict:
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    print(f"Seed: {args.seed} | Models: {args.models} | Workers: {args.workers}")

    from evaluation.framework import EvalFramework, EvalResult

    framework = EvalFramework()

    print("Loading prompts...")
    all_prompts = framework.load_prompts()

    if args.prompt_category != "all":
        all_prompts = [p for p in all_prompts if p.get("category") == args.prompt_category]

    if args.skip_benchmarks:
        all_prompts = [p for p in all_prompts if p.get("benchmark") is None and p.get("source") is None]

    print(f"Loaded {len(all_prompts)} prompts.")

    cache = _load_cache()
    all_scores: list[EvalResult] = []
    comparatives: list[dict] = []

    # Locks for shared mutable state
    results_lock = threading.Lock()
    # Serialises local (OSS) model inference so Qwen GPU calls don't overlap
    qwen_lock = threading.Lock()

    total = len(all_prompts)

    def _process_prompt(idx: int, prompt: dict) -> None:
        pid = prompt.get("id", f"prompt_{idx}")

        with results_lock:
            if pid in cache:
                cached = cache[pid]
                for s in cached.get("scores", []):
                    all_scores.append(EvalResult(**s))
                if cached.get("comparative"):
                    comparatives.append(cached["comparative"])
                print(f"  [{idx+1}/{total}] {pid} (cached)")
                return

        print(f"  [{idx+1}/{total}] {pid}")

        try:
            claude_result, qwen_result = framework.run_both_models(prompt, qwen_lock)
        except Exception as exc:
            import traceback
            print(f"    run_both_models failed: {exc!r}")
            traceback.print_exc()
            return

        prompt_scores: list[EvalResult] = []

        # Score both model responses concurrently
        def _score_model(result: dict) -> list[EvalResult]:
            model_id = result["model_id"]
            try:
                scores = framework.score_with_deepeval(result["response_text"], prompt)
                for s in scores:
                    s.model_id = model_id
                return scores
            except Exception as exc:
                print(f"    deepeval failed for {model_id}: {exc}")
                return []

        with ThreadPoolExecutor(max_workers=2) as ex:
            score_futs = [ex.submit(_score_model, r) for r in (claude_result, qwen_result)]
        for fut in score_futs:
            prompt_scores.extend(fut.result())

        comparative: dict | None = None
        if not args.skip_judge:
            try:
                comparative = framework.score_with_judge(
                    claude_result["response_text"],
                    qwen_result["response_text"],
                    prompt,
                    claude_result["model_id"],
                    qwen_result["model_id"],
                )
            except Exception as exc:
                print(f"    judge failed: {exc}")

        with results_lock:
            all_scores.extend(prompt_scores)
            if comparative:
                comparatives.append(comparative)
            cache[pid] = {
                "scores": [dataclasses.asdict(s) for s in prompt_scores],
                "comparative": comparative,
            }
            _save_cache(cache)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_process_prompt, i, p): i for i, p in enumerate(all_prompts)}
        for fut in as_completed(futs):
            exc = fut.exception()
            if exc:
                print(f"  prompt worker raised: {exc!r}")

    print("Aggregating results...")
    framework.aggregate(all_scores)

    # Write comparative.csv
    if comparatives:
        import csv
        comp_path = Path(__file__).parent / "results" / "comparative.csv"
        fieldnames = list(comparatives[0].keys())
        with comp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comparatives)

    print("Generating charts...")
    try:
        framework.report()
    except Exception as exc:
        print(f"  chart generation failed (non-fatal): {exc}")

    # Sync to LangSmith if configured
    try:
        from evaluation.langsmith_sync import sync_scores_to_langsmith
        sync_scores_to_langsmith(all_scores)
    except Exception as exc:
        print(f"  LangSmith sync failed (non-fatal): {exc}")

    print("Evaluation complete. Results written to evaluation/results/")

    # Clean up partial cache on success
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()


if __name__ == "__main__":
    main()
