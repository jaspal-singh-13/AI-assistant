"""Observability dashboard — Streamlit page.

FR-OBS-07: 5-row layout reading entirely from logs/calls.jsonl (no external API).

Row 1: Metric cards — calls, avg latency, total cost, cost/1k tokens per model.
Row 2: Line chart — cost per call over time, one line per model.
Row 3: Area chart — cumulative cost since session start.
Row 4: Stacked bar — input vs output tokens per call, both models side by side.
Row 5: Safety log table — blocked calls with timestamp and category.
"""

from __future__ import annotations

import streamlit as st

# TODO (Phase 3): uncomment once deps installed
# import pandas as pd
# from observability.logger import read_calls
# from observability.pricing import hours_since_fetch


st.set_page_config(page_title="Observability", layout="wide")
st.title("Observability")


def render_pricing_label() -> None:
    """Show 'Prices updated N hours ago' or fallback notice (FR-OBS-02)."""
    pricing = st.session_state.get("pricing")
    if pricing is None:
        st.caption("Pricing not yet fetched.")
        return
    # TODO Phase 3: hours = hours_since_fetch(pricing["fetched_at"])
    # st.caption(f"Prices updated {hours:.1f} hours ago · source: {pricing['source']}")
    st.caption("TODO Phase 3 — pricing label")


def render_metric_cards() -> None:
    """Row 1: metric cards for both models (FR-OBS-07)."""
    # TODO Phase 3: read_calls(), compute per-model stats, render with st.metric
    st.info("TODO Phase 3 — metric cards")


def render_cost_charts() -> None:
    """Row 2+3: cost per call line chart + cumulative area chart (FR-OBS-07)."""
    # TODO Phase 3: pd.DataFrame from read_calls(), st.line_chart, st.area_chart
    st.info("TODO Phase 3 — cost charts")


def render_token_bar() -> None:
    """Row 4: stacked bar — input vs output tokens per call (FR-OBS-07)."""
    # TODO Phase 3: st.bar_chart with stacked input/output columns
    st.info("TODO Phase 3 — token bar chart")


def render_safety_log() -> None:
    """Row 5: safety log table — blocked calls only (FR-OBS-07)."""
    # TODO Phase 3: filter read_calls() where guardrail_blocked=True, st.dataframe
    st.info("TODO Phase 3 — safety log")


render_pricing_label()
st.divider()
render_metric_cards()
render_cost_charts()
render_token_bar()
render_safety_log()
