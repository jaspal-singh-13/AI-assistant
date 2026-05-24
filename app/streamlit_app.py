"""Dashboard — home page for the AI Assistant Comparison app.

Shows high-level KPIs, per-model call stats, a condensed observability
snapshot, and an evaluation scorecard overview.

Read-only: does not initialise the agent graph or write any data.

Run with: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_repo_root = str(Path(__file__).parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv
load_dotenv()

import logging
import os

from observability.logger import configure_logging
configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logging.getLogger("transformers").setLevel(logging.ERROR)

import pandas as pd
import streamlit as st

from observability.logger import read_calls
from memory.manager import list_threads

_ROOT = Path(__file__).parent.parent
_SCORES_FILE = _ROOT / "evaluation" / "results" / "model_scores.json"

# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_cost(usd: float) -> str:
    if usd == 0:
        return "$0.00"
    if usd < 0.0001:
        return f"${usd * 1_000_000:.2f} μ$"
    if usd < 0.01:
        return f"${usd * 1000:.3f} m$"
    return f"${usd:.4f}"


def _short(model_id: str) -> str:
    return model_id.split("/")[-1]


def _load_scores() -> dict | None:
    if not _SCORES_FILE.exists():
        return None
    try:
        return json.loads(_SCORES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Dashboard")
st.caption("AI Assistant Comparison — Claude Haiku vs Qwen 2.5 7B")

# ── load data ─────────────────────────────────────────────────────────────────

all_records = read_calls()
threads = list_threads()

try:
    from agent.models import list_models
    configured_models = list_models()
except Exception:
    configured_models = []

# ── Row 1: Top KPI cards ──────────────────────────────────────────────────────

st.subheader("Overview")

total_threads = len(threads)
total_calls = len(all_records)
total_cost = sum(r.get("total_cost_usd", 0.0) for r in all_records)
avg_latency = (
    sum(r.get("latency_ms", 0.0) for r in all_records) / total_calls
    if total_calls else 0.0
)
blocked = sum(1 for r in all_records if r.get("guardrail_blocked"))
block_rate = blocked / total_calls if total_calls else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Threads", f"{total_threads:,}")
c2.metric("Total calls", f"{total_calls:,}")
c3.metric("Total cost", _fmt_cost(total_cost))
c4.metric("Avg latency", f"{avg_latency:,.0f} ms" if total_calls else "—")
c5.metric("Block rate", f"{block_rate:.1%}" if total_calls else "—")

st.divider()

# ── Row 2: Per-model cards ─────────────────────────────────────────────────────

st.subheader("Models")

if configured_models:
    model_cols = st.columns(len(configured_models))
    for col, (key, cfg) in zip(model_cols, configured_models):
        model_records = [r for r in all_records if r.get("model_id") == cfg.model_id]
        badge = "🔵 Frontier" if cfg.model_type == "frontier" else "🟠 OSS"
        m_cost = sum(r.get("total_cost_usd", 0.0) for r in model_records)
        m_lat = (
            sum(r.get("latency_ms", 0.0) for r in model_records) / len(model_records)
            if model_records else 0.0
        )
        with col:
            st.markdown(f"**{cfg.model_label}** &nbsp; {badge}")
            st.metric("Calls", f"{len(model_records):,}")
            st.metric("Total cost", _fmt_cost(m_cost))
            st.metric("Avg latency", f"{m_lat:,.0f} ms" if model_records else "—")
else:
    st.info("No models configured. Check your `.env` for `MODELS_*` entries.", icon="⚙️")

st.divider()

# ── Row 3: Observability snapshot ─────────────────────────────────────────────

st.subheader("Observability Snapshot")

if not all_records:
    st.info(
        "No calls logged yet. Go to the **Chat** page and send a message to start collecting data.",
        icon="📭",
    )
else:
    df = pd.DataFrame(all_records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # last 50 calls for the snapshot chart
    snap_df = df.tail(50)

    col_chart, col_info = st.columns([3, 1])

    with col_chart:
        st.markdown("**Cumulative cost — last 50 calls**")
        models_in_df = snap_df["model_id"].unique().tolist()
        cum_df = pd.DataFrame(index=snap_df.index)
        for model in models_in_df:
            mask = snap_df["model_id"] == model
            cum_df[_short(model)] = (
                snap_df.loc[mask, "total_cost_usd"]
                .cumsum()
                .reindex(snap_df.index, method="ffill")
                .fillna(0)
            )
        st.area_chart(cum_df, height=200)

    with col_info:
        st.markdown("**Recent activity**")
        for model in models_in_df:
            mdf = snap_df[snap_df["model_id"] == model]
            st.markdown(
                f"<small><b>{_short(model)}</b><br>"
                f"{len(mdf)} calls &nbsp;·&nbsp; {_fmt_cost(mdf['total_cost_usd'].sum())}</small>",
                unsafe_allow_html=True,
            )
        st.markdown("")
        st.page_link("pages/02_observability.py", label="→ Full Observability", icon="📈")

st.divider()

# ── Row 4: Evaluation snapshot ────────────────────────────────────────────────

st.subheader("Evaluation Snapshot")

scores_data = _load_scores()

if scores_data is None:
    st.info(
        "No evaluation results yet. Run `make eval` from the CLI or go to the **Evaluation** page.",
        icon="🧪",
    )
else:
    generated_at = scores_data.get("generated_at", "unknown")
    models_data: dict = scores_data.get("models", {})
    st.caption(f"Last run: {generated_at}")

    _NEGATIVE_DIMS = {"hallucination", "bias_harmful"}
    _DIM_LABELS = {
        "hallucination": "Hallucination ↓",
        "bias_harmful": "Bias & Harmful ↓",
        "content_safety": "Content Safety ↑",
    }

    # Build a compact table: rows = models, cols = dimensions
    rows = []
    for mid, dim_scores in models_data.items():
        row: dict = {"Model": mid}
        for dim, label in _DIM_LABELS.items():
            dim_data = dim_scores.get(dim, {})
            pass_rate = dim_data.get("pass_rate")
            if pass_rate is None:
                row[label] = "—"
            elif dim in _NEGATIVE_DIMS:
                row[label] = f"{round((1 - pass_rate) * 100, 1)}%"
            else:
                row[label] = f"{round(pass_rate * 100, 1)}%"
        rows.append(row)

    if rows:
        score_df = pd.DataFrame(rows).set_index("Model")
        st.dataframe(score_df, width=None)

    st.page_link("pages/03_evaluation.py", label="→ Full Evaluation", icon="🔬")
