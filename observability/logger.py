"""Call logger — appends every LLM call to logs/calls.jsonl (append-only JSONL).

FR-OBS-01: Every LLM call logged with full schema (FR §6.3).
FR-GRD-05: Blocked calls stored with SHA-256 hash only, not raw content.
NFR-PRV-01: PII redacted from all log fields before writing.

Relationship to the 3 evaluation dimensions (see EVALUATION.md):
  - Hallucination Rate:  NOT stored here. Stored in evaluation/results/summary.csv.
  - Bias & Harmful:      NOT stored here. Stored in evaluation/results/summary.csv.
  - Content Safety:      guardrail_blocked + block_reason + block_stage fields here
                         contribute to the content_safety.guardrail_block_rate metric
                         in evaluation/results/model_scores.json.

This file is the runtime log. Eval scores are in evaluation/results/*.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

LOGS_DIR = Path(__file__).parent.parent / "logs"
CALLS_LOG = LOGS_DIR / "calls.jsonl"


def log_call(
    *,
    model_id: str,
    model_type: str,
    input_tokens: int,
    output_tokens: int,
    input_cost_usd: float,
    output_cost_usd: float,
    latency_ms: float,
    pricing_source: str,
    pricing_fetched_at: str,
    guardrail_blocked: bool = False,
    block_layer: str | None = None,
    block_reason: str | None = None,
    block_stage: str | None = None,
    original_message_hash: str | None = None,
    summary_used: bool = False,
    tool_calls: list[str] | None = None,
) -> None:
    """
    Append one call record to logs/calls.jsonl.

    All cost fields are computed by the caller (observability.pricing).
    PII must be redacted before calling this function (NFR-PRV-01).

    TODO (Phase 3): implement file write.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    total_cost = input_cost_usd + output_cost_usd
    total_tokens = input_tokens + output_tokens
    cost_per_1k = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0.0

    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "model_type": model_type,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost_usd, 8),
        "output_cost_usd": round(output_cost_usd, 8),
        "total_cost_usd": round(total_cost, 8),
        "cost_per_1k_tokens": round(cost_per_1k, 6),
        "latency_ms": round(latency_ms, 2),
        "pricing_source": pricing_source,
        "pricing_fetched_at": pricing_fetched_at,
        "guardrail_blocked": guardrail_blocked,
        "block_layer": block_layer,
        "block_reason": block_reason,
        "block_stage": block_stage,
        "original_message_hash": original_message_hash,
        "summary_used": summary_used,
        "tool_calls": tool_calls or [],
    }

    lock = FileLock(str(CALLS_LOG) + ".lock")
    with lock:
        with CALLS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_calls(model_id: str | None = None) -> list[dict]:
    """Load all call records from calls.jsonl, optionally filtered by model_id."""
    if not CALLS_LOG.exists():
        return []
    records = []
    for line in CALLS_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            if model_id is None or record.get("model_id") == model_id:
                records.append(record)
        except json.JSONDecodeError:
            continue
    return records
