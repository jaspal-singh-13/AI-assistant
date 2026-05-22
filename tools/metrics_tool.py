"""Metrics tool — agent self-awareness via calls.jsonl.

FR-TOOL-05: Reads logs/calls.jsonl and returns summary statistics.
Makes the agent self-aware of its own performance (latency, cost, safety block rate).
Natural language queries like "how fast are you?" trigger this tool.
"""

from __future__ import annotations

import json
from pathlib import Path

CALLS_LOG = Path(__file__).parent.parent / "logs" / "calls.jsonl"

# TODO (Phase 1): uncomment @tool decorator once langchain is installed
# from langchain_core.tools import tool
#
# @tool
def get_metrics() -> str:
    """Return current performance statistics from the call log."""
    if not CALLS_LOG.exists() or CALLS_LOG.stat().st_size == 0:
        return "No call data yet — start a conversation to generate metrics."

    entries: list[dict] = []
    for line in CALLS_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return "No valid call records found."

    # TODO (Phase 1): compute per-model stats and format as readable string
    # Per model: avg latency, total cost, avg input/output tokens, safety block rate
    raise NotImplementedError("Phase 1 — get_metrics computation")
