"""Call logger — appends every LLM call to logs/calls.jsonl (append-only JSONL).
Also provides a general-purpose application logger writing to logs/app.log.

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
import logging
import logging.handlers
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

LOGS_DIR = Path(__file__).parent.parent / "logs"
CALLS_LOG = LOGS_DIR / "calls.jsonl"
APP_LOG = LOGS_DIR / "app.log"

REQUIRED_CALL_FIELDS: frozenset[str] = frozenset({
    "timestamp", "model_id", "model_type",
    "input_tokens", "output_tokens",
    "llm_cost_usd", "total_cost_usd", "latency_ms",
})


def configure_logging(level: str = "INFO") -> None:
    """
    Set up rotating file + stderr handlers on the root logger.

    Idempotent — safe to call on every Streamlit rerun.
    Call once at app startup before any other imports emit logs.
    """
    root = logging.getLogger()
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        return
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%SZ")

    file_h = logging.handlers.RotatingFileHandler(
        APP_LOG, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_h.setFormatter(formatter)

    stream_h = logging.StreamHandler()
    stream_h.setFormatter(formatter)

    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(file_h)
    root.addHandler(stream_h)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call at module level: logger = get_logger(__name__)."""
    return logging.getLogger(name)


@contextmanager
def log_duration(logger: logging.Logger, label: str):
    """Context manager that logs elapsed ms for any code block at DEBUG level.

    Logs an ERROR (with full traceback) if the block raises an exception,
    then re-raises so the caller still handles it.
    """
    t0 = time.perf_counter()
    logger.debug("%s — start", label)
    try:
        yield
    except Exception:
        logger.exception("%s — raised", label)
        raise
    finally:
        ms = (time.perf_counter() - t0) * 1000
        logger.debug("%s — done in %.1f ms", label, ms)


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
    guardrail_cost_usd: float = 0.0,
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
    guardrail_cost_usd covers LlamaGuard (Claude Haiku tokens) + NeMo/Presidio
    (Modal CPU wall-clock) for both input and output pipelines.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    llm_cost = input_cost_usd + output_cost_usd
    total_cost = llm_cost + guardrail_cost_usd
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
        "llm_cost_usd": round(llm_cost, 8),
        "guardrail_cost_usd": round(guardrail_cost_usd, 8),
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
            if not REQUIRED_CALL_FIELDS.issubset(record):
                continue
            if model_id is None or record["model_id"] == model_id:
                records.append(record)
        except json.JSONDecodeError:
            continue
    return records
