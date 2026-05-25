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
        """get_model returns a ModelConfig for a known key."""
        from agent.models import get_model, DEFAULT_MODEL_KEY
        config = get_model(DEFAULT_MODEL_KEY)
        assert config.model_id
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

    def test_all_models_have_required_fields(self):
        """Every ModelConfig has model_id, model_label, and model_type."""
        from agent.models import MODELS
        for key, config in MODELS.items():
            assert config.model_id, f"{key} missing model_id"
            assert config.model_label, f"{key} missing model_label"
            assert config.model_type in ("frontier", "oss"), f"{key} invalid model_type"

    def test_oss_model_has_hf_repo(self):
        """OSS models must have hf_repo set."""
        from agent.models import MODELS
        oss_models = [(k, c) for k, c in MODELS.items() if c.model_type == "oss"]
        assert oss_models, "No OSS model registered"
        for key, config in oss_models:
            assert config.hf_repo is not None, f"{key} missing hf_repo"

    def test_build_llm_frontier(self):
        """build_llm for frontier model returns a ChatAnthropic instance (mocked)."""
        from agent.models import DEFAULT_MODEL_KEY
        mock_llm = MagicMock()
        with patch.dict("sys.modules", {"langchain_anthropic": MagicMock(ChatAnthropic=MagicMock(return_value=mock_llm))}):
            from agent.models import build_llm
            result = build_llm(DEFAULT_MODEL_KEY)
        assert result is not None

    def test_build_llm_oss(self):
        """build_llm for OSS model returns a LocalTransformersChatModel (mocked)."""
        from agent.models import MODELS
        oss_key = next(k for k, c in MODELS.items() if c.model_type == "oss")
        mock_local_model = MagicMock()
        mock_local_module = MagicMock()
        mock_local_module.LocalTransformersChatModel.return_value = mock_local_model
        with patch.dict("sys.modules", {"agent.local_llm": mock_local_module}):
            from agent.models import build_llm
            result = build_llm(oss_key)
        assert result is not None


class TestAgentFactory:
    def test_create_agent_returns_compiled_graph(self):
        """create_agent returns a CompiledGraph when given a mock LLM and tools."""
        mock_graph = MagicMock()
        mock_llm = MagicMock()
        with patch("agent.factory.create_react_agent", return_value=mock_graph, create=True):
            with patch.dict("sys.modules", {
                "langgraph.prebuilt": MagicMock(create_react_agent=MagicMock(return_value=mock_graph))
            }):
                from agent.factory import create_agent
                result = create_agent(mock_llm, [])
        assert result is not None

    def test_run_agent_returns_response_and_snapshot(self):
        """run_agent returns (str, list[dict]) with at least a response step."""
        from langchain_core.messages import AIMessage
        mock_graph = MagicMock()
        ai_msg = AIMessage(content="Hello!", tool_calls=[])
        mock_graph.stream.return_value = [{"agent": {"messages": [ai_msg]}}]

        from agent.factory import run_agent
        response, snapshot = run_agent(mock_graph, [{"role": "user", "content": "hi"}])

        assert isinstance(response, str)
        assert isinstance(snapshot, list)
        assert response == "Hello!"

    def test_state_snapshot_tool_call_has_call_id(self):
        """Tool call steps in state_snapshot include call_id (FR §15.2)."""
        from langchain_core.messages import AIMessage
        from agent.factory import _parse_message_to_step

        msg = AIMessage(
            content="",
            tool_calls=[{"name": "get_weather", "args": {"city": "London"}, "id": "tc-001", "type": "tool_call"}],
        )
        step = _parse_message_to_step(msg)
        assert step is not None
        assert step["type"] == "tool_call"
        assert step["call_id"] == "tc-001"
        assert step["tool"] == "get_weather"

    def test_state_snapshot_direct_response_has_no_tools(self):
        """When no tools are called, state_snapshot has a single response step."""
        from langchain_core.messages import AIMessage
        from agent.factory import _parse_message_to_step

        msg = AIMessage(content="Here is your answer.", tool_calls=[])
        step = _parse_message_to_step(msg)
        assert step is not None
        assert step["type"] == "response"
        assert step["content"] == "Here is your answer."


class TestSystemPrompt:
    def test_system_prompt_lists_all_four_pages(self):
        """SYSTEM_PROMPT must mention all four app pages by name."""
        from agent.system_prompt import SYSTEM_PROMPT
        for page in ("Dashboard", "Chat", "Observability", "Evaluation"):
            assert page in SYSTEM_PROMPT, f"Page '{page}' not found in SYSTEM_PROMPT"

    def test_system_prompt_has_required_sections(self):
        """SYSTEM_PROMPT must contain the App map, walkthroughs, proactive help, and tool sections."""
        from agent.system_prompt import SYSTEM_PROMPT
        for header in (
            "APP MAP",
            "STEP-BY-STEP WALKTHROUGHS",
            "WHEN TO OFFER THE APP MAP PROACTIVELY",
            "AVAILABLE TOOLS",
        ):
            assert header in SYSTEM_PROMPT, f"Section '{header}' not found in SYSTEM_PROMPT"

    def test_system_prompt_covers_each_process(self):
        """Every process letter A through M must have a Layer 2 walkthrough section."""
        from agent.system_prompt import SYSTEM_PROMPT
        import string
        for letter in string.ascii_uppercase[:13]:  # A–M
            marker = f"### {letter}."
            assert marker in SYSTEM_PROMPT, f"Walkthrough '{marker}' not found in SYSTEM_PROMPT"
