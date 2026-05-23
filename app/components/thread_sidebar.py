"""Thread sidebar component.

Renders: New Chat button, thread list with rename/delete, context window slider.
FR-MEM-03, FR-MEM-04, FR-MEM-06.
"""

from __future__ import annotations

import streamlit as st

from memory.manager import (
    DEFAULT_SUMMARY_TRIGGER,
    create_thread,
    delete_thread,
    get_context_label,
    list_threads,
    load_thread,
    rename_thread,
    save_thread,
)


def render_sidebar() -> None:
    """Render the full sidebar: new chat button, thread list, context window slider."""
    with st.sidebar:
        _render_new_chat_button()
        st.divider()
        _render_thread_list()
        st.divider()
        _render_context_slider()


def _render_new_chat_button() -> None:
    """Prominent New Chat button at the top of the sidebar."""
    if st.button("+ New Chat", use_container_width=True, type="primary"):
        new_thread = create_thread()
        st.session_state["active_thread"] = new_thread
        st.session_state["threads"] = list_threads()
        st.session_state.pop("editing_thread_id", None)
        st.rerun()


def _render_thread_list() -> None:
    """Render thread list; each row has the title button + rename + delete icons."""
    st.markdown("### Threads")

    threads = st.session_state.get("threads", [])
    active_id = (st.session_state.get("active_thread") or {}).get("id")
    editing_id = st.session_state.get("editing_thread_id")

    for thread in threads:
        tid = thread.get("id", "")
        label = thread.get("title", tid) or tid
        is_active = tid == active_id

        if editing_id == tid:
            # Inline rename form
            new_title = st.text_input(
                "Rename", value=label, key=f"rename_input_{tid}", label_visibility="collapsed"
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_{tid}", use_container_width=True):
                    full_thread = load_thread(tid)
                    rename_thread(full_thread, new_title)
                    if is_active:
                        st.session_state["active_thread"] = full_thread
                    st.session_state["threads"] = list_threads()
                    st.session_state.pop("editing_thread_id", None)
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_{tid}", use_container_width=True):
                    st.session_state.pop("editing_thread_id", None)
                    st.rerun()
        else:
            col_title, col_edit, col_del = st.columns([6, 1, 1])
            with col_title:
                btn_label = f"**{label}**" if is_active else label
                if st.button(btn_label, key=f"thread_{tid}", use_container_width=True):
                    st.session_state["active_thread"] = load_thread(tid)
                    st.rerun()
            with col_edit:
                if st.button("✏️", key=f"edit_{tid}", help="Rename"):
                    st.session_state["editing_thread_id"] = tid
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{tid}", help="Delete"):
                    delete_thread(tid)
                    if is_active:
                        st.session_state["active_thread"] = None
                    st.session_state["threads"] = list_threads()
                    st.rerun()


def _render_context_slider() -> None:
    """Render the context window + summary trigger sliders and dynamic label."""
    thread = st.session_state.get("active_thread")
    if thread is None:
        return

    current_window = thread.get("context_window_size", 10)
    new_window = st.slider("Context window", min_value=5, max_value=50, value=current_window, step=1)
    if new_window != current_window:
        thread["context_window_size"] = new_window
        # Clamp summary_trigger so it stays at least context_window + 5
        min_trigger = new_window + 5
        if thread.get("summary_trigger", DEFAULT_SUMMARY_TRIGGER) < min_trigger:
            thread["summary_trigger"] = min_trigger
        save_thread(thread)

    min_trigger = thread.get("context_window_size", 10) + 5
    current_trigger = max(thread.get("summary_trigger", DEFAULT_SUMMARY_TRIGGER), min_trigger)
    new_trigger = st.slider(
        "Summary trigger",
        min_value=min_trigger,
        max_value=100,
        value=current_trigger,
        step=1,
        help="Summarise when this many messages fall outside the context window (always ≥ context window + 5)",
    )
    if new_trigger != thread.get("summary_trigger"):
        thread["summary_trigger"] = new_trigger
        save_thread(thread)

    st.caption(get_context_label(thread))
