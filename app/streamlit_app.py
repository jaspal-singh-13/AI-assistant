"""Streamlit application entry point.

Run with: streamlit run app/streamlit_app.py

Session state keys:
  - "threads"         : list of thread index entries (from memory.manager.list_threads)
  - "active_thread"   : current thread dict (fully loaded)
  - "model_key"       : active model key (str, e.g. "claude-sonnet")
  - "pricing"         : {data, source, fetched_at} cached for 24hr (FR-OBS-02)
  - "agent_graph"     : compiled LangGraph graph for current model

FR-MOD-01 to FR-MOD-05, FR-MEM-03, FR-AGT-01 to FR-AGT-04.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  # must run before any langchain/anthropic imports read env vars

import logging
logging.getLogger("transformers").setLevel(logging.ERROR)

import nest_asyncio
nest_asyncio.apply()

import streamlit as st

from agent.factory import create_agent
from agent.models import DEFAULT_MODEL_KEY, build_llm, list_models
from memory.manager import list_threads
from tools.registry import get_tools
from app.components.thread_sidebar import render_sidebar
from app.components.chat_window import render_chat


@st.cache_resource(show_spinner="Warming up agents…")
def _warmup_graphs() -> dict:
    """Build one compiled graph per model at startup and cache across reruns."""
    tools = get_tools()
    graphs = {}
    for key, _ in list_models():
        try:
            graphs[key] = create_agent(build_llm(key), tools)
        except Exception:
            graphs[key] = None  # missing credentials — will error clearly on first send
    return graphs


def init_session_state() -> None:
    """Initialise all st.session_state keys on first load."""
    if "model_key" not in st.session_state:
        st.session_state["model_key"] = DEFAULT_MODEL_KEY
    if "threads" not in st.session_state:
        st.session_state["threads"] = list_threads()
    if "active_thread" not in st.session_state:
        st.session_state["active_thread"] = None
    if "pricing" not in st.session_state:
        st.session_state["pricing"] = None
    if "pending_response" not in st.session_state:
        st.session_state["pending_response"] = False
    # Pull the pre-warmed graph for the current model into session state
    if "agent_graph" not in st.session_state:
        graphs = _warmup_graphs()
        st.session_state["agent_graph"] = graphs.get(st.session_state.get("model_key", DEFAULT_MODEL_KEY))


def render_model_selector() -> None:
    """Render the model dropdown in the header (FR-MOD-01)."""
    models = list_models()
    options = {config.model_label: key for key, config in models}
    current_key = st.session_state.get("model_key", DEFAULT_MODEL_KEY)
    current_label = next(
        (config.model_label for key, config in models if key == current_key),
        models[0][1].model_label,
    )
    chosen_label = st.selectbox(
        "Model",
        list(options.keys()),
        index=list(options.keys()).index(current_label),
        label_visibility="collapsed",
    )
    chosen_key = options[chosen_label]
    if chosen_key != st.session_state.get("model_key"):
        st.session_state["model_key"] = chosen_key
        # Swap to the already-warmed graph for the chosen model
        graphs = _warmup_graphs()
        st.session_state["agent_graph"] = graphs.get(chosen_key)
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="AI Assistant Comparison",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("AI Assistant Comparison")
    with col2:
        render_model_selector()

    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
