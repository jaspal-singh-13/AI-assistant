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

    def test_build_llm_oss_local(self, monkeypatch):
        """OSS model with no OSS_SERVE_URL set falls back to LocalTransformersChatModel."""
        from agent.models import MODELS
        oss_key = next(k for k, c in MODELS.items() if c.model_type == "oss")
        monkeypatch.delenv("OSS_SERVE_URL", raising=False)
        mock_local_model = MagicMock()
        mock_local_module = MagicMock()
        mock_local_module.LocalTransformersChatModel.return_value = mock_local_model
        with patch.dict("sys.modules", {"agent.local_llm": mock_local_module}):
            from agent.models import build_llm
            result = build_llm(oss_key)
        assert result is not None

    def test_build_llm_oss_served(self, monkeypatch):
        """OSS model with OSS_SERVE_URL set uses ChatOpenAI against that URL."""
        from agent.models import MODELS
        oss_key = next(k for k, c in MODELS.items() if c.model_type == "oss")
        monkeypatch.setenv("OSS_SERVE_URL", "http://localhost:8000/v1")
        mock_chat = MagicMock()
        mock_openai_module = MagicMock(ChatOpenAI=MagicMock(return_value=mock_chat))
        with patch.dict("sys.modules", {"langchain_openai": mock_openai_module}):
            from agent.models import build_llm
            result = build_llm(oss_key)
        assert result is mock_chat
        mock_openai_module.ChatOpenAI.assert_called_once()
        kwargs = mock_openai_module.ChatOpenAI.call_args.kwargs
        assert kwargs["base_url"] == "http://localhost:8000/v1"


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
        steps = _parse_message_to_step(msg)
        assert len(steps) == 1
        assert steps[0]["type"] == "tool_call"
        assert steps[0]["call_id"] == "tc-001"
        assert steps[0]["tool"] == "get_weather"

    def test_state_snapshot_direct_response_has_no_tools(self):
        """When no tools are called, state_snapshot has a single response step."""
        from langchain_core.messages import AIMessage
        from agent.factory import _parse_message_to_step

        msg = AIMessage(content="Here is your answer.", tool_calls=[])
        steps = _parse_message_to_step(msg)
        assert len(steps) == 1
        assert steps[0]["type"] == "response"
        assert steps[0]["content"] == "Here is your answer."

    def test_parallel_tool_calls_fan_out(self):
        """An AIMessage with N parallel tool_calls produces N tool_call steps,
        not just the first (regression: previously msg.tool_calls[0] silently
        dropped all but the first call)."""
        from langchain_core.messages import AIMessage
        from agent.factory import _parse_message_to_step

        msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "get_weather", "args": {"city": "Nagpur"}, "id": "tc-1", "type": "tool_call"},
                {"name": "get_weather", "args": {"city": "Indore"}, "id": "tc-2", "type": "tool_call"},
                {"name": "get_weather", "args": {"city": "Pune"}, "id": "tc-3", "type": "tool_call"},
            ],
        )
        steps = _parse_message_to_step(msg)
        assert len(steps) == 3
        assert [s["args"]["city"] for s in steps] == ["Nagpur", "Indore", "Pune"]
        assert [s["call_id"] for s in steps] == ["tc-1", "tc-2", "tc-3"]
        assert all(s["type"] == "tool_call" for s in steps)

    def test_fold_tool_results_pairs_by_call_id(self):
        """fold_tool_results attaches each tool_result.content to its matching
        tool_call (by call_id) and drops the standalone tool_result entries."""
        from agent.factory import fold_tool_results

        raw = [
            {"type": "tool_call", "tool": "get_weather", "args": {"city": "Nagpur"}, "call_id": "tc-1", "latency_ms": 0},
            {"type": "tool_call", "tool": "get_weather", "args": {"city": "Indore"}, "call_id": "tc-2", "latency_ms": 0},
            {"type": "tool_call", "tool": "get_weather", "args": {"city": "Pune"},   "call_id": "tc-3", "latency_ms": 0},
            {"type": "tool_result", "content": "Nagpur: 42C", "call_id": "tc-1"},
            {"type": "tool_result", "content": "Indore: 38C", "call_id": "tc-2"},
            {"type": "tool_result", "content": "Pune: 32C",   "call_id": "tc-3"},
            {"type": "response", "content": "Here you go."},
        ]
        folded = fold_tool_results(raw)

        assert [s["type"] for s in folded] == ["tool_call", "tool_call", "tool_call", "response"]
        assert folded[0]["result"] == "Nagpur: 42C"
        assert folded[1]["result"] == "Indore: 38C"
        assert folded[2]["result"] == "Pune: 32C"

    def test_fold_tool_results_preserves_unmatched(self):
        """An unmatched tool_result (no preceding tool_call with same id) is
        kept so malformed streams do not silently lose data."""
        from agent.factory import fold_tool_results

        raw = [
            {"type": "tool_result", "content": "orphan", "call_id": "tc-missing"},
            {"type": "response", "content": "done"},
        ]
        folded = fold_tool_results(raw)
        assert folded == raw


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
