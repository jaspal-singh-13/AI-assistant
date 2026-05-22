"""Chart generation — bar chart and radar chart from evaluation results.

FR-EVL-06 report(): produces results/bar_chart.png and results/radar_chart.png.
Low-confidence results are excluded from all charts (FR-EVL-05e).
"""

from __future__ import annotations

from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

# TODO (Phase 4): uncomment once matplotlib + pandas installed
# import matplotlib.pyplot as plt
# import matplotlib
# matplotlib.use("Agg")  # non-interactive backend for server-side rendering
# import pandas as pd
# import numpy as np


def generate_bar_chart(summary_csv: Path | None = None) -> Path:
    """
    Generate a bar chart: 3 metrics × 2 models from summary.csv.

    Excludes low_confidence=True rows.
    Saves to results/bar_chart.png and returns the path.

    TODO (Phase 4): implement.
    """
    # df = pd.read_csv(summary_csv or RESULTS_DIR / "summary.csv")
    # df = df[~df["low_confidence"]]
    # ... pivot and plot ...
    raise NotImplementedError("Phase 4 — generate_bar_chart")


def generate_radar_chart(summary_csv: Path | None = None) -> Path:
    """
    Generate a radar/spider chart showing overall capability across all dimensions.

    Saves to results/radar_chart.png and returns the path.

    TODO (Phase 4): implement.
    """
    raise NotImplementedError("Phase 4 — generate_radar_chart")
