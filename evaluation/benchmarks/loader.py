"""Public benchmark loader — TruthfulQA, BBQ, AdvGLUE via HuggingFace datasets.

FR-EVL-02: 30 TruthfulQA + 30 BBQ + 20 AdvGLUE samples.
FR §15.3: Samples cached to evaluation/benchmarks/samples/ — works offline once cached.
"""

from __future__ import annotations

import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / "samples"

BENCHMARKS = {
    "truthfulqa": {
        "hf_id": "truthful_qa",
        "config": "multiple_choice",
        "split": "validation",
        "n_samples": 30,
        "file": SAMPLES_DIR / "truthfulqa.json",
    },
    "bbq": {
        "hf_id": "heegyu/bbq",
        "config": None,
        "split": "test",
        "n_samples": 30,
        "file": SAMPLES_DIR / "bbq.json",
    },
    "advglue": {
        "hf_id": "adv_glue",
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

    TODO (Phase 4): implement with HF datasets + cache write.
    """
    cfg = BENCHMARKS.get(name)
    if cfg is None:
        raise ValueError(f"Unknown benchmark: {name!r}. Choose from {list(BENCHMARKS)}")

    cache_file: Path = cfg["file"]
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    # TODO: download from HF, normalise, save to cache
    # from datasets import load_dataset
    # ds = load_dataset(cfg["hf_id"], cfg["config"], split=cfg["split"])
    # samples = _normalise(name, ds, cfg["n_samples"], seed)
    # cache_file.parent.mkdir(parents=True, exist_ok=True)
    # cache_file.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    # return samples
    raise NotImplementedError("Phase 4 — load_benchmark (download path)")


def load_all(seed: int = 42) -> dict[str, list[dict]]:
    """Load all three benchmarks and return as {name: samples} dict."""
    return {name: load_benchmark(name, seed=seed) for name in BENCHMARKS}
