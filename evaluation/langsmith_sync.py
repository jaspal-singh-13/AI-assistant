"""LangSmith score sync — write DeepEval scores back to LangSmith.

FR-OBS-06: DeepEval scores written to LangSmith via client.create_feedback().
LangSmith stores and displays them; it does not compute scores itself.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from observability.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from evaluation.framework import EvalResult


def sync_scores_to_langsmith(results: list["EvalResult"]) -> None:
    """
    Upload all EvalResult scores to LangSmith as feedback entries.

    Each result maps to one client.create_feedback() call with:
      run_id   ← looked up from LangSmith by (model_id, prompt_id)
      key      ← result.metric
      score    ← result.score / 5  (normalised 0–1)
      comment  ← result.reasoning
    """
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        logger.debug("sync_scores_to_langsmith | LANGSMITH_API_KEY not set — skipping")
        return

    from langsmith import Client  # type: ignore[import]

    logger.info("sync_scores_to_langsmith | start | n=%d", len(results))
    client = Client(api_key=api_key)
    synced = 0
    for r in results:
        run_id = _lookup_run_id(client, r.model_id, r.prompt_id)
        if run_id:
            client.create_feedback(
                run_id=run_id,
                key=r.metric,
                score=r.score / 5.0,
                comment=r.reasoning or None,
            )
            synced += 1
    logger.info("sync_scores_to_langsmith | done | synced=%d / %d", synced, len(results))


def _lookup_run_id(client, model_id: str, prompt_id: str) -> str | None:
    """Find the LangSmith run ID for a (model_id, prompt_id) pair."""
        project = os.environ.get("LANGSMITH_PROJECT", "ai-assistant-eval")
    try:
        runs = list(client.list_runs(
            project_name=project,
            filter=f'and(eq(metadata_key, "model_id"), eq(metadata_value, "{model_id}"))',
        ))
        for run in runs:
            meta = run.extra.get("metadata", {}) if run.extra else {}
            if meta.get("prompt_id") == prompt_id:
                logger.debug("_lookup_run_id | found | model=%s pid=%s", model_id, prompt_id)
                return str(run.id)
    except Exception:
        logger.warning("_lookup_run_id | lookup failed | model=%s pid=%s", model_id, prompt_id, exc_info=True)
    return None
