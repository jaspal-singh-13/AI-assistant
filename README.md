# AI Assistant Comparison

Two AI assistants — one powered by **Claude Haiku** (frontier), one by **Qwen 2.5 7B** (open-source) — evaluated on hallucination, bias, and content safety.

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

## OSS Model Server (GPU inference)

Two options for fast Qwen inference. **Option A (Modal)** is recommended — no local GPU required.

---

### Option A — Modal (recommended)

[Modal](https://modal.com) runs the model on a cloud A10G GPU and gives you a public HTTPS endpoint.
Cold-start is ~60–90s; subsequent requests are fast (~30–50 tokens/s).

#### Prerequisites

- A Modal account at [modal.com](https://modal.com) (free tier works)
- Your Modal token ID and secret (found at [modal.com/settings/tokens](https://modal.com/settings/tokens))

#### Step 1 — Install Modal and authenticate

```bash
pip install "modal>=0.73"

modal token set \
  --token-id <your-token-id> \
  --token-secret <your-token-secret>
```

The token is saved to `~/.modal.toml`. You only need to do this once per machine.

Alternatively, add the credentials to `.env` and they will be picked up automatically:

```env
MODAL_TOKEN_ID=ak-xxxxx
MODAL_TOKEN_SECRET=as-xxxxx
```

#### Step 2 — Deploy the model server

```bash
# On Windows, set UTF-8 first to avoid encoding errors in Modal's CLI output
chcp 65001        # Windows only
set PYTHONUTF8=1  # Windows only

modal deploy serve/modal_server.py
```

Expected output:
```
✓ Created objects.
└── 🔨 Created web function serve =>
    https://<your-workspace>--qwen-serve-serve.modal.run
✓ App deployed in 6s! 🎉
```

The first deploy builds the container image (installs vLLM + CUDA deps) — this takes **3–5 minutes** once.
Subsequent deploys reuse the cached image and finish in ~10s.

#### Step 3 — Set `OSS_SERVE_URL` in `.env`

Copy the URL printed above and add `/v1` to the end:

```env
OSS_SERVE_URL=https://<your-workspace>--qwen-serve-serve.modal.run/v1
```

#### Step 4 — Start Streamlit

```bash
python -m streamlit run app/streamlit_app.py
```

Streamlit routes all Qwen calls to Modal automatically. No second terminal needed.

#### Verify the endpoint is alive

```bash
curl https://<your-workspace>--qwen-serve-serve.modal.run/health
# → {"status":"ok","model":"Qwen/Qwen2.5-7B-Instruct","quant":"..."}
# (first request triggers a cold-start — wait ~90s)
```

#### Re-deploy after code changes

```bash
modal deploy serve/modal_server.py
```

#### Stop / tear down

```bash
modal app stop qwen-serve      # stops running containers (billing stops)
modal app delete qwen-serve    # deletes the app entirely
```

The `hf-cache` Modal Volume persists model weights so re-deploys don't re-download the 15 GB model.

---

### Option B — Local GPU

By default, Qwen runs locally on CPU — slow (~2–5 tokens/s for the 7B model).
To use your GPU, start the FastAPI model server in a separate terminal **before** launching Streamlit.

#### Step 1 — Configure `.env`

```env
# URL the Streamlit app will call for OSS inference
OSS_SERVE_URL=http://localhost:8000/v1

# Quantization mode — pick based on your VRAM
OSS_QUANT=4bit    # ~4 GB VRAM  (recommended for most consumer GPUs)
# OSS_QUANT=8bit  # ~8 GB VRAM  (better quality, more memory)
# OSS_QUANT=16bit # ~14 GB VRAM (full float16, best quality)
```

| `OSS_QUANT` | VRAM needed (7B model) | Notes |
|---|---|---|
| `4bit` | ~4 GB | Double-quant BnB; barely noticeable quality drop for chat |
| `8bit` | ~8 GB | Good balance of quality and memory |
| `16bit` | ~14 GB | Full `float16`, best quality |

#### Step 2 — Start the model server

```bash
# Terminal 1 — loads model once, stays running
python serve/model_server.py
```

You'll see:
```
[model_server] Loading Qwen/Qwen2.5-7B-Instruct in 4bit mode …
[model_server] Model ready in 42.3s  (quant=4bit)
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Check the server is alive:
```bash
curl http://localhost:8000/health
# → {"status":"ok","model":"Qwen/Qwen2.5-7B-Instruct","quant":"4bit","device":"cuda:0"}
```

#### Step 3 — Start Streamlit as normal

```bash
# Terminal 2
python -m streamlit run app/streamlit_app.py
```

Streamlit will now route all Qwen calls to `http://localhost:8000/v1/chat/completions` instead of running inference in-process.

#### Fallback behaviour

If `OSS_SERVE_URL` is **not set** (or left blank) in `.env`, the app falls back to the original local CPU inference automatically — no code change needed.

#### Custom model or port

```env
OSS_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct   # swap to a smaller model
OSS_HOST=0.0.0.0                           # bind host (default 0.0.0.0)
OSS_PORT=9000                              # bind port (default 8000)
OSS_SERVE_URL=http://localhost:9000/v1     # must match port above
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
| OSS tool calling | HF Router via ChatOpenAI client (router.huggingface.co/v1) | ChatHuggingFace + HuggingFaceEndpoint does not propagate tool schemas correctly so the model outputs raw JSON text instead of structured tool_calls. The HF Router exposes an OpenAI-compatible API that fixes this while still running Llama on HF infrastructure with the same HF_TOKEN. No OpenAI account needed. |
| Local GPU inference | FastAPI server (`serve/model_server.py`) with OpenAI-compatible API | Decouples model loading from the Streamlit process; `ChatOpenAI(base_url=...)` gives native LangChain streaming with no custom wrapper; `bitsandbytes` quantization keeps VRAM usage configurable (4 / 8 / 16-bit) |

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
- **Qwen on CPU (default):** ~2–5 tokens/s for the 7B model without the GPU server. Use `serve/model_server.py` with `OSS_QUANT=4bit` to get ~20–50 tokens/s on a consumer GPU.
- **Two-process setup for GPU inference:** The FastAPI server is a separate process from Streamlit. This adds operational complexity (two terminals to start) but keeps the Streamlit process free of GPU memory and avoids model reloads on Streamlit hot-reloads.
- **LlamaGuard 3 via HF Inference API:** ~300ms latency. Toggle "Safety guardrails" off in the sidebar to skip it for faster responses.
- **Incremental summarisation:** Slightly stale summaries possible (only updates when a full window of messages goes uncovered). Acceptable tradeoff for cost savings.

---

## What I Would Improve With More Time

1. **Async streaming** — the GPU server already emits SSE; wiring async consumption into Streamlit would remove the sync-blocking tradeoff.
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

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | console.anthropic.com |
| `HF_TOKEN` | Yes | — | huggingface.co/settings/tokens |
| `LANGFUSE_PUBLIC_KEY` | Yes | — | cloud.langfuse.com |
| `LANGFUSE_SECRET_KEY` | Yes | — | cloud.langfuse.com |
| `LANGFUSE_BASE_URL` | Yes | — | `https://us.cloud.langfuse.com` |
| `LANGSMITH_API_KEY` | Yes | — | smith.langchain.com |
| `LANGSMITH_TRACING` | Yes | — | `true` |
| `LANGSMITH_PROJECT` | Yes | — | your project name |
| `OSS_SERVE_URL` | No | _(CPU fallback)_ | URL of the FastAPI GPU server, e.g. `http://localhost:8000/v1` |
| `OSS_QUANT` | No | `16bit` | Quantization mode for the GPU server: `4bit` / `8bit` / `16bit` |
| `OSS_MODEL_NAME` | No | `Qwen/Qwen2.5-7B-Instruct` | HuggingFace repo to load in the GPU server |
| `OSS_HOST` | No | `0.0.0.0` | Bind host for the GPU server |
| `OSS_PORT` | No | `8000` | Bind port for the GPU server |

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
