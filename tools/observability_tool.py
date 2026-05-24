"""Observability summary tool — read-only agent self-awareness via calls.jsonl.

Returns per-model runtime statistics (latency, cost, tokens, tool usage, block rate).
Read-only: no writes, no network calls, no side effects.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

CALLS_LOG = Path(__file__).parent.parent / "logs" / "calls.jsonl"


@tool
def get_observability_summary(model_id: str = "") -> str:
    """Return runtime performance statistics from the call log.

    Covers all models by default. Pass a model_id substring to filter to a
    specific model (e.g. 'claude', 'qwen'). Use when the user asks about cost,
    latency, tokens, tool usage, blocked calls, or any runtime performance question.
    Read-only — does not modify any data.
    """
    import json
    from collections import defaultdict
    from statistics import median, quantiles

    if not CALLS_LOG.exists() or CALLS_LOG.stat().st_size == 0:
        return "No call data yet. Send a message in the Chat page to generate observability data."

    entries: list[dict] = []
    for line in CALLS_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return "No valid call records found in the log."

    if model_id:
        entries = [e for e in entries if model_id.lower() in e.get("model_id", "").lower()]
        if not entries:
            return f"No records found matching model_id filter: {model_id!r}"

    stats: dict = defaultdict(lambda: {
        "latencies": [], "costs": [], "input_tokens": [], "output_tokens": [],
        "blocked": 0, "tools": [], "total": 0,
    })

    for e in entries:
        m = e.get("model_id", "unknown")
        s = stats[m]
        s["total"] += 1
        if e.get("latency_ms"):
            s["latencies"].append(float(e["latency_ms"]))
        if e.get("total_cost_usd") is not None:
            s["costs"].append(float(e["total_cost_usd"]))
        if e.get("input_tokens"):
            s["input_tokens"].append(int(e["input_tokens"]))
        if e.get("output_tokens"):
            s["output_tokens"].append(int(e["output_tokens"]))
        if e.get("guardrail_blocked"):
            s["blocked"] += 1
        s["tools"].extend(e.get("tool_calls") or [])

    lines = [f"Observability Summary ({len(entries)} total calls)\n{'='*50}"]
    for model, s in stats.items():
        total = s["total"]
        lats = sorted(s["latencies"])
        avg_lat = sum(lats) / len(lats) if lats else 0
        p50 = median(lats) if lats else 0
        p95 = quantiles(lats, n=20)[18] if len(lats) >= 2 else (lats[0] if lats else 0)
        total_cost = sum(s["costs"])
        avg_cost_per_1k = (
            total_cost / (sum(s["input_tokens"]) + sum(s["output_tokens"])) * 1000
            if (s["input_tokens"] or s["output_tokens"]) and total_cost > 0
            else 0.0
        )
        block_rate = s["blocked"] / total if total else 0

        from collections import Counter
        top_tools = Counter(s["tools"]).most_common(3)
        tools_str = ", ".join(f"{t}×{c}" for t, c in top_tools) if top_tools else "none"

        lines.append(
            f"\nModel: {model}\n"
            f"  Calls          : {total:,}\n"
            f"  Avg latency    : {avg_lat:,.0f} ms  |  p50: {p50:,.0f} ms  |  p95: {p95:,.0f} ms\n"
            f"  Total cost     : ${total_cost:.4f}\n"
            f"  Avg cost/1k tok: ${avg_cost_per_1k:.4f}\n"
            f"  Block rate     : {block_rate:.1%}  ({s['blocked']} blocked)\n"
            f"  Top tools      : {tools_str}"
        )

    return "\n".join(lines)
