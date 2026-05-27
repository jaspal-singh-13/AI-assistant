"""Evaluation Dashboard — scorecard, run eval, prompt browser, results.

Layout:
  Tab 1 — Dashboard   : model scorecard from model_scores.json + charts
  Tab 2 — Run Eval    : config panel, prompt filter, live subprocess output
  Tab 3 — Prompts & Results : browse/add prompts, summary.csv, comparative.csv
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

_repo_root = str(Path(__file__).parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Evaluation", layout="wide")

_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = _ROOT / "evaluation" / "results"
_PROMPTS_DIR = _ROOT / "evaluation" / "prompts"
_SCORES_FILE = _RESULTS_DIR / "model_scores.json"
_SUMMARY_FILE = _RESULTS_DIR / "summary.csv"
_COMPARATIVE_FILE = _RESULTS_DIR / "comparative.csv"
_BAR_CHART = _RESULTS_DIR / "bar_chart.png"
_RADAR_CHART = _RESULTS_DIR / "radar_chart.png"

_CATEGORY_LABELS = {
    "factual": "Factual",
    "adversarial": "Adversarial",
    "bias_sensitive": "Bias & Sensitive",
}
_DIMENSION_LABELS = {
    "hallucination": "Hallucination",
    "bias_harmful": "Bias & Harmful",
    "content_safety": "Content Safety",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_scores() -> dict | None:
    if not _SCORES_FILE.exists():
        return None
    try:
        return json.loads(_SCORES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_prompts() -> list[dict]:
    prompts: list[dict] = []
    for json_file in sorted(_PROMPTS_DIR.glob("*.json")):
        try:
            items = json.loads(json_file.read_text(encoding="utf-8"))
            prompts.extend(items)
        except Exception:
            pass
    return prompts


def _available_models() -> list[str]:
    try:
        sys.path.insert(0, str(_ROOT))
        from agent.models import list_models
        return [key for key, _ in list_models()]
    except Exception:
        return []


def _load_summary_csv() -> pd.DataFrame | None:
    if not _SUMMARY_FILE.exists():
        return None
    try:
        return pd.read_csv(_SUMMARY_FILE)
    except Exception:
        return None


_METRIC_LABELS = {
    "hallucination": "Hallucination",
    "bias": "Bias",
    "toxicity": "Toxicity",
    "jailbreak_resistance": "Jailbreak Resistance",
    "refusal_quality": "Refusal Quality",
}

# Metrics where a higher score is better (green). All others are lower-is-better (red).
_HIGHER_IS_BETTER = {"jailbreak_resistance", "refusal_quality"}


def _style_pivot(pivot: "pd.DataFrame"):
    """Apply per-column polarity-aware gradient: green=good, red=bad.

    Uses explicit matplotlib colormap objects and Styler.apply() to avoid
    the pandas background_gradient quirk where RdYlGn_r string is silently
    ignored in some pandas/Streamlit versions.
    """
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors

    rdylgn = cm.get_cmap("RdYlGn")
    rdylgn_r = rdylgn.reversed()
    norm = mcolors.Normalize(vmin=0, vmax=1)

    def _col_colors(series: "pd.Series", metric_name: str) -> list[str]:
        cmap = rdylgn if metric_name in _HIGHER_IS_BETTER else rdylgn_r
        return [
            f"background-color: {mcolors.to_hex(cmap(norm(v)))}"
            for v in series
        ]

    styler = pivot.style
    for col in pivot.columns:
        styler = styler.apply(_col_colors, metric_name=col, subset=[col])
    return styler

_MODEL_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]


def _chart_all_metrics(df: pd.DataFrame) -> alt.Chart:
    """Interactive horizontal grouped bar chart — all metrics, both models.

    All bars are normalised so longer = better:
      - higher-is-better metrics (jailbreak_resistance, refusal_quality): raw score used as-is
      - lower-is-better metrics (hallucination, bias, toxicity): displayed as 1 - raw_score
    The tooltip shows the original raw score so the user can verify against model_scores.json.
    """
    df = df[df["low_confidence"].astype(str).str.lower() != "true"].copy()
    avg = df.groupby(["model_id", "metric"])["score"].mean().reset_index()
    avg["score"] = avg["score"].round(3)

    # Normalise to a performance scale where 1 = best for every metric
    avg["perf_score"] = avg.apply(
        lambda r: r["score"] if r["metric"] in _HIGHER_IS_BETTER else round(1 - r["score"], 3),
        axis=1,
    )

    avg["metric_label"] = avg["metric"].map(lambda m: _METRIC_LABELS.get(m, m))
    avg["raw_label"] = avg.apply(
        lambda r: f"Raw: {r['score']:.3f}" + ("" if r["metric"] in _HIGHER_IS_BETTER else " (inverted)"),
        axis=1,
    )

    models = sorted(avg["model_id"].unique().tolist())
    color_scale = alt.Scale(domain=models, range=_MODEL_COLORS[: len(models)])

    base = alt.Chart(avg).encode(
        y=alt.Y(
            "metric_label:N",
            sort=alt.EncodingSortField("perf_score", op="mean", order="descending"),
            title=None,
            axis=alt.Axis(labelFontSize=13),
        ),
        color=alt.Color("model_id:N", scale=color_scale, title="Model"),
        tooltip=[
            alt.Tooltip("model_id:N", title="Model"),
            alt.Tooltip("metric_label:N", title="Metric"),
            alt.Tooltip("perf_score:Q", title="Performance (↑ better)", format=".3f"),
            alt.Tooltip("raw_label:N", title="Original score"),
        ],
    )

    bars = base.mark_bar().encode(
        x=alt.X(
            "perf_score:Q",
            scale=alt.Scale(domain=[0, 1]),
            title="Performance Score (higher = better for all metrics)",
            axis=alt.Axis(grid=True, format=".1f"),
        ),
        yOffset="model_id:N",
    )

    labels = base.mark_text(align="left", dx=4, fontSize=11).encode(
        x=alt.X("perf_score:Q", scale=alt.Scale(domain=[0, 1])),
        yOffset="model_id:N",
        text=alt.Text("perf_score:Q", format=".2f"),
    )

    rule = alt.Chart(pd.DataFrame({"x": [0.5]})).mark_rule(
        color="gray", strokeDash=[4, 4], opacity=0.6
    ).encode(x="x:Q")

    return (
        (bars + labels + rule)
        .properties(title="All Metrics — Model Comparison", height=300)
        .configure_view(strokeWidth=0)
        .configure_title(fontSize=15, anchor="start")
        .configure_legend(labelFontSize=12, titleFontSize=12)
        .interactive()
    )


# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────

def render_dashboard() -> None:
    scores_data = _load_scores()

    if scores_data is None:
        st.info("No results found yet. Go to **Run Evaluation** to generate them.")
        return

    generated_at = scores_data.get("generated_at", "unknown")
    models_data: dict = scores_data.get("models", {})
    model_ids = list(models_data.keys())

    st.caption(f"Last run: {generated_at}")

    # ── Scorecard ─────────────────────────────────────────────────────────────
    # Hallucination and Bias & Harmful are displayed as failure rates (lower = better).
    # Content Safety is displayed as a pass rate (higher = better).
    _NEGATIVE_DIMS = {"hallucination", "bias_harmful"}

    st.subheader("Model Scorecard")
    st.caption(
        "Each dimension is scored by running the evaluation prompts through DeepEval metrics. "
        "Hover the **?** icon on any model score for raw metric details."
    )
    dimensions = ["hallucination", "bias_harmful", "content_safety"]
    dim_cols = st.columns(len(dimensions))

    for dim_col, dim in zip(dim_cols, dimensions):
        with dim_col:
            is_negative = dim in _NEGATIVE_DIMS
            if is_negative:
                header = f"**{_DIMENSION_LABELS[dim]} Rate** ↓ lower is better"
            else:
                header = f"**{_DIMENSION_LABELS[dim]} Pass Rate** ↑ higher is better"
            st.markdown(header)

            for model_id in model_ids:
                dim_data = models_data.get(model_id, {}).get(dim, {})
                pass_rate = dim_data.get("pass_rate", 0.0)
                low_conf = dim_data.get("low_confidence_excluded", 0)

                # For negative dims show failure rate; for positive show pass rate
                display_pct = round((1 - pass_rate) * 100, 1) if is_negative else round(pass_rate * 100, 1)

                # Secondary detail lines (raw deepeval scores in tooltip)
                detail_parts = [f"Pass rate: {round(pass_rate * 100, 1)}%"]
                if dim == "hallucination":
                    detail_parts.append(f"DeepEval hallucination score: {dim_data.get('deepeval_score', 0):.3f}")
                elif dim == "bias_harmful":
                    detail_parts.append(f"Bias score: {dim_data.get('deepeval_bias_score', 0):.3f}")
                    detail_parts.append(f"Toxicity score: {dim_data.get('deepeval_toxicity_score', 0):.3f}")
                elif dim == "content_safety":
                    detail_parts.append(f"Jailbreak resistance: {dim_data.get('deepeval_jailbreak_score', 0):.3f}")
                    detail_parts.append(f"Refusal quality: {dim_data.get('deepeval_refusal_quality_score', 0):.3f}")
                if low_conf:
                    detail_parts.append(f"⚠ {low_conf} low-confidence excluded")

                st.metric(
                    label=model_id,
                    value=f"{display_pct}%",
                    help=" · ".join(detail_parts),
                )

    st.divider()

    # ── Chart ─────────────────────────────────────────────────────────────────
    summary_df = _load_summary_csv()

    if summary_df is not None and not summary_df.empty:
        st.altair_chart(_chart_all_metrics(summary_df), width='stretch')
    else:
        st.info("No summary data found — run an evaluation first.")

    # ── Per-model detail expander ─────────────────────────────────────────────
    with st.expander("Full JSON scorecard"):
        st.json(models_data)


# ── Tab 2: Run Evaluation ─────────────────────────────────────────────────────

def _start_eval(cmd: list[str]) -> None:
    """Launch eval subprocess; stream output into a plain list shared with the thread."""
    output_buf: list[str] = []
    st.session_state["eval_output"] = output_buf
    st.session_state["eval_running"] = True
    st.session_state["eval_exit_code"] = None

    def _run(buf: list[str]) -> None:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(_ROOT),
        )
        st.session_state["eval_proc"] = proc
        for line in proc.stdout:  # type: ignore[union-attr]
            buf.append(line.rstrip())
        proc.wait()
        # Write primitives back via a flag list to avoid session state access from thread
        buf.append(f"__exit_code__:{proc.returncode}")

    t = threading.Thread(target=_run, args=(output_buf,), daemon=True)
    t.start()


def render_run_eval() -> None:
    # Init session state keys
    if "eval_running" not in st.session_state:
        st.session_state["eval_running"] = False
    if "eval_output" not in st.session_state:
        st.session_state["eval_output"] = []
    if "eval_exit_code" not in st.session_state:
        st.session_state["eval_exit_code"] = None

    all_prompts = _load_prompts()
    available_models = _available_models()

    left, right = st.columns([1, 1], gap="large")

    # ── Config ────────────────────────────────────────────────────────────────
    with left:
        st.subheader("Configuration")

        selected_models = st.multiselect(
            "Models",
            options=available_models,
            default=available_models,
            help="Models to evaluate. Must match keys defined in .env.",
        )

        category = st.selectbox(
            "Prompt category",
            options=["all", "factual", "adversarial", "bias_sensitive"],
            format_func=lambda x: "All categories" if x == "all" else _CATEGORY_LABELS.get(x, x),
            help=(
                "Filter which evaluation prompts are run:\n\n"
                "• **Factual** — questions with a known correct answer; tests hallucination.\n\n"
                "• **Adversarial** — jailbreak attempts, prompt injections; tests safety & refusal quality.\n\n"
                "• **Bias & Sensitive** — prompts touching race, gender, religion; tests for biased or toxic output.\n\n"
                "• **All categories** — runs every prompt across all three categories."
            ),
        )

        col_a, col_b = st.columns(2)
        with col_a:
            light_mode = st.toggle("Light mode", value=True, help="3 prompts per category (9 total)")
            skip_judge = st.toggle("Skip judge", value=False, help="Skip LLM-as-judge (faster)")
        with col_b:
            skip_benchmarks = st.toggle(
                "Skip benchmarks",
                value=True,
                help=(
                    "When enabled (default), skips running external benchmark datasets "
                    "(e.g. TruthfulQA, MMLU). "
                    "Disable only when you want a full benchmark sweep — it adds significant runtime."
                ),
            )
            # workers = st.slider("Workers", min_value=1, max_value=5, value=1)
            workers = 1

        seed = st.number_input(
            "Seed",
            min_value=0,
            value=42,
            step=1,
            help=(
                "Random seed passed to the evaluation pipeline. "
                "Using the same seed across runs ensures identical prompt-sampling order, "
                "making results reproducible and directly comparable."
            ),
        )

    # ── Prompt filter ─────────────────────────────────────────────────────────
    with right:
        st.subheader("Prompt Filter")
        st.caption("Leave empty to use the configuration above. Select specific IDs to override.")

        # Group prompt IDs by category for readable labels
        by_cat: dict[str, list[str]] = {}
        for p in all_prompts:
            cat = p.get("category", "unknown")
            by_cat.setdefault(cat, []).append(p["id"])

        prompt_options: list[str] = []
        for cat in ["factual", "adversarial", "bias_sensitive"]:
            for pid in by_cat.get(cat, []):
                prompt_options.append(pid)

        selected_ids: list[str] = st.multiselect(
            "Specific prompt IDs",
            options=prompt_options,
            default=[],
            help="Selected prompts will be run regardless of category/light settings.",
        )

        if selected_ids:
            st.info(f"{len(selected_ids)} prompt(s) selected — will pass `--prompt-ids`")

        # Preview selected prompts
        if selected_ids:
            preview = [p for p in all_prompts if p["id"] in selected_ids]
            with st.expander(f"Preview selected prompts ({len(preview)})"):
                for p in preview:
                    st.markdown(f"**{p['id']}** `{p.get('category', '')}` — {p.get('prompt', '')[:120]}")

    st.divider()

    # ── Run button ────────────────────────────────────────────────────────────
    run_col, status_col = st.columns([1, 3])
    with run_col:
        run_disabled = st.session_state["eval_running"] or not selected_models
        if st.button("Run Evaluation", type="primary", disabled=run_disabled, width='stretch'):
            cmd = [sys.executable, "evaluation/run_eval.py"]
            cmd += ["--models"] + selected_models
            cmd += ["--seed", str(seed)]
            cmd += ["--workers", str(workers)]
            if category != "all":
                cmd += ["--prompt-category", category]
            if light_mode and not selected_ids:
                cmd.append("--light")
            if skip_judge:
                cmd.append("--skip-judge")
            if skip_benchmarks:
                cmd.append("--skip-benchmarks")
            if selected_ids:
                cmd += ["--prompt-ids"] + selected_ids
            _start_eval(cmd)
            st.rerun()

    with status_col:
        # Derive status from the shared buffer — no thread writes to session_state
        output_lines: list[str] = st.session_state.get("eval_output", [])
        exit_sentinel = next(
            (l for l in output_lines if l.startswith("__exit_code__:")), None
        )
        if exit_sentinel:
            # Process finished — update session state from the main thread
            exit_code = int(exit_sentinel.split(":")[1])
            st.session_state["eval_running"] = False
            st.session_state["eval_exit_code"] = exit_code

        if st.session_state["eval_running"]:
            st.info("Evaluation running…")
        elif st.session_state["eval_exit_code"] is not None:
            if st.session_state["eval_exit_code"] == 0:
                st.success("Evaluation completed successfully. Refresh the Dashboard tab to see updated results.")
            else:
                st.error(f"Evaluation failed (exit code {st.session_state['eval_exit_code']}).")

    # ── Live output ───────────────────────────────────────────────────────────
    output_lines = st.session_state.get("eval_output", [])
    # Strip the internal sentinel line before display
    display_lines = [l for l in output_lines if not l.startswith("__exit_code__:")]
    if display_lines or st.session_state["eval_running"]:
        st.subheader("Live Output")

        # ── Progress bar parsed from log lines ────────────────────────────────
        import re
        total_match = None
        completed = 0
        stage = "Starting…"

        for line in display_lines:
            # e.g. "load_prompts | done | n=45"  (before --prompt-ids / --light filter)
            m = re.search(r"load_prompts \| done \| n=(\d+)", line)
            if m:
                total_match = int(m.group(1))

            # e.g. "processing 3 prompts with 1 workers"  (after all filters applied)
            # overrides the pre-filter count so the progress bar reflects reality
            m2 = re.search(r"processing (\d+) prompts with", line)
            if m2:
                total_match = int(m2.group(1))

            # e.g. "prompt | [2/9] factual_001"  or "prompt | cached | [2/9] ..."
            if re.search(r"prompt \|.*\[\d+/\d+\]", line):
                completed += 1

            # Stage detection (last match wins)
            if "eval pipeline start" in line:
                stage = "Initialising…"
            elif "load_prompts | done" in line:
                stage = "Prompts loaded"
            elif "processing" in line and "prompts with" in line:
                stage = "Running prompts…"
            elif "aggregate | start" in line:
                stage = "Aggregating results…"
            elif "aggregate | done" in line:
                stage = "Writing CSV files…"
            elif "charts | generating" in line:
                stage = "Generating charts…"
            elif "charts | done" in line:
                stage = "Syncing to LangSmith…"
            elif "eval pipeline done" in line:
                stage = "Done"

        if total_match and total_match > 0:
            progress = min(completed / total_match, 1.0)
            st.progress(progress, text=f"{stage}  ({completed} / {total_match} prompts)")
        elif st.session_state["eval_running"]:
            st.progress(0.0, text=stage)

        tail = display_lines[-40:] if len(display_lines) > 40 else display_lines
        st.code("\n".join(tail) if tail else "Starting…", language="text")

        if st.session_state["eval_running"]:
            time.sleep(1.5)
            st.rerun()


# ── Tab 3: Prompts & Results ──────────────────────────────────────────────────

def render_prompts_and_results() -> None:
    sub_tabs = st.tabs(["Browse Prompts", "Add Custom Prompt", "Summary", "Comparative"])

    # ── Browse Prompts ────────────────────────────────────────────────────────
    with sub_tabs[0]:
        all_prompts = _load_prompts()
        if not all_prompts:
            st.warning("No prompts found in evaluation/prompts/")
            return

        categories = ["All"] + sorted({p.get("category", "") for p in all_prompts})
        cat_filter = st.selectbox("Filter by category", categories, key="browse_cat_filter")

        filtered = all_prompts if cat_filter == "All" else [p for p in all_prompts if p.get("category") == cat_filter]

        df = pd.DataFrame([
            {
                "ID": p.get("id", ""),
                "Category": p.get("category", ""),
                "Prompt": p.get("prompt", "")[:120] + ("…" if len(p.get("prompt", "")) > 120 else ""),
                "Expected Output": (p.get("expected_output") or "")[:80],
                "Has Context": bool(p.get("context")),
            }
            for p in filtered
        ])

        st.caption(f"{len(df)} prompts")
        st.dataframe(df, width='stretch', hide_index=True)

    # ── Add Custom Prompt ─────────────────────────────────────────────────────
    with sub_tabs[1]:
        st.markdown("Add a custom prompt to the evaluation suite. It will be appended to the matching category JSON file.")

        with st.form("add_prompt_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_id = st.text_input("Prompt ID", placeholder="e.g. factual_custom_001")
                new_category = st.selectbox("Category", ["factual", "adversarial", "bias_sensitive"])
            with col2:
                new_expected = st.text_input(
                    "Expected Output (optional)",
                    help=(
                        "The ideal reference answer for this prompt. "
                        "Used by the LLM judge to score factual accuracy. "
                        "Leave blank for adversarial or open-ended prompts."
                    ),
                )
                new_context = st.text_area(
                    "Context (optional)",
                    height=80,
                    help=(
                        "Background text the model should use to answer the prompt "
                        "(e.g. a document excerpt for RAG-style questions). "
                        "Leave blank for prompts that don't need grounding context."
                    ),
                )

            new_prompt = st.text_area("Prompt text *", height=100, placeholder="Enter the prompt…")
            submitted = st.form_submit_button("Add Prompt", type="primary")

        if submitted:
            if not new_id.strip() or not new_prompt.strip():
                st.error("Prompt ID and prompt text are required.")
            else:
                target_file = _PROMPTS_DIR / f"{new_category}.json"
                try:
                    existing = json.loads(target_file.read_text(encoding="utf-8")) if target_file.exists() else []
                    if any(p.get("id") == new_id.strip() for p in existing):
                        st.error(f"A prompt with ID '{new_id.strip()}' already exists in {new_category}.json")
                    else:
                        entry: dict = {
                            "id": new_id.strip(),
                            "category": new_category,
                            "prompt": new_prompt.strip(),
                        }
                        if new_context.strip():
                            entry["context"] = new_context.strip()
                        if new_expected.strip():
                            entry["expected_output"] = new_expected.strip()
                        existing.append(entry)
                        target_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
                        st.success(f"Added '{new_id.strip()}' to {new_category}.json")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Failed to save prompt: {exc}")

    # ── Summary CSV ───────────────────────────────────────────────────────────
    with sub_tabs[2]:
        if not _SUMMARY_FILE.exists():
            st.info("No summary.csv found. Run an evaluation first.")
        else:
            st.caption(
                "Per-prompt, per-metric raw scores from the last evaluation run. "
                "The pivot table shows mean scores: green = good, red = bad "
                "(polarity is aware — lower hallucination is green, higher jailbreak resistance is green)."
            )
            df_sum = pd.read_csv(_SUMMARY_FILE)

            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                model_filter = st.multiselect(
                    "Filter by model",
                    options=sorted(df_sum["model_id"].unique()),
                    default=sorted(df_sum["model_id"].unique()),
                    key="sum_model_filter",
                )
            with filter_col2:
                metric_filter = st.multiselect(
                    "Filter by metric",
                    options=sorted(df_sum["metric"].unique()),
                    default=sorted(df_sum["metric"].unique()),
                    key="sum_metric_filter",
                )

            df_filtered = df_sum[df_sum["model_id"].isin(model_filter) & df_sum["metric"].isin(metric_filter)]

            # Mean scores summary
            st.markdown("**Mean scores per model × metric**")
            pivot = df_filtered.groupby(["model_id", "metric"])["score"].mean().round(4).unstack(fill_value=0)
            st.dataframe(_style_pivot(pivot), width='stretch')

            st.divider()
            st.caption(f"{len(df_filtered)} rows")
            st.dataframe(df_filtered, width='stretch', hide_index=True)
            st.download_button("Download summary.csv", df_filtered.to_csv(index=False), "summary.csv", "text/csv")

    # ── Comparative CSV ───────────────────────────────────────────────────────
    with sub_tabs[3]:
        if not _COMPARATIVE_FILE.exists():
            st.info("No comparative.csv found. Run an evaluation with the judge enabled.")
        else:
            st.caption(
                "Head-to-head comparison produced by the LLM judge. "
                "For each prompt the judge reads both models' responses and declares a **winner** "
                "(model A, model B, or **tie**). Requires **Skip judge** to be off during the eval run."
            )
            df_comp = pd.read_csv(_COMPARATIVE_FILE)

            winner_filter = st.multiselect(
                "Filter by winner",
                options=sorted(df_comp["winner"].unique()) if "winner" in df_comp.columns else [],
                default=sorted(df_comp["winner"].unique()) if "winner" in df_comp.columns else [],
                key="comp_winner_filter",
            )
            df_comp_f = df_comp[df_comp["winner"].isin(winner_filter)] if "winner" in df_comp.columns else df_comp

            # Colour-code winner column
            def _highlight_winner(row: pd.Series) -> list[str]:
                styles = [""] * len(row)
                if "winner" in row.index:
                    w = row["winner"]
                    idx = row.index.get_loc("winner")
                    if w == "tie":
                        styles[idx] = "color: grey"
                    else:
                        styles[idx] = "font-weight: bold"
                return styles

            st.caption(f"{len(df_comp_f)} comparisons")
            st.dataframe(
                df_comp_f.style.apply(_highlight_winner, axis=1),
                width='stretch',
                hide_index=True,
            )
            st.download_button("Download comparative.csv", df_comp_f.to_csv(index=False), "comparative.csv", "text/csv")


# ── Main ──────────────────────────────────────────────────────────────────────

st.title("Evaluation")

tab_dashboard, tab_run, tab_results = st.tabs(["Dashboard", "Run Evaluation", "Prompts & Results"])

with tab_dashboard:
    render_dashboard()

with tab_run:
    render_run_eval()

with tab_results:
    render_prompts_and_results()
