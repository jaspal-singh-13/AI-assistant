"""Thread sidebar component.

Renders: thread list, new thread button, active thread highlight, context window slider.
FR-MEM-03, FR-MEM-04, FR-MEM-06.
"""

from __future__ import annotations

import streamlit as st


def render_sidebar() -> None:
    """
    Render the full sidebar: thread list + context window slider.

    Updates st.session_state["active_thread"] on thread selection.
    Updates st.session_state["active_thread"]["context_window_size"] on slider change.

    TODO (Phase 2): implement.
    """
    with st.sidebar:
        _render_thread_list()
        st.divider()
        _render_context_slider()


def _render_thread_list() -> None:
    """
    Render the thread list with a 'New thread' button at the top.

    - Auto-title generated from first 6 words of first user message (FR-MEM-06).
    - Active thread highlighted.
    - Clicking a thread loads it into st.session_state["active_thread"].

    TODO (Phase 2): implement.
    """
    st.markdown("### Threads")
    if st.button("+ New thread", use_container_width=True):
        # TODO: new_thread = create_thread(); st.session_state["active_thread"] = new_thread
        st.info("TODO Phase 2 — create_thread")

    threads = st.session_state.get("threads", [])
    for thread in threads:
        label = thread.get("title", thread.get("id", "untitled"))
        is_active = (
            st.session_state.get("active_thread", {}).get("id") == thread.get("id")
        )
        button_label = f"**{label}**" if is_active else label
        if st.button(button_label, key=f"thread_{thread['id']}", use_container_width=True):
            # TODO: load full thread and set as active
            pass


def _render_context_slider() -> None:
    """
    Render the context window slider (5–50, default 10) and dynamic label.

    FR-MEM-03, FR-MEM-04.
    TODO (Phase 2): implement.
    """
    thread = st.session_state.get("active_thread")
    if thread is None:
        return

    current = thread.get("context_window_size", 10)
    new_size = st.slider("Context window", min_value=5, max_value=50, value=current, step=1)
    if new_size != current:
        thread["context_window_size"] = new_size
        # TODO: save_thread(thread)

    # Dynamic label (FR-MEM-04)
    # from memory.manager import get_context_label
    # st.caption(get_context_label(thread))
    st.caption(f"LLM sees last {new_size} messages")  # placeholder
