"""Guardrail metadata panel component.

Renders a collapsible panel below each assistant message showing the
per-stage input and output guardrail results.

Consistent with state_panel.py — uses the same expander pattern.
Backwards-compatible: silently skips messages that predate this feature.
"""

from __future__ import annotations

import streamlit as st


def _fmt_cost(usd: float) -> str:
    """Format a USD cost value, always displayed in USD regardless of magnitude."""
    if usd == 0:
        return "$0.00"
    if usd < 0.000001:
        return f"${usd:.10f}"
    if usd < 0.0001:
        return f"${usd:.8f}"
    if usd < 0.01:
        return f"${usd:.6f}"
    return f"${usd:.4f}"


def render_guardrail_panel(metadata: dict) -> None:
    """Render the collapsible guardrail panel for one assistant message."""
    ig = metadata.get("input_guard")
    og = metadata.get("output_guard")

    if ig is None and og is None:
        return

    input_status = _status_label(ig)
    output_status = _status_label(og) if og is not None else "—"

    ig_latency = ig.get("latency_ms", 0) if ig else 0
    og_latency = og.get("latency_ms", 0) if og else 0
    total_latency = ig_latency + og_latency

    header = f"Guardrails  [{input_status} · {output_status}]  {total_latency:.0f}ms"

    with st.expander(header):
        st.markdown("**INPUT PIPELINE**")
        if ig:
            _render_stages(ig.get("stages", []))
            pii = ig.get("pii_count", 0)
            if pii and not ig.get("blocked"):
                st.caption(f"  PII note: {pii} {'entity' if pii == 1 else 'entities'} detected and redacted from logs")
        else:
            st.caption("  No input guard data")

        st.markdown("**OUTPUT PIPELINE**")
        if og is None:
            st.caption("  Not reached (input blocked)")
        else:
            _render_stages(og.get("stages", []))

        guardrail_cost = metadata.get("guardrail_cost_usd")
        if guardrail_cost is not None:
            st.caption(f"  💰 Guardrail cost: {_fmt_cost(guardrail_cost)}")


def _render_stages(stages: list[dict]) -> None:
    """Render each stage as a single captioned line."""
    if not stages:
        st.caption("  No stage data available")
        return
    for stage in stages:
        skipped = stage.get("skipped", False)
        passed = stage.get("passed", True)
        if skipped:
            icon = "⚠️"
        elif passed:
            icon = "✅"
        else:
            icon = "🚫"
        name = stage.get("name", "Unknown")
        latency = stage.get("latency_ms", 0)
        latency_str = "<1ms" if latency < 1 else f"{latency:.0f}ms"
        detail = stage.get("detail")
        line = f"  {icon}  {name}  ·  {latency_str}"
        if detail:
            line += f"  →  {detail}"
        st.caption(line)


def _status_label(guard: dict | None) -> str:
    """Return a short status string for the expander header."""
    if guard is None:
        return "—"
    if guard.get("blocked"):
        reason = guard.get("reason") or "blocked"
        return f"BLOCKED ({reason})"
    return "Passed"
