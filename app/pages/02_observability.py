"""Observability dashboard — Streamlit page.

FR-OBS-07: 5-row layout reading entirely from logs/calls.jsonl (no external API).

Row 1: Metric cards — calls, avg latency, total cost, cost/1k tokens per model.
Row 2: Line chart — cost per call over time, one line per model.
Row 3: Area chart — cumulative cost since session start.
Row 4: Stacked bar — input vs output tokens per call, both models side by side.
Row 5: Safety log table — blocked calls with timestamp and category.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from observability.logger import read_calls
from observability.pricing import hours_since_fetch

st.set_page_config(page_title="Observability", layout="wide")
st.title("Observability")


def _load_df() -> pd.DataFrame:
    records = read_calls()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def render_pricing_label() -> None:
    """Show 'Prices updated N hours ago' or fallback notice (FR-OBS-02)."""
    pricing = st.session_state.get("pricing")
    if pricing is None:
        st.caption("Pricing not yet fetched — pricing will load on next chat message.")
        return
    hours = hours_since_fetch(pricing["fetched_at"])
    st.caption(f"Prices updated {hours:.1f} hours ago · source: {pricing['source']}")


def render_metric_cards(df: pd.DataFrame) -> None:
    """Row 1: metric cards for both models (FR-OBS-07)."""
    if df.empty:
        st.info("No calls logged yet. Send a message to start collecting data.")
        return

    models = df["model_id"].unique().tolist()
    cols = st.columns(len(models) * 4 or 4)
    col_idx = 0
    for model in models:
        mdf = df[df["model_id"] == model]
        short = model.split("/")[-1][:20]
        cols[col_idx].metric(f"Calls ({short})", len(mdf))
        cols[col_idx + 1].metric(
            f"Avg latency ({short})",
            f"{mdf['latency_ms'].mean():.0f} ms",
        )
        cols[col_idx + 2].metric(
            f"Total cost ({short})",
            f"${mdf['total_cost_usd'].sum():.5f}",
        )
        avg_1k = mdf["cost_per_1k_tokens"].mean()
        cols[col_idx + 3].metric(
            f"Cost/1k tokens ({short})",
            f"${avg_1k:.5f}" if avg_1k > 0 else "N/A",
        )
        col_idx += 4


def render_cost_charts(df: pd.DataFrame) -> None:
    """Row 2+3: cost per call line chart + cumulative area chart (FR-OBS-07)."""
    if df.empty:
        return

    st.subheader("Cost per call")
    cost_pivot = (
        df.assign(call_idx=df.groupby("model_id").cumcount())
        .pivot_table(index="call_idx", columns="model_id", values="total_cost_usd", aggfunc="mean")
        .reset_index(drop=True)
    )
    st.line_chart(cost_pivot)

    st.subheader("Cumulative cost")
    cum_df = pd.DataFrame(index=df.index)
    for model in df["model_id"].unique():
        mask = df["model_id"] == model
        col = df.loc[mask, "total_cost_usd"].cumsum().reindex(df.index, method="ffill").fillna(0)
        cum_df[model.split("/")[-1][:20]] = col
    st.area_chart(cum_df)


def render_token_bar(df: pd.DataFrame) -> None:
    """Row 4: stacked bar — input vs output tokens per call (FR-OBS-07)."""
    if df.empty:
        return

    st.subheader("Tokens per call (input vs output)")
    token_df = df[["input_tokens", "output_tokens"]].copy()
    token_df.columns = ["Input tokens", "Output tokens"]
    st.bar_chart(token_df)


def render_safety_log(df: pd.DataFrame) -> None:
    """Row 5: safety log table — blocked calls only (FR-OBS-07)."""
    st.subheader("Safety log")
    if df.empty:
        st.info("No calls logged yet.")
        return

    blocked = df[df["guardrail_blocked"] == True].copy()  # noqa: E712
    if blocked.empty:
        st.success("No blocked calls.")
        return

    display_cols = ["timestamp", "model_id", "block_layer", "block_reason", "block_stage",
                    "original_message_hash"]
    available = [c for c in display_cols if c in blocked.columns]
    st.dataframe(blocked[available], use_container_width=True)


df = _load_df()
render_pricing_label()
st.divider()
render_metric_cards(df)
st.divider()
render_cost_charts(df)
st.divider()
render_token_bar(df)
st.divider()
render_safety_log(df)
