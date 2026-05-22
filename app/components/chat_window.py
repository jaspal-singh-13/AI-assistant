"""Chat window component.

Renders all messages with:
  - Model badges per assistant message (blue=frontier, coral=OSS) — FR-MOD-04.
  - Mid-thread model switch dividers — FR-MOD-02.
  - Message input box with send button.
  - Agent reasoning state panel toggle.
"""

from __future__ import annotations

import streamlit as st

FRONTIER_BADGE_COLOR = "#3B82F6"   # blue
OSS_BADGE_COLOR = "#F97316"        # coral/orange

BADGE_CSS = """
<span style="
  background-color:{color};
  color:white;
  font-size:0.7rem;
  font-weight:600;
  padding:2px 8px;
  border-radius:12px;
  float:right;
  cursor:help;
" title="Tokens: {tokens} | Cost: ${cost:.6f}">{label}</span>
"""


def render_chat() -> None:
    """Render the full chat window for the active thread."""
    thread = st.session_state.get("active_thread")
    if thread is None:
        st.info("Select or create a thread to start chatting.")
        return

    messages = thread.get("messages", [])
    _render_messages(messages)

    # If a response is pending, run the agent now (user message already visible above)
    from app.components.stream_handler import run_pending_response
    run_pending_response()

    _render_input_box()


def _render_messages(messages: list[dict]) -> None:
    """Render each message; insert a divider when the model changes mid-thread."""
    prev_model = None
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        metadata = msg.get("metadata", {})
        model_label = metadata.get("model_label")
        model_type = metadata.get("model_type", "frontier")

        if role == "assistant" and model_label and model_label != prev_model and prev_model is not None:
            st.markdown(
                f"<div style='text-align:center;color:gray;'>── switched to {model_label} ──</div>",
                unsafe_allow_html=True,
            )
        if role == "assistant" and model_label:
            prev_model = model_label

        with st.chat_message(role):
            if role == "assistant" and model_label:
                badge_color = FRONTIER_BADGE_COLOR if model_type == "frontier" else OSS_BADGE_COLOR
                tokens = metadata.get("input_tokens", 0) + metadata.get("output_tokens", 0)
                cost = metadata.get("cost_usd", 0.0)
                badge = BADGE_CSS.format(color=badge_color, label=model_label, tokens=tokens, cost=cost)
                st.markdown(badge, unsafe_allow_html=True)

            st.markdown(content)

            if role == "assistant" and msg.get("state_snapshot"):
                from app.components.state_panel import render_state_panel
                render_state_panel(msg["state_snapshot"], metadata)


def _render_input_box() -> None:
    """Render the chat input and invoke handle_send on submit."""
    if prompt := st.chat_input("Type a message…"):
        from app.components.stream_handler import handle_send
        handle_send(prompt)
