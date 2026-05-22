"""Metrics tool — agent self-awareness via calls.jsonl.

FR-TOOL-05: Reads logs/calls.jsonl and returns summary statistics.
Makes the agent self-aware of its own performance (latency, cost, safety block rate).
Natural language queries like "how fast are you?" trigger this tool.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from langchain_core.tools import tool

CALLS_LOG = Path(__file__).parent.parent / "logs" / "calls.jsonl"


@tool
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

    stats: dict = defaultdict(lambda: {"latency": [], "cost": [], "blocked": 0, "total": 0})
    for e in entries:
        m = e.get("model_key", "unknown")
        stats[m]["total"] += 1
        if e.get("latency_ms"):
            stats[m]["latency"].append(e["latency_ms"])
        if e.get("total_cost"):
            stats[m]["cost"].append(e["total_cost"])
        if e.get("blocked"):
            stats[m]["blocked"] += 1

    lines = []
    for model, s in stats.items():
        avg_lat = sum(s["latency"]) / len(s["latency"]) if s["latency"] else 0
        total_cost = sum(s["cost"])
        block_rate = s["blocked"] / s["total"] if s["total"] else 0
        lines.append(
            f"{model}: avg latency {avg_lat:.0f}ms, total cost ${total_cost:.4f}, "
            f"block rate {block_rate:.1%}"
        )
    return "\n".join(lines) if lines else "No stats available."
