# AI Assistant Comparison

Two AI assistants — one powered by **Claude Sonnet** (frontier), one by **Qwen 2.5 0.5B** (open-source) — evaluated on hallucination, bias, and content safety.

> **Status:** Boilerplate scaffold — implementation in progress (see [TODO.md](TODO.md)).

---

## Public URLs

| Service | URL |
|---|---|
| Streamlit App | _TODO — deploy Phase 4_ |
| HF Spaces (Qwen) | _TODO — deploy Phase 4_ |

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd ai-assistant-comparison
pip install -r requirements.txt

# 2. Copy env template and fill in keys
cp .env.example .env

# 3. Run the app
make run

# 4. Run evaluations (Phase 4)
make eval
```

---

## Architecture

```
User
 │
 ▼
Streamlit UI
 ├── Sidebar: threads · model selector · context window slider
 ├── Chat window: all messages, model badge per message, switch divider
 ├── State panel: LangGraph steps + tool call variable inspection
 └── Observability tab: real-time cost charts · latency · safety log
 │
 ▼
Input guardrails pipeline
  Rebuff → LlamaGuard 3 → Presidio
 │
 ▼
LangGraph ReAct agent  ← swappable LLM, same graph
 ├── LLM context: sliding window + incremental summary
 └── Tools: time · weather · search · metrics
 │
 └── graph.stream(stream_mode=["updates", "messages"])
     ├── "messages" → token streaming to UI
     └── "updates"  → step state for state panel
 │
 ▼
Output guardrails pipeline
  Guardrails AI validators → LlamaGuard 3 re-check → NeMo topical rails
 │
 ▼
Observability logger → logs/calls.jsonl
 ├── Langfuse (cost, latency, token tracking)
 └── LangSmith (trace storage, experiment dataset)
```

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Agent framework | LangGraph `create_react_agent` | One graph for both models, built-in tool loop |
| Streaming | Sync `graph.stream()` + `nest_asyncio` | Simplest Streamlit integration |
| Memory | Sliding window + incremental summarisation | LLM never re-reads old messages |
| Summarisation | Summary-of-summary approach | Cheap per call, survives restarts |
| Model metadata | Per-message in thread JSON | Full audit trail, badge display, cost attribution |
| Pricing | LiteLLM JSON fetched live, 24hr cache | Always current, no manual updates |
| Judge debiasing | Position swap — run every comparison twice | Eliminates largest source of LLM judge noise |
| Input guard order | Rebuff (5ms) → LlamaGuard (300ms) → Presidio (local) | Cheapest check first |
| OSS hosting | HF Spaces CPU free tier | Free, public URL, meets assignment requirement |

---

## Evaluation

Both models are compared across three dimensions. See [EVALUATION.md](EVALUATION.md) for the complete metric definitions, prompt sets, and storage schema.

| Dimension | What it measures | Key metrics | Storage |
|---|---|---|---|
| **Hallucination Rate** | Factual accuracy, fabrication | HallucinationMetric, TruthfulQA accuracy, judge rubric | `summary.csv`, `model_scores.json` |
| **Bias & Harmful Outputs** | Stereotypes, discriminatory framing, toxicity | BiasMetric, ToxicityMetric, BBQ accuracy, judge rubric | `summary.csv`, `model_scores.json` |
| **Content Safety** | Jailbreak resistance, refusal quality | GEval(jailbreak), GEval(refusal), guardrail block rate, Promptfoo redteam | `summary.csv`, `model_scores.json`, `calls.jsonl` |

Scores for both models are written to `evaluation/results/model_scores.json` after each `make eval` run. Adding a third model requires only one entry in `agent/models.py` — all score files are keyed by `model_id`.

---

## Tradeoffs

- **Sync vs async streaming:** Using sync `graph.stream()` blocks the Streamlit thread ~2–5s per response. Acceptable for a demo; async SSE would be better for production.
- **Qwen 2.5 0.5B on CPU:** ~8–12s per call on HF Spaces free tier. Shows a loading spinner. GPU tier would reduce this to ~1–2s but costs money.
- **LlamaGuard 3 via HF Inference API:** ~300ms latency. Using a local model would be faster but requires GPU memory.
- **Incremental summarisation:** Slightly stale summaries possible (only updates when a full window of messages goes uncovered). Acceptable tradeoff for cost savings.

---

## What I Would Improve With More Time

1. **Async streaming** with a FastAPI SSE layer for true token-by-token display.
2. **Persistent Langfuse** traces with a dedicated project per eval run.
3. **Fine-tuning Qwen** on a domain-specific dataset to close the quality gap.
4. **Multi-user support** with proper auth and per-user thread isolation.
5. **Eval caching** to skip already-scored (model, prompt) pairs on re-runs.
6. **Automated red-team loop** that generates new adversarial prompts based on previous failures.

---

## Cost + Latency Table

_TODO — populate after Phase 3 observability is live._

| Model | Avg Latency | Avg Input Tokens | Avg Output Tokens | Cost / Call | Cost / 1k Tokens |
|---|---|---|---|---|---|
| Claude Sonnet | — | — | — | — | — |
| Qwen 2.5 0.5B | — | — | — | $0 billed / equiv $X | — |

---

## Environment Variables

| Variable | Required | Source |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | console.anthropic.com |
| `HUGGINGFACE_TOKEN` | Yes | huggingface.co/settings/tokens |
| `LANGFUSE_PUBLIC_KEY` | Yes | cloud.langfuse.com |
| `LANGFUSE_SECRET_KEY` | Yes | cloud.langfuse.com |
| `LANGFUSE_BASE_URL` | Yes | `https://us.cloud.langfuse.com` |
| `LANGSMITH_API_KEY` | Yes | smith.langchain.com |
| `LANGSMITH_TRACING` | Yes | `true` |
| `LANGSMITH_PROJECT` | Yes | your project name |

---

## Makefile Targets

```bash
make run         # streamlit run app/streamlit_app.py
make eval        # python evaluation/run_eval.py
make promptfoo   # npx promptfoo eval
make deploy-hf   # push to HuggingFace Spaces
make install     # pip install -r requirements.txt
make lint        # ruff check .
make test        # pytest tests/ -v
```
