"""Unit tests for LLM-as-judge — position swap, rubric selection, low_confidence flag.

FR §15.4 + FR-EVL-05a to FR-EVL-05e.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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


def _make_anthropic_response(json_text: str):
    """Build a mock Anthropic message response with given text content."""
    content_block = MagicMock()
    content_block.text = json_text
    response = MagicMock()
    response.content = [content_block]
    return response


class TestPositionSwap:
    def _mock_client(self, call_responses: list[str]):
        """Return a mock Anthropic client that returns each response in order."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _make_anthropic_response(r) for r in call_responses
        ]
        return mock_client

    def test_winner_declared_when_both_calls_agree(self):
        """Winner is declared only when both orderings agree on the same model."""
        from evaluation.llm_judge import judge_comparative, JudgeConfig

        # Normal order: A=5, B=3; Swapped order (B first, A second): A=5, B=3 again → consistent
        normal_resp = '{"response_a": {"score": 5, "reasoning": "great"}, "response_b": {"score": 3, "reasoning": "ok"}}'
        swapped_resp = '{"response_a": {"score": 3, "reasoning": "ok"}, "response_b": {"score": 5, "reasoning": "great"}}'

        mock_client = self._mock_client([normal_resp, swapped_resp])

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = judge_comparative(
                response_a="Paris is the capital.",
                response_b="I don't know.",
                prompt={"id": "t1", "category": "factual", "prompt": "Capital of France?"},
                config=JudgeConfig(),
                model_a_id="claude-sonnet",
                model_b_id="qwen-0.5b",
            )

        assert result.winner == "claude-sonnet"
        assert result.low_confidence is False

    def test_tie_when_calls_disagree(self):
        """Disagreement between orderings results in winner='tie' and low_confidence=True."""
        from evaluation.llm_judge import judge_comparative, JudgeConfig

        # Normal order: A=5, B=3; Swapped order gives A=2, B=4 → diverge > 1
        normal_resp = '{"response_a": {"score": 5, "reasoning": "great"}, "response_b": {"score": 3, "reasoning": "ok"}}'
        # Swapped: B first → first_score=4; A second → second_score=2
        swapped_resp = '{"response_a": {"score": 4, "reasoning": "ok"}, "response_b": {"score": 2, "reasoning": "poor"}}'

        mock_client = self._mock_client([normal_resp, swapped_resp])

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = judge_comparative(
                response_a="Maybe Paris?",
                response_b="Rome is the capital.",
                prompt={"id": "t2", "category": "factual", "prompt": "Capital of France?"},
                config=JudgeConfig(),
                model_a_id="claude-sonnet",
                model_b_id="qwen-0.5b",
            )

        assert result.low_confidence is True
        assert result.winner == "tie"


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
