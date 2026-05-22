"""Unit tests for LLM-as-judge — position swap, rubric selection, low_confidence flag.

FR §15.4 + FR-EVL-05a to FR-EVL-05e.
"""

from __future__ import annotations

import pytest


class TestRubricSelection:
    def test_factual_hallucination_rubric_exists(self):
        """get_rubric returns a non-empty string for factual + hallucination."""
        from evaluation.llm_judge import get_rubric
        rubric = get_rubric("factual", "hallucination")
        assert isinstance(rubric, str)
        assert len(rubric) > 20

    def test_adversarial_jailbreak_rubric_exists(self):
        from evaluation.llm_judge import get_rubric
        rubric = get_rubric("adversarial", "jailbreak_resistance")
        assert isinstance(rubric, str)

    def test_bias_rubric_exists(self):
        from evaluation.llm_judge import get_rubric
        rubric = get_rubric("bias_sensitive", "bias")
        assert isinstance(rubric, str)

    def test_unknown_rubric_raises(self):
        from evaluation.llm_judge import get_rubric
        with pytest.raises(ValueError):
            get_rubric("factual", "jailbreak_resistance")  # type: ignore


class TestPositionSwap:
    def test_winner_declared_when_both_calls_agree(self):
        """Winner is declared only when both orderings agree on the same model."""
        pytest.skip("Phase 4")

    def test_tie_when_calls_disagree(self):
        """Disagreement between orderings results in winner='tie' and low_confidence=True."""
        pytest.skip("Phase 4")


class TestComparativeResult:
    def test_low_confidence_winner_is_tie(self):
        """ComparativeResult.winner returns 'tie' when low_confidence=True."""
        from evaluation.llm_judge import ComparativeResult
        result = ComparativeResult(
            prompt_id="test_001",
            prompt_category="factual",
            dimension="hallucination",
            ordering="model_a_first",
            model_a="claude-sonnet",
            model_b="llama-1b",
            model_a_score=4,
            model_b_score=3,
            low_confidence=True,
        )
        assert result.winner == "tie"

    def test_correct_winner_when_high_confidence(self):
        """ComparativeResult.winner returns the higher-scoring model."""
        from evaluation.llm_judge import ComparativeResult
        result = ComparativeResult(
            prompt_id="test_002",
            prompt_category="factual",
            dimension="hallucination",
            ordering="model_a_first",
            model_a="claude-sonnet",
            model_b="llama-1b",
            model_a_score=5,
            model_b_score=3,
            low_confidence=False,
        )
        assert result.winner == "claude-sonnet"
