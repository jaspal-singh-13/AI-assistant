"""Evaluation entry point.

Usage:
  python evaluation/run_eval.py [--seed 42] [--models claude-sonnet qwen-0.5b]
                                [--workers 3] [--skip-judge] [--skip-benchmarks]
                                [--prompt-category all] [--light]
                                [--prompt-ids factual_001 adversarial_003 ...]

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

from observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

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
    parser.add_argument(
        "--light",
        action="store_true",
        help="Light mode: keep only 3 prompts per category (9 total). Ideal for quick smoke-tests.",
    )
    parser.add_argument(
        "--prompt-ids",
        nargs="*",
        default=None,
        help="Run only specific prompt IDs (space-separated). Overrides --light and --prompt-category.",
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
    logger.info("=== eval pipeline start | seed=%d models=%s workers=%d light=%s ===",
                args.seed, args.models, args.workers, args.light)

    from evaluation.framework import EvalFramework, EvalResult

    framework = EvalFramework()

    logger.info("load_prompts | start")
    all_prompts = framework.load_prompts()

    if args.prompt_category != "all":
        all_prompts = [p for p in all_prompts if p.get("category") == args.prompt_category]

    if args.skip_benchmarks:
        all_prompts = [p for p in all_prompts if p.get("benchmark") is None and p.get("source") is None]

    if args.light:
        import random
        from collections import defaultdict
        rng = random.Random(args.seed)
        by_category: dict[str, list] = defaultdict(list)
        for p in all_prompts:
            by_category[p.get("category", "unknown")].append(p)
        all_prompts = []
        for cat, prompts in sorted(by_category.items()):
            rng.shuffle(prompts)
            all_prompts.extend(prompts[:3])

    logger.info("load_prompts | done | n=%d%s", len(all_prompts), " [light]" if args.light else "")

    if args.prompt_ids:
        id_set = set(args.prompt_ids)
        all_prompts = [p for p in all_prompts if p.get("id") in id_set]
        logger.info("load_prompts | filtered by --prompt-ids | n=%d", len(all_prompts))

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
                logger.debug("prompt | cached | [%d/%d] %s", idx + 1, total, pid)
                return

        logger.info("prompt | [%d/%d] %s", idx + 1, total, pid)

        try:
            claude_result, qwen_result = framework.run_both_models(prompt, qwen_lock)
        except Exception:
            logger.error("run_both_models | failed | pid=%s", pid, exc_info=True)
            return

        prompt_scores: list[EvalResult] = []

        # Score both model responses concurrently
        def _score_model(result: dict) -> list[EvalResult]:
            model_id = result["model_id"]
            try:
                scores = framework.score_with_deepeval(result["response_text"], prompt)
                for s in scores:
                    s.model_id = model_id
                logger.debug("deepeval | ok | model=%s pid=%s scores=%d", model_id, pid, len(scores))
                return scores
            except Exception:
                logger.warning("deepeval | failed | model=%s pid=%s", model_id, pid, exc_info=True)
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
                logger.debug("judge | ok | pid=%s low_confidence=%s", pid, comparative.get("low_confidence"))
            except Exception:
                logger.warning("judge | failed | pid=%s", pid, exc_info=True)

        with results_lock:
            all_scores.extend(prompt_scores)
            if comparative:
                comparatives.append(comparative)
            cache[pid] = {
                "scores": [dataclasses.asdict(s) for s in prompt_scores],
                "comparative": comparative,
            }
            _save_cache(cache)

    logger.info("processing %d prompts with %d workers", len(all_prompts), args.workers)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_process_prompt, i, p): i for i, p in enumerate(all_prompts)}
        for fut in as_completed(futs):
            exc = fut.exception()
            if exc:
                logger.error("prompt worker raised: %r", exc)

    logger.info("aggregate | start | total_scores=%d comparatives=%d",
                len(all_scores), len(comparatives))
    framework.aggregate(all_scores)
    logger.info("aggregate | done | summary.csv + model_scores.json written")

    # Write comparative.csv
    if comparatives:
        import csv
        comp_path = Path(__file__).parent / "results" / "comparative.csv"
        fieldnames = list(comparatives[0].keys())
        with comp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comparatives)
        logger.info("comparative.csv written | rows=%d", len(comparatives))

    logger.info("charts | generating")
    try:
        framework.report()
        logger.info("charts | done")
    except Exception:
        logger.warning("charts | generation failed (non-fatal)", exc_info=True)

    # Sync to LangSmith if configured
    try:
        from evaluation.langsmith_sync import sync_scores_to_langsmith
        sync_scores_to_langsmith(all_scores)
    except Exception:
        logger.warning("LangSmith sync failed (non-fatal)", exc_info=True)

    logger.info("=== eval pipeline done | results written to evaluation/results/ ===")

    # Clean up partial cache on success
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()


if __name__ == "__main__":
    main()
