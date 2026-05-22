"""Unit tests for agent/models.py and agent/factory.py.

Tests verify model registry correctness and agent graph construction.
External LLM calls are always mocked — no real API calls in tests.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestModelRegistry:
    def test_default_model_key_exists(self):
        """DEFAULT_MODEL_KEY must be a valid key in MODELS."""
        from agent.models import MODELS, DEFAULT_MODEL_KEY
        assert DEFAULT_MODEL_KEY in MODELS

    def test_get_model_returns_config(self):
        """get_model returns a ModelConfig for known keys."""
        from agent.models import get_model
        config = get_model("claude-sonnet")
        assert config.model_id == "claude-sonnet-4-20250514"
        assert config.model_type == "frontier"

    def test_get_model_raises_on_unknown(self):
        """get_model raises ValueError for unknown keys."""
        from agent.models import get_model
        with pytest.raises(ValueError, match="Unknown model key"):
            get_model("not-a-real-model")

    def test_list_models_returns_all(self):
        """list_models returns all registered models."""
        from agent.models import list_models, MODELS
        result = list_models()
        assert len(result) == len(MODELS)
        keys = [k for k, _ in result]
        assert "claude-sonnet" in keys
        assert "qwen-0.5b" in keys

    def test_all_models_have_required_fields(self):
        """Every ModelConfig has model_id, model_label, and model_type."""
        from agent.models import MODELS
        for key, config in MODELS.items():
            assert config.model_id, f"{key} missing model_id"
            assert config.model_label, f"{key} missing model_label"
            assert config.model_type in ("frontier", "oss"), f"{key} invalid model_type"

    def test_oss_model_has_hf_repo(self):
        """OSS models must have hf_repo set."""
        from agent.models import get_model
        qwen = get_model("qwen-0.5b")
        assert qwen.hf_repo is not None
        assert "Qwen" in qwen.hf_repo

    def test_build_llm_frontier(self):
        """build_llm for frontier model returns a ChatAnthropic instance (mocked)."""
        pytest.skip("Phase 1 — needs langchain-anthropic installed")

    def test_build_llm_oss(self):
        """build_llm for OSS model returns a ChatHuggingFace instance (mocked)."""
        pytest.skip("Phase 1 — needs langchain-huggingface installed")


class TestAgentFactory:
    def test_create_agent_returns_compiled_graph(self):
        """create_agent returns a CompiledGraph when given a mock LLM and tools."""
        pytest.skip("Phase 1 — implement create_agent first")

    def test_run_agent_returns_response_and_snapshot(self):
        """run_agent returns (str, list[dict]) with at least a response step."""
        pytest.skip("Phase 1 — implement run_agent first")

    def test_state_snapshot_tool_call_has_call_id(self):
        """Tool call steps in state_snapshot include call_id (FR §15.2)."""
        pytest.skip("Phase 1 — implement _parse_message_to_step first")

    def test_state_snapshot_direct_response_has_no_tools(self):
        """When no tools are called, state_snapshot has a single response step."""
        pytest.skip("Phase 1 — implement run_agent first")
