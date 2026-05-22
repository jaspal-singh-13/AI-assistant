"""Thread sidebar component.

Renders: thread list, new thread button, active thread highlight, context window slider.
FR-MEM-03, FR-MEM-04, FR-MEM-06.
"""

from __future__ import annotations

import streamlit as st

from memory.manager import create_thread, get_context_label, list_threads, load_thread, save_thread


def render_sidebar() -> None:
    """Render the full sidebar: thread list + context window slider."""
    with st.sidebar:
        _render_thread_list()
        st.divider()
        _render_context_slider()


def _render_thread_list() -> None:
    """Render the thread list with a 'New thread' button at the top."""
    st.markdown("### Threads")
    if st.button("+ New thread", use_container_width=True):
        new_thread = create_thread()
        st.session_state["active_thread"] = new_thread
        st.session_state["threads"] = list_threads()
        st.rerun()

    threads = st.session_state.get("threads", [])
    active_id = (st.session_state.get("active_thread") or {}).get("id")

    for thread in threads:
        tid = thread.get("id", "")
        label = thread.get("title", tid) or tid
        is_active = tid == active_id
        button_label = f"**{label}**" if is_active else label
        if st.button(button_label, key=f"thread_{tid}", use_container_width=True):
            st.session_state["active_thread"] = load_thread(tid)
            st.rerun()


def _render_context_slider() -> None:
    """Render the context window slider (5–50, default 10) and dynamic label."""
    thread = st.session_state.get("active_thread")
    if thread is None:
        return

    current = thread.get("context_window_size", 10)
    new_size = st.slider("Context window", min_value=5, max_value=50, value=current, step=1)
    if new_size != current:
        thread["context_window_size"] = new_size
        save_thread(thread)

    st.caption(get_context_label(thread))
