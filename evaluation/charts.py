"""Chart generation — bar chart and radar chart from evaluation results.

FR-EVL-06 report(): produces results/bar_chart.png and results/radar_chart.png.
Low-confidence results are excluded from all charts (FR-EVL-05e).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS_DIR = Path(__file__).parent / "results"

_DIMENSION_LABELS = {
    "hallucination": "Hallucination",
    "bias_harmful": "Bias & Harmful",
    "content_safety": "Content Safety",
}

_MODEL_COLORS = {
    0: "#4C72B0",  # blue — claude
    1: "#DD8452",  # orange — qwen
}


def generate_bar_chart(summary_csv: Path | None = None) -> Path:
    """
    Generate a bar chart: 3 metrics × 2 models from summary.csv.

    Excludes low_confidence=True rows.
    Saves to results/bar_chart.png and returns the path.
    """
    csv_path = summary_csv or RESULTS_DIR / "summary.csv"
    df = pd.read_csv(csv_path)

    # Normalise the low_confidence column which may be "True"/"False" strings
    df["low_confidence"] = df["low_confidence"].astype(str).str.lower() == "true"
    df = df[~df["low_confidence"]]

    models = df["model_id"].unique().tolist()
    dimensions = ["hallucination", "bias_harmful", "content_safety"]
    dim_labels = [_DIMENSION_LABELS[d] for d in dimensions]

    # Average score per (model, dimension)
    avg = (
        df.groupby(["model_id", "dimension"])["score"]
        .mean()
        .reset_index()
    )

    x = np.arange(len(dimensions))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))

    for i, model in enumerate(models):
        model_data = avg[avg["model_id"] == model]
        scores = [
            model_data[model_data["dimension"] == d]["score"].values[0]
            if len(model_data[model_data["dimension"] == d]) > 0 else 0.0
            for d in dimensions
        ]
        offset = (i - (len(models) - 1) / 2) * width
        bars = ax.bar(x + offset, scores, width, label=model, color=_MODEL_COLORS.get(i, "#888"))
        for bar, score in zip(bars, scores):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{score:.2f}",
                ha="center", va="bottom", fontsize=8,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(dim_labels)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Average Score")
    ax.set_title("Evaluation Results by Dimension")
    ax.legend()
    fig.tight_layout()

    out_path = RESULTS_DIR / "bar_chart.png"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def generate_radar_chart(summary_csv: Path | None = None) -> Path:
    """
    Generate a radar/spider chart showing overall capability across all dimensions.

    Saves to results/radar_chart.png and returns the path.
    """
    csv_path = summary_csv or RESULTS_DIR / "summary.csv"
    df = pd.read_csv(csv_path)
    df["low_confidence"] = df["low_confidence"].astype(str).str.lower() == "true"
    df = df[~df["low_confidence"]]

    models = df["model_id"].unique().tolist()
    dimensions = ["hallucination", "bias_harmful", "content_safety"]
    labels = [_DIMENSION_LABELS[d] for d in dimensions]

    avg = (
        df.groupby(["model_id", "dimension"])["score"]
        .mean()
        .reset_index()
    )

    num_vars = len(dimensions)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})

    for i, model in enumerate(models):
        model_data = avg[avg["model_id"] == model]
        values = [
            model_data[model_data["dimension"] == d]["score"].values[0]
            if len(model_data[model_data["dimension"] == d]) > 0 else 0.0
            for d in dimensions
        ]
        values += values[:1]  # close polygon
        color = _MODEL_COLORS.get(i, "#888")
        ax.plot(angles, values, "o-", linewidth=2, color=color, label=model)
        ax.fill(angles, values, alpha=0.2, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Overall Capability Radar", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    fig.tight_layout()

    out_path = RESULTS_DIR / "radar_chart.png"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
