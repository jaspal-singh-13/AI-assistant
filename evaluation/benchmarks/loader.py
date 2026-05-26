"""Public benchmark loader — TruthfulQA, BBQ, AdvGLUE via HuggingFace datasets.

FR-EVL-02: 30 TruthfulQA + 30 BBQ + 20 AdvGLUE samples.
FR §15.3: Samples cached to evaluation/benchmarks/samples/ — works offline once cached.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from observability.logger import get_logger

logger = get_logger(__name__)

SAMPLES_DIR = Path(__file__).parent / "samples"

BENCHMARKS = {
    "truthfulqa": {
        "hf_id": "truthfulqa/truthful_qa",
        "config": "multiple_choice",
        "split": "validation",
        "n_samples": 30,
        "file": SAMPLES_DIR / "truthfulqa.json",
    },
    "bbq": {
        # heegyu/bbq uses a legacy bbq.py script; datasets>=4.0 removed script execution.
        # Load from the auto-generated parquet branch instead.
        "hf_id": "heegyu/bbq",
        "config": None,
        "split": "test",
        "revision": "refs/convert/parquet",
        "n_samples": 30,
        "file": SAMPLES_DIR / "bbq.json",
    },
    "advglue": {
        "hf_id": "AI-Secure/adv_glue",
        "config": "adv_sst2",
        "split": "validation",
        "n_samples": 20,
        "file": SAMPLES_DIR / "advglue.json",
    },
}


def load_benchmark(name: str, seed: int = 42) -> list[dict]:
    """
    Load *n_samples* from benchmark *name*.
    Uses local cache if available; downloads from HuggingFace otherwise.

    Returns list of normalised sample dicts:
      {id, benchmark, question, choices?, answer, context?}
    """
    cfg = BENCHMARKS.get(name)
    if cfg is None:
        raise ValueError(f"Unknown benchmark: {name!r}. Choose from {list(BENCHMARKS)}")

    cache_file: Path = cfg["file"]
    if cache_file.exists():
        logger.debug("load_benchmark | cache hit | name=%s", name)
        return json.loads(cache_file.read_text(encoding="utf-8"))

    logger.info("load_benchmark | downloading | name=%s hf_id=%s", name, cfg["hf_id"])
    from datasets import load_dataset  # type: ignore[import]

    revision = cfg.get("revision")
    ds = load_dataset(cfg["hf_id"], cfg["config"], split=cfg["split"], revision=revision)
    samples = _normalise(name, ds, cfg["n_samples"], seed)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("load_benchmark | cached | name=%s n=%d", name, len(samples))
    return samples


def load_all(seed: int = 42) -> dict[str, list[dict]]:
    """Load all three benchmarks and return as {name: samples} dict."""
    return {name: load_benchmark(name, seed=seed) for name in BENCHMARKS}


def _normalise(name: str, ds, n_samples: int, seed: int) -> list[dict]:
    """Convert a HuggingFace dataset split to the normalised sample format."""
    rng = random.Random(seed)
    indices = list(range(len(ds)))
    rng.shuffle(indices)
    indices = indices[:n_samples]

    if name == "truthfulqa":
        return [_normalise_truthfulqa(ds[i], i) for i in indices]
    if name == "bbq":
        return [_normalise_bbq(ds[i], i) for i in indices]
    if name == "advglue":
        return [_normalise_advglue(ds[i], i) for i in indices]
    raise ValueError(f"No normaliser for {name!r}")


def _normalise_truthfulqa(row: dict, idx: int) -> dict:
    mc = row.get("mc1_targets", {})
    choices = mc.get("choices", [])
    labels = mc.get("labels", [])
    answer = choices[labels.index(1)] if 1 in labels else choices[0] if choices else ""
    return {
        "id": f"truthfulqa_{idx:04d}",
        "benchmark": "truthfulqa",
        "question": row.get("question", ""),
        "choices": choices,
        "answer": answer,
        "category": row.get("category", ""),
    }


def _normalise_bbq(row: dict, idx: int) -> dict:
    label = row.get("label", 0)
    answers = [row.get("ans0", ""), row.get("ans1", ""), row.get("ans2", "")]
    answer = answers[label] if 0 <= label < len(answers) else answers[0]
    return {
        "id": f"bbq_{idx:04d}",
        "benchmark": "bbq",
        "question": row.get("question", ""),
        "context": row.get("context", ""),
        "choices": answers,
        "answer": answer,
        "category": row.get("category", ""),
    }


def _normalise_advglue(row: dict, idx: int) -> dict:
    label = row.get("label", 0)
    sentiment = "positive" if label == 1 else "negative"
    return {
        "id": f"advglue_{idx:04d}",
        "benchmark": "advglue",
        "question": f"What is the sentiment of this sentence: {row.get('sentence', '')}",
        "answer": sentiment,
        "context": row.get("sentence", ""),
    }
