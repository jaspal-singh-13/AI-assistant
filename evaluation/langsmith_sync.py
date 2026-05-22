"""LangSmith score sync — write DeepEval scores back to LangSmith.

FR-OBS-06: DeepEval scores written to LangSmith via client.create_feedback().
LangSmith stores and displays them; it does not compute scores itself.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

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

    TODO (Phase 4): implement.
    """
    # from langsmith import Client
    # client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    # for r in results:
    #     run_id = _lookup_run_id(client, r.model_id, r.prompt_id)
    #     if run_id:
    #         client.create_feedback(
    #             run_id=run_id,
    #             key=r.metric,
    #             score=r.score / 5.0,
    #             comment=r.reasoning,
    #         )
    raise NotImplementedError("Phase 4 — sync_scores_to_langsmith")


def _lookup_run_id(client, model_id: str, prompt_id: str) -> str | None:
    """
    Find the LangSmith run ID for a (model_id, prompt_id) pair.
    TODO (Phase 4): implement by searching runs in the project.
    """
    raise NotImplementedError("Phase 4 — _lookup_run_id")
