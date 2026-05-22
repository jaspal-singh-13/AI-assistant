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

import streamlit as st

# TODO (Phase 2): uncomment once deps installed
# import nest_asyncio
# nest_asyncio.apply()

# from agent.factory import create_agent, run_agent
# from agent.models import DEFAULT_MODEL_KEY, build_llm, list_models
# from memory.manager import create_thread, list_threads, get_context_label
# from tools.registry import get_tools
# from observability.pricing import fetch_pricing
# from app.components.thread_sidebar import render_sidebar
# from app.components.chat_window import render_chat
# from app.components.stream_handler import handle_send


def init_session_state() -> None:
    """Initialise all st.session_state keys on first load."""
    if "model_key" not in st.session_state:
        st.session_state["model_key"] = "claude-sonnet"  # DEFAULT_MODEL_KEY
    if "threads" not in st.session_state:
        st.session_state["threads"] = []  # list_threads()
    if "active_thread" not in st.session_state:
        st.session_state["active_thread"] = None
    if "pricing" not in st.session_state:
        st.session_state["pricing"] = None  # fetch_pricing() TODO Phase 3
    if "agent_graph" not in st.session_state:
        st.session_state["agent_graph"] = None  # rebuilt on model switch


def render_model_selector() -> None:
    """Render the model dropdown in the header (FR-MOD-01)."""
    # TODO (Phase 2): implement with st.selectbox
    # models = list_models()
    # options = {label: key for key, config in models for label in [config.model_label]}
    # ...
    st.info("TODO Phase 2 — model selector")


def main() -> None:
    st.set_page_config(
        page_title="AI Assistant Comparison",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    # Header — model selector always visible (FR-MOD-01)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("AI Assistant Comparison")
    with col2:
        render_model_selector()

    # Sidebar — thread list + context slider
    # TODO (Phase 2): render_sidebar()
    with st.sidebar:
        st.markdown("### Threads")
        st.info("TODO Phase 2 — thread sidebar")

    # Main chat window
    # TODO (Phase 2): render_chat()
    st.info("TODO Phase 2 — chat window")


if __name__ == "__main__":
    main()
