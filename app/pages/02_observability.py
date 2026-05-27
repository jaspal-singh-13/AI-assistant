"""Observability dashboard — redesigned for readability.

Layout:
  Sidebar  : model filter, call-count filter, auto-refresh
  Row 0    : pricing freshness label
  Row 1    : global summary (total calls, avg latency, total cost, block rate)
  Row 2    : per-model detail cards (one column per model)
  Tabs     : Cost · Latency · Tokens · Tools
  Bottom   : Safety log + raw-log download
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = str(Path(__file__).parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import time

import pandas as pd
import streamlit as st

from observability.logger import read_calls
from observability.pricing import hours_since_fetch

st.set_page_config(page_title="Observability", layout="wide")

# ── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    all_records = read_calls()
    all_model_ids: list[str] = sorted(
        {r["model_id"] for r in all_records} if all_records else []
    )

    selected_models: list[str] = st.multiselect(
        "Models",
        options=all_model_ids,
        default=all_model_ids,
        help="Deselect a model to hide it from all charts and cards.",
    )

    max_calls = st.slider(
        "Show last N calls (per model)",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="Limits how many calls appear in the charts. Does not affect metric totals.",
    )

    auto_refresh = st.toggle(
        "Auto-refresh (30 s)",
        value=False,
        help="Automatically reloads this page every 30 seconds so charts reflect new activity without a manual refresh.",
    )

    st.divider()
    st.caption("Logs written to `logs/calls.jsonl`")
    if all_records:
        import json
        raw_text = "\n".join(json.dumps(r) for r in all_records)
        st.download_button(
            "⬇ Download full log",
            data=raw_text,
            file_name="calls.jsonl",
            mime="application/jsonl",
        )


# ── data loading ─────────────────────────────────────────────────────────────
def _load_df(models: list[str], tail: int) -> pd.DataFrame:
    records = read_calls()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    if models:
        df = df[df["model_id"].isin(models)]
    # keep last *tail* rows per model so the slider works correctly.
    # Use groupby().tail() directly — groupby().apply() drops the grouping
    # column on pandas >= 2.2, which breaks downstream df["model_id"] access.
    df = (
        df.groupby("model_id", group_keys=False)
        .tail(tail)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    return df


df = _load_df(selected_models, max_calls)

# ── auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(30)
    st.rerun()


# ── helpers ───────────────────────────────────────────────────────────────────
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


def _short(model_id: str) -> str:
    return model_id.split("/")[-1]


# ── header ────────────────────────────────────────────────────────────────────
st.title("Observability")

pricing = st.session_state.get("pricing")
if pricing is None:
    st.caption("Pricing not yet loaded — send a message to fetch live prices.")
else:
    hours = hours_since_fetch(pricing["fetched_at"])
    st.caption(
        f"Prices updated {hours:.1f} h ago · source: `{pricing['source']}`"
    )

if df.empty:
    st.info(
        "No calls logged yet. Send a message in the Chat page to start collecting data.",
        icon="📭",
    )
    st.stop()

# ── Row 1: global summary ─────────────────────────────────────────────────────
st.subheader("Summary — all selected models")
total_calls = len(df)
avg_latency = df["latency_ms"].mean()
llm_cost = df["llm_cost_usd"].sum() if "llm_cost_usd" in df.columns else df["total_cost_usd"].sum()
guardrail_cost = df["guardrail_cost_usd"].sum() if "guardrail_cost_usd" in df.columns else 0.0
blocked = df["guardrail_blocked"].sum() if "guardrail_blocked" in df.columns else 0
block_rate = blocked / total_calls if total_calls else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Total calls",
    f"{total_calls:,}",
    help="Total number of completed LLM calls within the selected models and call-count window.",
)
c2.metric(
    "Avg latency",
    f"{avg_latency:,.0f} ms",
    help="Mean end-to-end response time — from when a message is submitted to the last token received.",
)
c3.metric(
    "LLM cost",
    _fmt_cost(llm_cost),
    help="Estimated total spend on LLM tokens (input + output) based on live provider pricing.",
)
c4.metric(
    "Guardrail cost",
    _fmt_cost(guardrail_cost),
    help="Estimated cost of running LlamaGuard safety checks on inputs and outputs. Separate from LLM cost.",
)
c5.metric(
    "Block rate",
    f"{block_rate:.1%}" if total_calls else "—",
    help="Percentage of calls where the safety guardrail blocked either the user's input or the model's output.",
)

st.divider()

# ── Row 2: per-model detail cards ─────────────────────────────────────────────
models_in_df = df["model_id"].unique().tolist()
st.subheader("Per-model breakdown")

model_cols = st.columns(len(models_in_df))
for col, model in zip(model_cols, models_in_df):
    mdf = df[df["model_id"] == model]
    with col:
        mtype = mdf["model_type"].iloc[0] if "model_type" in mdf.columns else "—"
        badge = "🔵 Frontier" if mtype == "frontier" else "🟠 OSS"
        st.markdown(f"**{_short(model)}**  \n{badge}")
        st.metric("Calls", f"{len(mdf):,}", help="Total LLM calls logged for this model in the selected window.")
        st.metric(
            "Avg latency",
            f"{mdf['latency_ms'].mean():,.0f} ms",
            help="Mean end-to-end response time for this model.",
        )
        m_llm_cost = mdf["llm_cost_usd"].sum() if "llm_cost_usd" in mdf.columns else mdf["total_cost_usd"].sum()
        st.metric("LLM cost", _fmt_cost(m_llm_cost), help="Cumulative estimated token cost for this model.")
        m_guard_cost = mdf["guardrail_cost_usd"].sum() if "guardrail_cost_usd" in mdf.columns else 0.0
        st.metric(
            "Guardrail cost",
            _fmt_cost(m_guard_cost),
            help="Cumulative cost of safety-guardrail checks run on this model's calls.",
        )
        avg_1k = mdf["cost_per_1k_tokens"].mean()
        st.metric(
            "Cost / 1k tokens",
            _fmt_cost(avg_1k / 1000) if avg_1k > 0 else "—",
            help="Average token cost per 1 000 tokens (input + output combined) at current pricing.",
        )
        blk = mdf["guardrail_blocked"].sum() if "guardrail_blocked" in mdf.columns else 0
        st.metric(
            "Blocked calls",
            f"{int(blk):,}",
            help="Number of calls where the safety guardrail blocked the input or output.",
        )
        if "tool_calls" in mdf.columns:
            all_tools = [t for row in mdf["tool_calls"] for t in (row or [])]
            st.metric(
                "Tool invocations",
                f"{len(all_tools):,}",
                help="Total number of external tool calls (e.g. weather, search) made by the agent.",
            )

st.divider()

# ── Row 3: charts in tabs ─────────────────────────────────────────────────────
tab_cost, tab_latency, tab_tokens, tab_tools = st.tabs(
    ["💰 Cost", "⏱ Latency", "🔢 Tokens", "🔧 Tools"]
)

# ── Cost tab ──────────────────────────────────────────────────────────────────
with tab_cost:
    col_a, col_b = st.columns(2)

    _has_split = "llm_cost_usd" in df.columns and "guardrail_cost_usd" in df.columns

    with col_a:
        if _has_split:
            st.markdown("**LLM vs guardrail cost per call** *(stacked)*")
            stacked_df = (
                df.assign(call_idx=df.groupby("model_id").cumcount())
                .groupby("call_idx")[["llm_cost_usd", "guardrail_cost_usd"]]
                .mean()
                .rename(columns={"llm_cost_usd": "LLM cost", "guardrail_cost_usd": "Guardrail cost"})
            )
            st.area_chart(stacked_df, height=300)
        else:
            st.markdown("**Cost per call** *(by model)*")
            cost_pivot = (
                df.assign(call_idx=df.groupby("model_id").cumcount())
                .pivot_table(
                    index="call_idx",
                    columns="model_id",
                    values="total_cost_usd",
                    aggfunc="mean",
                )
                .rename(columns=_short)
            )
            st.line_chart(cost_pivot, height=300)

    with col_b:
        st.markdown("**Cumulative cost** *(LLM vs guardrail)*")
        cum_df = pd.DataFrame(index=df.index)
        if _has_split:
            cum_df["LLM cost"] = df["llm_cost_usd"].cumsum().values
            cum_df["Guardrail cost"] = df["guardrail_cost_usd"].cumsum().values
        else:
            for model in models_in_df:
                mask = df["model_id"] == model
                col_ser = (
                    df.loc[mask, "total_cost_usd"]
                    .cumsum()
                    .reindex(df.index, method="ffill")
                    .fillna(0)
                )
                cum_df[_short(model)] = col_ser
        st.area_chart(cum_df, height=300)

# ── Latency tab ───────────────────────────────────────────────────────────────
with tab_latency:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Latency per call** *(ms)*")
        lat_pivot = (
            df.assign(call_idx=df.groupby("model_id").cumcount())
            .pivot_table(
                index="call_idx",
                columns="model_id",
                values="latency_ms",
                aggfunc="mean",
            )
            .rename(columns=_short)
        )
        st.line_chart(lat_pivot, height=300)

    with col_b:
        st.markdown("**Latency distribution** *(histogram, all calls)*")
        hist_df = pd.DataFrame(
            {"Latency (ms)": df["latency_ms"], "Model": df["model_id"].map(_short)}
        )
        for model in hist_df["Model"].unique():
            sub = hist_df[hist_df["Model"] == model]["Latency (ms)"]
            st.caption(
                f"{model} — min {sub.min():.0f} ms · "
                f"p50 {sub.median():.0f} ms · "
                f"p95 {sub.quantile(0.95):.0f} ms · "
                f"max {sub.max():.0f} ms"
            )
        st.bar_chart(
            hist_df.pivot_table(
                index=hist_df["Latency (ms)"].apply(lambda x: round(x / 200) * 200),
                columns="Model",
                aggfunc="size",
                fill_value=0,
            ),
            height=250,
        )

# ── Tokens tab ────────────────────────────────────────────────────────────────
with tab_tokens:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Input vs output tokens per call**")
        tok_df = df[["input_tokens", "output_tokens"]].copy()
        tok_df.columns = ["Input tokens", "Output tokens"]
        st.bar_chart(tok_df, height=300)

    with col_b:
        st.markdown("**Token totals by model**")
        tok_summary = (
            df.groupby("model_id")[["input_tokens", "output_tokens"]]
            .sum()
            .rename(index=_short)
            .rename(columns={"input_tokens": "Input", "output_tokens": "Output"})
        )
        st.bar_chart(tok_summary, height=300)

# ── Tools tab ─────────────────────────────────────────────────────────────────
with tab_tools:
    if "tool_calls" not in df.columns:
        st.info("No tool call data in logs.")
    else:
        all_tools_flat = [t for row in df["tool_calls"] for t in (row or [])]
        if not all_tools_flat:
            st.info("No tool calls logged yet.")
        else:
            tool_counts = (
                pd.Series(all_tools_flat)
                .value_counts()
                .rename_axis("Tool")
                .reset_index(name="Calls")
            )
            st.markdown("**Tool invocation counts**")
            st.bar_chart(tool_counts.set_index("Tool"), height=300)

            st.markdown("**Tool calls per model**")
            tool_model_rows = [
                {"model": _short(row["model_id"]), "tool": t}
                for _, row in df.iterrows()
                for t in (row.get("tool_calls") or [])
            ]
            if tool_model_rows:
                tm_df = pd.DataFrame(tool_model_rows)
                pivot = (
                    tm_df.pivot_table(
                        index="tool", columns="model", aggfunc="size", fill_value=0
                    )
                )
                st.dataframe(pivot, width='stretch')

st.divider()

# ── Safety log ────────────────────────────────────────────────────────────────
st.subheader("Safety log")

if "guardrail_blocked" not in df.columns:
    st.info("No guardrail data in logs.")
else:
    blocked_df = df[df["guardrail_blocked"] == True].copy()  # noqa: E712
    if blocked_df.empty:
        st.success("No blocked calls in the selected window.", icon="✅")
    else:
        st.warning(
            f"{len(blocked_df)} blocked call(s) — {len(blocked_df)/total_calls:.1%} of selected calls",
            icon="🚨",
        )
        display_cols = [
            "timestamp", "model_id", "block_stage", "block_layer",
            "block_reason", "original_message_hash",
        ]
        available = [c for c in display_cols if c in blocked_df.columns]
        rename_map = {
            "timestamp": "Time (UTC)",
            "model_id": "Model",
            "block_stage": "Stage",
            "block_layer": "Layer",
            "block_reason": "Reason",
            "original_message_hash": "Message hash (SHA-256)",
        }
        st.dataframe(
            blocked_df[available].rename(columns=rename_map),
            width='stretch',
            column_config={
                "Time (UTC)": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
            },
        )
