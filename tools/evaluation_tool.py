"""Evaluation summary tool — read-only access to evaluation results.

Returns per-model benchmark scores from evaluation/results/model_scores.json.
Read-only: no writes, no network calls, no eval runs triggered.
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

SCORES_FILE = Path(__file__).parent.parent / "evaluation" / "results" / "model_scores.json"


@tool
def get_evaluation_summary(model_id: str = "") -> str:
    """Return evaluation benchmark scores for both models.

    Shows hallucination rate, bias & harmful rate, and content safety pass-rate
    from the most recent eval run. Pass a model_id substring to filter to a
    specific model (e.g. 'claude', 'qwen'). Use when the user asks about
    hallucination, bias, toxicity, safety, jailbreak resistance, or any
    benchmark / quality score. Read-only — does not trigger an evaluation run.
    Run `make eval` (CLI) or use the Evaluation page to generate results first.
    """
    if not SCORES_FILE.exists():
        return (
            "No evaluation results found. Run `make eval` from the CLI or use the "
            "Evaluation page to generate benchmark scores."
        )

    try:
        data = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"Could not read evaluation results: {exc}"

    generated_at = data.get("generated_at", "unknown")
    models_data: dict = data.get("models", {})

    if not models_data:
        return "Evaluation results file exists but contains no model data."

    if model_id:
        models_data = {k: v for k, v in models_data.items() if model_id.lower() in k.lower()}
        if not models_data:
            return f"No evaluation results found matching model_id filter: {model_id!r}"

    _NEGATIVE_DIMS = {"hallucination", "bias_harmful"}
    _DIM_LABELS = {
        "hallucination": "Hallucination",
        "bias_harmful": "Bias & Harmful",
        "content_safety": "Content Safety",
    }

    lines = [f"Evaluation Summary (run: {generated_at})\n{'='*50}"]
    for mid, dim_scores in models_data.items():
        lines.append(f"\nModel: {mid}")
        for dim, label in _DIM_LABELS.items():
            dim_data = dim_scores.get(dim, {})
            pass_rate = dim_data.get("pass_rate", None)
            if pass_rate is None:
                lines.append(f"  {label:22}: n/a")
                continue
            if dim in _NEGATIVE_DIMS:
                display = f"{round((1 - pass_rate) * 100, 1)}% failure rate (lower is better)"
            else:
                display = f"{round(pass_rate * 100, 1)}% pass rate (higher is better)"
            low_conf = dim_data.get("low_confidence_excluded", 0)
            suffix = f"  ⚠ {low_conf} low-confidence excluded" if low_conf else ""
            lines.append(f"  {label:22}: {display}{suffix}")

    return "\n".join(lines)
