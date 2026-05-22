"""Agent reasoning state panel component.

Renders a collapsible panel below each assistant message showing the full
LangGraph step sequence: THINKING → TOOL CALL → RESPONDING.

FR-AGT-04: Collapsible panel with per-step detail and latency.
FR §15.2: call_id used to match tool call → tool result pairs.
"""

from __future__ import annotations

import streamlit as st

MAX_ARG_LEN = 80    # truncate tool arg values to 80 chars (FR-AGT-04)
MAX_RESULT_LEN = 200  # truncate tool results to 200 chars (FR-AGT-04)


def render_state_panel(state_snapshot: list[dict], metadata: dict) -> None:
    """Render the collapsible 'Agent reasoning' panel for one assistant message."""
    if not state_snapshot:
        return

    model_label = metadata.get("model_label", "")
    n_steps = len(state_snapshot)
    total_latency = sum(s.get("latency_ms", 0) for s in state_snapshot)

    with st.expander(f"Agent reasoning  [{model_label}]  {n_steps} steps · {total_latency:.0f}ms"):
        _render_steps(state_snapshot)


def _render_steps(steps: list[dict]) -> None:
    """Render each step in sequence."""
    tool_steps = [s for s in steps if s.get("type") == "tool_call"]

    if not tool_steps:
        st.caption("Direct response — no tools called")
        return

    for i, step in enumerate(steps, start=1):
        step_type = step.get("type", "")

        if step_type == "thinking":
            st.markdown(f"**{i}. THINKING**")
            content = step.get("content", "")[:MAX_ARG_LEN]
            st.caption(f"> {content}")

        elif step_type == "tool_call":
            tool_name = step.get("tool", "unknown")
            latency = step.get("latency_ms", 0)
            st.markdown(f"**{i}. TOOL CALL** `[{tool_name}]`")

            args = step.get("args", {})
            if args:
                rows = [(k, str(v)[:MAX_ARG_LEN]) for k, v in args.items()]
                for k, v in rows:
                    st.code(f"{k}  →  {v}", language=None)

            result = step.get("result", "")
            if result:
                st.caption(f"Result: {str(result)[:MAX_RESULT_LEN]}   {latency:.0f}ms")

        elif step_type == "response":
            st.markdown(f"**{i}. RESPONDING**")
            tokens = step.get("output_tokens", "")
            if tokens:
                st.caption(f"Final answer generated ({tokens} output tokens)")
