# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.11.3] — 2026-05-25

### Fixed
- `evaluation/framework.py` `_run_one()` — renamed shadowing `config` local to `model_config`, added `run_config` dict carrying `model_id` (real API model name) and `configurable.thread_id` (prompt id), and passed it to both `run_agent()` call sites — fixes `model=unknown thread=?` in evaluation logs and ensures the real model name is consistent across all log lines and the returned result dict

## [0.11.2] — 2026-05-25

### Fixed
- Added `REQUIRED_CALL_FIELDS` schema constant to `observability/logger.py` and enforced it in `read_calls()`, which now silently drops legacy JSONL records missing any required field — fixes `KeyError: 'model_id'` crash on the Streamlit Cloud observability page caused by old-schema records in `calls.jsonl`

## [0.11.1] — 2026-05-25

### Changed
- `_fmt_cost()` in `app/components/guardrail_panel.py`, `app/pages/02_observability.py`, and `app/streamlit_app.py` — all cost values now display in plain USD (e.g. `$0.00000266`) instead of the previous micro/milli-dollar notation (`μ$`, `m$`)

## [0.11.0] — 2026-05-25

### Added
- `observability/pricing.py` — `MODAL_A10G_PER_SECOND_USD = 0.000306` and `MODAL_CPU_PER_SECOND_USD = 0.0000131 × 0.125` constants for the three Modal services (Qwen GPU, NeMo CPU, Presidio CPU)
- `observability/pricing.py` — `compute_guardrail_cost(input_guard, output_guard, pricing)` helper that sums Claude Haiku token cost (LlamaGuard) plus Modal CPU wall-clock cost (NeMo, Presidio) for both guardrail pipelines in a single call
- `guardrails/llamaguard.py` `GuardResult` — `input_tokens` and `output_tokens` fields; populated from `msg.usage` on every `classify()` call
- `observability/logger.py` `log_call()` — `guardrail_cost_usd` field; `llm_cost_usd` field; `total_cost_usd` now equals `llm_cost + guardrail_cost`
- `config/pricing_fallback.json` — `Qwen/Qwen2.5-7B-Instruct` entry with derived per-token rates (`$0.00000153` input, `$0.00000765` output) based on Modal A10G rate and measured throughput
- `app/components/guardrail_panel.py` — `💰 Guardrail cost` line at the bottom of each message's guardrail expander
- `app/pages/02_observability.py` — `LLM cost` and `Guardrail cost` split metrics in summary row and per-model cards; Cost tab replaced with stacked area chart showing LLM vs guardrail cost split

### Changed
- `observability/pricing.py` `compute_cost` OSS branch — now uses `(latency_ms / 1000) × MODAL_A10G_PER_SECOND_USD` instead of the (wrong) HF CPU hourly rate
- Removed `HF_SPACES_CPU_HOURLY_USD` and old `MODAL_GPU_PER_SECOND_USD` (was A100-40GB rate, incorrect for A10G)
- `app/components/stream_handler.py` — computes and passes `guardrail_cost_usd` on both the blocked and normal response paths
- `tests/test_guardrails.py` — all `classify()` tests updated to mock `anthropic.Anthropic` (was `requests.post` against a stale HF API design)

## [0.10.0] — 2026-05-25

### Added
- `serve/presidio_modal.py` — Modal CPU service with spaCy `en_core_web_lg` baked into the container image; exposes `POST /detect` for full NER-based PII detection (PERSON, LOCATION, ORGANIZATION, etc.)
- `serve/nemo_modal.py` — Modal service wrapping NeMo Guardrails; exposes `POST /check_input` and `POST /check_output` using the existing `guardrails/nemo/` Colang config
- `guardrails/nemo_client.py` — lightweight HTTP client for `NEMO_SERVE_URL`; gracefully returns `(False, None)` when env var is absent or service unreachable
- NeMo Guardrails wired as Stage 4 of `input_guard.py` and Stage 3 of `output_guard.py` — fully optional, shown as "skipped" in the guardrail panel when `NEMO_SERVE_URL` is not set
- `deepeval>=1.4` and `datasets>=2.0` restored to `[project.dependencies]` and `requirements.txt` so the evaluation page works on Streamlit Cloud without `ModuleNotFoundError`
- Modal Microservices table added to `README.md` with deploy commands for all three services

### Changed
- `guardrails/nemo/config.yml` — switched LLM engine from `openai/gpt-3.5-turbo` to `anthropic/claude-haiku-4-5-20251001` (project uses Anthropic, not OpenAI)
- `guardrails/input_guard.py` `_detect_pii()` — tries `PRESIDIO_SERVE_URL/detect` first for full NER; falls back to local regex patterns if unset or unreachable
- `deepeval` and `datasets` removed from `[project.optional-dependencies] dev` (now in main deps)
- `.env.example` updated with `PRESIDIO_SERVE_URL` and `NEMO_SERVE_URL` placeholders

## [0.9.0] — 2026-05-25

### Added
- Dashboard home page (`app/streamlit_app.py`) with KPI cards (threads, calls, total cost, avg latency, block rate), per-model mini-cards, condensed cumulative-cost chart snapshot, and evaluation scorecard table
- `app/pages/01_chat.py` — chat UI promoted to its own named page so the sidebar reads "Chat"
- `tools/observability_tool.py` — `get_observability_summary(model_id)` read-only tool that returns per-model call count, latency (avg/p50/p95), cost, block rate, and top tool invocations from `logs/calls.jsonl`
- `tools/evaluation_tool.py` — `get_evaluation_summary(model_id)` read-only tool that returns hallucination, bias & harmful, and content safety scores from `evaluation/results/model_scores.json`
- `agent/system_prompt.py` — app-level `SYSTEM_PROMPT` constant injected as the first `SystemMessage` on every LLM call; documents all four app pages and provides exact tool-use guidance including when to call each of the five tools

### Changed
- `memory/manager.py:get_llm_context()` now prepends the app `SYSTEM_PROMPT` SystemMessage before the optional summary SystemMessage and the sliding window messages
- `tools/registry.py` updated to export `get_observability_summary` and `get_evaluation_summary` instead of `get_metrics`
- `tests/test_tools.py` — replaced `TestMetricsTool` with `TestObservabilityTool` (4 tests) and `TestEvaluationTool` (3 tests); updated memory context window bound to 12 (adds 1 for app SystemMessage)

### Removed
- `tools/metrics_tool.py` and `get_metrics` tool — superseded by `get_observability_summary`

## [0.8.1] — 2026-05-25

### Changed
- Replaced Presidio + spaCy PII detection with zero-dependency regex patterns (EMAIL, PHONE, SSN, CREDIT_CARD, IP_ADDRESS, PASSPORT) — eliminates 400MB model download, works on Streamlit Cloud with no permissions issues
- Added `sys.path` repo-root insertion in `streamlit_app.py` and page files so local modules resolve correctly on Streamlit Cloud
- Removed `presidio-analyzer`/`presidio-anonymizer` from `requirements.txt` and `pyproject.toml` slim deps; moved to `[dev]` optional group
- Removed `uv.lock` from version control; added to `.gitignore`
- Added `[build-system]` and `[tool.setuptools.packages.find]` to `pyproject.toml` so local packages install correctly via `pip install .`

## [0.8.0] — 2026-05-25

### Added
- `requirements-local.txt` — full local-dev requirements (GPU inference, evals, Modal, NeMo guardrails, dev tools)

### Changed
- `requirements.txt` slimmed to Streamlit Cloud-compatible subset: removed `nemoguardrails`, `torch`, `transformers`, `accelerate`, `bitsandbytes`, `fastapi`, `uvicorn`, `modal`, `gradio`, `deepeval`, `datasets`, `pytest`, `ruff`; added `python-dotenv`
- `make install` now installs from `requirements-local.txt` to keep the full local-dev experience
- `README.md` Quick Start section updated to document both requirements files with a comparison table

## [0.7.9] — 2026-05-24

### Changed
- Updated Makefile with new targets: `serve` (local FastAPI model server), `modal-deploy` (Modal vLLM deployment), `eval-light` (quick 9-prompt smoke-test)
- Updated `deploy-hf` target from TODO stub to working `huggingface-cli upload` command accepting `$(HF_SPACE)`
- Updated `install` target to also download `en_core_web_lg` spaCy model required by Presidio
- Updated `run` target to use `python -m streamlit run` for cross-platform compatibility

## [0.7.8] — 2026-05-24

### Fixed
- Wired Langfuse tracing into the agent stream: `stream_handler.py` now imports `build_run_config` and passes the resulting config (with `LangfuseCallbackHandler`) to `stream_events()`, so all LLM calls, tool steps, and token counts appear in the Langfuse dashboard

## [0.7.7] — 2026-05-24

### Fixed
- Fixed regression in `evaluation/langsmith_sync.py` where `with Client(...) as client:` caused `AttributeError` because `langsmith.Client` does not implement the context manager protocol; replaced with explicit `try/finally` + `client.close()` guard

## [0.7.6] — 2026-05-24

### Fixed
- Progress bar in `app/pages/03_evaluation.py` now shows the correct prompt count when `--prompt-ids` or `--light` filters are active; previously showed the unfiltered total (e.g. 45) instead of the actual count being run (e.g. 3)

## [0.7.5] — 2026-05-24

### Fixed
- Replaced all 6 deprecated `use_container_width=True` usages in `app/pages/03_evaluation.py` with `width='stretch'` (Streamlit deprecation, removal after 2025-12-31)

## [0.7.4] — 2026-05-24

### Fixed
- Migrated `tools/search_tool.py` from deprecated `duckduckgo_search` package to its renamed successor `ddgs`; updated import from `duckduckgo_search` → `ddgs`
- Updated `requirements.txt` and `pyproject.toml` dependency from `duckduckgo-search>=6.0` → `ddgs>=6.0`

## [0.7.3] — 2026-05-24

### Fixed
- Removed nested `ThreadPoolExecutor` in `evaluation/deepeval_metrics.py`; metrics now run sequentially to avoid orphaned asyncio event loops on Windows (`ProactorEventLoop`) that caused `RuntimeError: Event loop is closed` and `ResourceWarning: unclosed transport` spam
- Wrapped `langsmith.Client` in a `with` context manager in `evaluation/langsmith_sync.py` so its httpx connection pool is explicitly closed after sync, eliminating `ResourceWarning: unclosed socket` at script exit
- Fixed indentation bug in `_lookup_run_id()` (`langsmith_sync.py` line 55) that would have caused `IndentationError` at runtime
- Added `warnings.filterwarnings("ignore", category=ResourceWarning)` in `evaluation/run_eval.py` as a safety net for residual third-party async cleanup noise

## [0.7.2] — 2026-05-24

### Added
- Added `serve/modal_server.py` — Modal deployment of Qwen2.5-7B-Instruct via vLLM on an A10G GPU; exposes OpenAI-compatible `/v1/chat/completions` with no local GPU required
- Added `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` to `.env` and `.env.example`
- Updated `OSS_SERVE_URL` in `.env` to point to the live Modal endpoint
- Added `modal>=0.73` to `requirements.txt`

## [0.7.1] — 2026-05-24

### Added
- Added `Dockerfile` — single CUDA 12.1 image shared by both services
- Added `docker-compose.yml` — `model-server` (FastAPI GPU) + `streamlit` services; Streamlit waits for model-server health check; HuggingFace weights cached in a named volume
- Added `.dockerignore` to exclude venv, secrets, cache, and build artefacts from the image
- Added `make docker` and `make docker-down` targets to Makefile

## [0.7.0] — 2026-05-24

### Added
- Added `serve/model_server.py` — standalone FastAPI server that loads the OSS model on GPU and exposes an OpenAI-compatible `/v1/chat/completions` endpoint with streaming support
- Added `OSS_QUANT` env var (`4bit` | `8bit` | `16bit`) to control GPU VRAM usage via `bitsandbytes` quantization
- Added `OSS_SERVE_URL` env var; when set, `build_llm()` routes OSS model calls to the FastAPI server via `ChatOpenAI` instead of running local CPU inference
- Added `fastapi`, `uvicorn`, `bitsandbytes`, `langchain-openai` to `requirements.txt`

## [0.6.6] — 2026-05-24

### Changed
- Replaced static matplotlib charts with a single interactive Altair horizontal grouped bar chart in the Evaluation Dashboard; supports hover tooltips and pan/zoom

## [0.6.5] — 2026-05-24

### Changed
- Replaced static radar chart PNG on the Evaluation Dashboard with four inline matplotlib charts: all-metrics horizontal grouped bar, pass/fail stacked bar, per-metric score distribution box plot, and category × model heatmap
- Added `_load_summary_csv()` helper and chart functions `_fig_all_metrics_bar`, `_fig_score_distribution`, `_fig_category_heatmap`, `_fig_pass_fail` in `app/pages/03_evaluation.py`

## [0.6.4] — 2026-05-24

### Added
- New Streamlit page `app/pages/03_evaluation.py` with three tabs: Dashboard (scorecard metrics + charts from `model_scores.json`), Run Evaluation (config panel + prompt filter multiselect + live subprocess output), and Prompts & Results (prompt browser, add custom prompt form, summary.csv and comparative.csv tables)
- Added `--prompt-ids` argument to `run_eval.py` to run only specific prompt IDs, enabling targeted evaluation from the UI

## [0.6.3] — 2026-05-24

### Added
- Added "Safety guardrails" toggle to the sidebar; when off, both `run_input_pipeline` and `run_output_pipeline` are bypassed entirely, reducing per-message latency by ~300–400 ms

## [0.6.2] — 2026-05-24

### Added
- Added `--light` flag to `run_eval.py`: keeps 3 randomly-sampled prompts per category (9 total, seeded by `--seed`) for fast smoke-test runs

## [0.5.5] — 2026-05-24

### Fixed
- Fixed `langsmith_sync.py` reading wrong env var `LANGCHAIN_PROJECT` instead of `LANGSMITH_PROJECT`, causing all LangSmith score uploads to fail with "Project not found"

## [0.6.0] — 2026-05-24

### Added
- Implemented application logger in `observability/logger.py`: `configure_logging()` (rotating file + stderr handlers, idempotent), `get_logger()` (named logger factory), and `log_duration()` (context manager for elapsed-time tracing with automatic exception logging)
- Wired `get_logger(__name__)` into `agent/factory.py`, `guardrails/input_guard.py`, `guardrails/output_guard.py`, `guardrails/llamaguard.py`, `memory/manager.py`, and `app/components/stream_handler.py` — INFO/WARNING/ERROR/DEBUG calls cover all major code paths
- Wired `get_logger(__name__)` into all evaluation scripts: `evaluation/run_eval.py` (pipeline milestones, worker errors), `evaluation/framework.py` (prompt loading, model invocations, aggregation), `evaluation/llm_judge.py` (judge calls, JSON parse warnings), `evaluation/langsmith_sync.py` (sync start/done/skip), and `evaluation/benchmarks/loader.py` (cache hit/miss, download)
- `run_eval.py` now calls `configure_logging()` at startup so eval runs write to `logs/app.log`; replaced all bare `print()` + `traceback.print_exc()` error reporting with structured logger calls
- Added `configure_logging()` call at Streamlit startup in `app/streamlit_app.py` (respects `LOG_LEVEL` env var, defaults to `INFO`)
- Added `TestAppLogger` class (4 tests) to `tests/test_observability.py` covering handler installation, idempotency, elapsed-time logging, and exception tracing

## [0.5.4] — 2026-05-24

### Changed
- Parallelized evaluation pipeline for ~3–4x speedup: concurrent position-swap judge calls in `llm_judge.py` (ThreadPoolExecutor), concurrent Claude+Qwen model runs per prompt in `framework.py`, concurrent DeepEval metric calls in `deepeval_metrics.py`, and concurrent prompt processing in `run_eval.py` with a new `--workers N` flag (default 3)
- Moved Anthropic client construction to a module-level singleton in `llm_judge.py` to avoid per-call instantiation
- Added agent/LLM object cache in `framework.py` to avoid rebuilding graphs on every prompt
- Added `threading.Lock` guards in `run_eval.py` for shared `all_scores`/`comparatives` lists and cache writes; added `qwen_lock` to serialise local OSS model inference across workers

## [0.5.3] — 2026-05-24

### Fixed
- Fixed `ValidationError` crash in `agent/local_llm.py` `_stream()`: replaced `AIMessage` with `AIMessageChunk` when yielding `ChatGenerationChunk`, satisfying LangChain's `BaseMessageChunk` type constraint
- Replaced LlamaGuard (HF Inference API, decommissioned) with Claude Haiku (`claude-haiku-4-5-20251001`) as the content safety classifier in `guardrails/llamaguard.py`; uses Anthropic API with a structured S1–S13 system prompt, preserving the same `GuardResult` interface and response parsing

## [0.5.2] — 2026-05-24

### Fixed
- Updated `DEEPEVAL_JUDGE_MODEL` in `.env` and `.env.example` from deprecated `claude-3-haiku-20240307` to `claude-haiku-4-5-20251001`, resolving 404 errors from DeepEval's Anthropic judge during eval runs
- Fixed transformers `generation_config` deprecation warnings in `agent/local_llm.py` by passing a `GenerationConfig` object instead of individual generation kwargs to the pipeline

## [0.5.1] — 2026-05-24

### Added
- `app/components/guardrail_panel.py` — new collapsible panel that renders per-stage input and output guardrail results below each assistant message
- `guardrails/llamaguard.py` — added `stages` field to `GuardResult` dataclass to carry per-stage breakdown for UI display
- `guardrails/input_guard.py` — `run_input_pipeline()` now populates `stages` list with name, passed, latency_ms, and detail for each of the three stages; total latency accumulated across all stages
- `guardrails/output_guard.py` — `run_output_pipeline()` now populates `stages` list for heuristic validator and LlamaGuard 3 re-check stages
- `app/components/stream_handler.py` — saves `input_guard` and `output_guard` dicts (blocked, reason, pii_count, latency_ms, stages) into every assistant message's metadata; blocked-input path stores `output_guard: null`
- `app/components/chat_window.py` — calls `render_guardrail_panel(metadata)` for every assistant message

## [0.5.0] — 2026-05-24

### Added
- `evaluation/prompts/factual.json` — expanded from 3 to 15 factual prompts with context + expected_output
- `evaluation/prompts/adversarial.json` — expanded from 3 to 15 adversarial prompts covering DAN, encoding, social engineering, and persona-swap jailbreaks
- `evaluation/prompts/bias_sensitive.json` — expanded from 3 to 15 bias-sensitive prompts covering gender, race, religion, neurodiversity, and socioeconomic stereotypes
- `evaluation/benchmarks/loader.py` — implemented HF datasets download path with `_normalise_truthfulqa/bbq/advglue()` helpers and seeded sampling; writes JSON cache on first download
- `evaluation/llm_judge.py` — implemented `judge_absolute()` (single-response CoT scoring via Anthropic SDK) and `judge_comparative()` (position-swap debiasing with averaged scores and low-confidence detection per FR-EVL-05a–e)
- `evaluation/deepeval_metrics.py` — implemented all 5 metric getters (`get_hallucination_metric`, `get_bias_metric`, `get_toxicity_metric`, `get_jailbreak_metric`, `get_refusal_quality_metric`) and `score_response()` dispatcher using DeepEval + SingleTurnParams
- `evaluation/framework.py` — implemented all `EvalFramework` methods: `load_prompts()`, `run_both_models()`, `score_with_deepeval()`, `score_with_judge()`, `score_against_benchmark()`, `aggregate()` (writes summary.csv + model_scores.json), `report()` (calls charts.py)
- `evaluation/charts.py` — implemented `generate_bar_chart()` (3 dims × 2 models, excludes low_confidence rows) and `generate_radar_chart()` using matplotlib with Agg backend
- `evaluation/langsmith_sync.py` — implemented `sync_scores_to_langsmith()` and `_lookup_run_id()` via LangSmith Client; silently skips when `LANGSMITH_API_KEY` is absent
- `evaluation/run_eval.py` — implemented full pipeline: load → run both models → DeepEval scoring → LLM-as-judge → aggregate → chart → LangSmith sync; partial result caching via `_partial_cache.json` for judge outages
- `evaluation/promptfoo.yaml` — added HuggingFace provider for Qwen2.5-0.5B-Instruct; added per-prompt asserts for 10 key prompts (factual answers, adversarial refusals, bias equity)
- `deployment/hf_spaces/app.py` — implemented Gradio `ChatInterface` with Qwen2.5-0.5B-Instruct transformers pipeline; lazy model loading; `main()` launches demo

### Changed
- `tests/test_judge.py` — unskipped `TestPositionSwap` tests; implemented with mocked Anthropic client
- `tests/test_evaluation.py` — unskipped and implemented all framework, chart, and deepeval metric tests; added `fake_openai_key` fixture for metric instantiation tests

## [0.4.1] — 2026-05-23

### Changed
- `app/pages/02_observability.py` — full readability overhaul: sidebar with model filter, call-count slider and auto-refresh toggle; global summary banner (total calls, avg latency, total cost, block rate); per-model detail cards with frontier/OSS badge, full model names, and tool invocation count; charts reorganised into four tabs (Cost, Latency, Tokens, Tools); new latency-per-call line chart and latency distribution histogram; tool usage bar chart and per-model tool pivot table; safety log upgraded with warning banner, friendly column names, and datetime formatting; raw-log download button; micro-dollar cost formatter for sub-cent amounts

## [0.4.0] — 2026-05-23

### Added
- `guardrails/llamaguard.py` — `classify()`: LlamaGuard 3 via HF Inference API; gracefully skips if `HUGGINGFACE_TOKEN` is absent
- `guardrails/input_guard.py` — `run_input_pipeline()`: 3-stage pipeline — heuristic injection detection → LlamaGuard 3 → Presidio PII (never blocks); replaces rebuff (incompatible with langchain>=0.3)
- `guardrails/input_guard.py` — `_check_injection()`: regex-based prompt injection detection (~1ms, no model call)
- `guardrails/input_guard.py` — `_detect_pii()`: Presidio `AnalyzerEngine` for local PII entity detection
- `guardrails/output_guard.py` — `run_output_pipeline()`: heuristic validators → LlamaGuard 3 re-check on output
- `guardrails/validators.py` — `ToxicLanguage`, `DetectPII`, `RestrictToTopic` heuristic validator classes
- `observability/pricing.py` — `fetch_pricing()`: GET LiteLLM pricing JSON with fallback to `config/pricing_fallback.json`
- `observability/pricing.py` — `compute_cost()`: frontier per-token cost from LiteLLM; OSS equivalent compute cost (never NA)
- `observability/logger.py` — `FileLock` for concurrent-safe JSONL writes
- `observability/langfuse_query.py` — `get_langfuse_handler()` and `build_run_config()` fully implemented
- `app/pages/02_observability.py` — full 5-row dashboard: metric cards, cost charts, token bar, safety log
- `app/components/stream_handler.py` — input guardrail wired before agent call; output guardrail wired after response; pricing fetched and logged per call

### Changed
- `requirements.txt` — added `presidio-analyzer`, `presidio-anonymizer`, `filelock`; removed `rebuff` (incompatible) and `guardrails-ai` (broken PyPI dep chain)
- uv virtualenv created at `.venv` with Python 3.12; `en_core_web_lg` spacy model installed for Presidio

## [0.3.5] — 2026-05-23

### Changed
- `app/components/thread_sidebar.py` — "Summary trigger" slider `min_value` is now dynamically `context_window + 5`; moving the context window slider auto-clamps the trigger if it would violate the rule
- `memory/manager.py` — `get_llm_context()` enforces `trigger >= window + 5` as a hard floor, protecting threads saved before this rule existed

## [0.3.4] — 2026-05-23

### Added
- `memory/manager.py` — `DEFAULT_SUMMARY_TRIGGER = 10` constant; stored as `summary_trigger` per thread so each thread can have its own threshold
- `memory/manager.py` — `get_llm_context()` reads `thread["summary_trigger"]` instead of reusing the context window size
- `app/components/thread_sidebar.py` — "Summary trigger" slider (1–50, default 10) below the context window slider; updates persist to disk per thread

## [0.3.3] — 2026-05-23

### Added
- `agent/factory.py` — `stream_events()`: unified event generator yielding typed dicts (`token`, `tool_call`, `tool_result`, `response`) for live UI rendering; keeps factory UI-agnostic
- `app/components/stream_handler.py` — live typing indicator ("▪ Thinking…") shown from the moment the agent starts until the first token arrives
- `app/components/stream_handler.py` — live tool call status ("🔧 Calling `<tool>`…") replaces the typing indicator while a tool is executing; "▪ Thinking…" resumes while the LLM digests the tool result
- `app/components/stream_handler.py` — token streaming with blinking `▌` cursor via `st.empty()` placeholder; cursor removed on completion

## [0.3.2] — 2026-05-23

### Fixed
- `agent/factory.py` — `_extract_text()`: normalises `AIMessage.content` from list-of-content-blocks to plain string, fixing raw `[{'text': ..., 'type': 'text'}]` display in the chat window
- `agent/factory.py` — streaming path: `_extract_text()` also applied to `AIMessageChunk.content` so token-by-token streaming works with block-format responses

### Added
- `memory/manager.py` — `delete_thread()`: removes thread JSON file and index entry
- `memory/manager.py` — `rename_thread()`: updates thread title and persists
- `app/components/thread_sidebar.py` — inline rename form (text input + Save/Cancel) per thread row
- `app/components/thread_sidebar.py` — delete button (🗑️) per thread row with active-thread guard
- `app/components/thread_sidebar.py` — prominent primary "New Chat" button at top of sidebar, separate from thread list

## [0.3.1] — 2026-05-23

### Added
- `agent/factory.py` — `stream_and_collect()`: single-pass dual-mode stream (`updates` + `messages`) that yields token strings for `st.write_stream()` while accumulating the state snapshot in the same LLM call
- `app/components/stream_handler.py` — `run_pending_response()` now streams tokens live into the assistant bubble via `st.write_stream()`; fallback to snapshot content if no tokens streamed (tool-only responses)
- Chat auto-renaming: `handle_send()` updates thread title from first 6 words of first user message when title is still the default "New thread"

## [0.3.0] — 2026-05-23

### Added
- `app/streamlit_app.py` — session state init, model dropdown (selectbox), `_rebuild_graph()` on model switch, routing to sidebar + chat; uncommented all Phase 2 imports
- `app/components/thread_sidebar.py` — thread list with active highlight, new thread button, context slider (5–50, default 10) with dynamic label from `get_context_label()`; full thread load on click
- `app/components/chat_window.py` — renders all messages with frontier (blue) / OSS (coral) badges, hover tooltip showing tokens + cost, mid-thread model switch divider, `st.chat_input` wired to `handle_send()`; agent reasoning state panel toggled per message
- `app/components/state_panel.py` — TODO comments removed; THINKING → TOOL CALL (args table, 80-char truncate) → RESPONDING collapsible panel fully active
- `app/components/stream_handler.py` — `handle_send()` implemented: builds LLM context, calls `run_agent()`, logs via `log_call()`, appends user + assistant messages to thread; guardrails deferred to Phase 3

### Changed
- Phase 2 gate met — all UI components implemented and wired together

## [0.2.0] — 2026-05-23

### Added
- `memory/converters.py` — implemented `dicts_to_messages()` and `message_to_dict()` (HumanMessage / AIMessage / ToolMessage mapping)
- `memory/summariser.py` — implemented `summarise()` with LLM invoke and summary-of-summary prompt
- `memory/manager.py` — implemented `create_thread()`, `get_llm_context()`, `update_summaries()`; fixed `save_thread()` to sync `message_count` and `updated_at` in index.json
- `agent/models.py` — implemented `build_llm()` for ChatAnthropic (frontier) and ChatHuggingFace via HuggingFaceEndpoint (OSS)
- `agent/factory.py` — implemented `create_agent()`, `run_agent()` streaming loop, `_parse_message_to_step()` with AIMessage / ToolMessage dispatch; added `nest_asyncio.apply()`
- `tools/time_tool.py` — added `@tool` decorator; `get_current_time()` is now a LangChain tool
- `tools/weather_tool.py` — implemented `get_weather()` with wttr.in JSON API and 404-fallback
- `tools/search_tool.py` — implemented `web_search()` returning top-5 DuckDuckGo results
- `tools/metrics_tool.py` — implemented `get_metrics()` computing per-model avg latency, total cost, and safety block rate from calls.jsonl
- `tools/registry.py` — implemented `get_tools()` returning all four tools
- `tests/test_memory.py` — unskipped and implemented all 8 Phase 1 tests (summarisation trigger, thread CRUD, LLM context window)
- `tests/test_tools.py` — unskipped and implemented all 6 Phase 1 tests (weather mocked, search mocked, metrics)
- `tests/test_agent.py` — unskipped and implemented all 6 Phase 1 tests (build_llm, create_agent, run_agent, _parse_message_to_step)

### Changed
- All Phase 1 `raise NotImplementedError` stubs replaced with working implementations

## [0.1.3] — 2026-05-22

### Added
- `EVALUATION.md` — central reference document mapping all 3 assignment dimensions (Hallucination Rate, Bias & Harmful Outputs, Content Safety) to metrics, prompt sets, and storage locations for both models
- `evaluation/results/model_scores.schema.json` — JSON schema for the per-model per-dimension scorecard written by `EvalFramework.aggregate()`
- `METRIC_TO_DIMENSION` constant in `evaluation/deepeval_metrics.py` mapping each DeepEval metric to its top-level dimension
- `dimension` field added to `EvalResult` dataclass in `evaluation/framework.py`
- Evaluation section added to `README.md` with dimension summary table

### Changed
- `evaluation/framework.py` module docstring updated with 3-dimension overview and storage file list
- `evaluation/deepeval_metrics.py` module docstring updated with dimension-to-metric grouping
- `observability/logger.py` module docstring clarifies runtime log vs eval score separation
- `TODO.md` updated with `EVALUATION.md`, `model_scores.schema.json`, and `model_scores.json` tasks

## [0.1.2] — 2026-05-22

### Fixed
- `TODO.md` rewritten — removed all false `[x]` "stub created" markers; `[x]` now only appears on code that is implemented and has passing tests
- Only 29 genuinely passing items remain marked done across all phases

### Added
- `.cursor/rules/keep-it-simple.mdc` — rule preventing overengineering, unnecessary abstractions, speculative generality, and bloated dependencies

## [0.1.1] — 2026-05-22

### Added
- `.cursor/rules/test-driven-todo.mdc` — rule enforcing tests must pass before marking TODO tasks `[x]`
- `tests/test_agent.py` — model registry tests (6 passing), agent factory stubs
- `tests/test_observability.py` — logger tests (6 passing, all `TestCallLogger` green), pricing stubs
- `tests/test_evaluation.py` — benchmark loader, rubric coverage, metric threshold, framework stubs
- `TODO.md` updated with test gate requirement per phase and new test file task entries

---

## [0.1.0] — 2026-05-22

### Added
- Full project scaffold — all directories, `__init__.py` files, and boilerplate stubs
- `agent/models.py` — model registry with `ModelConfig`, `MODELS` dict, `build_llm()` stub
- `agent/factory.py` — `create_agent()`, `run_agent()`, `_parse_message_to_step()` stubs
- `memory/manager.py` — thread CRUD, `get_llm_context()`, `update_summaries()`, `get_context_label()` stubs
- `memory/summariser.py` — `summarise()` and `merge()` stubs
- `memory/converters.py` — `dicts_to_messages()` and `message_to_dict()` stubs
- `memory/index.json` — empty thread index
- `tools/registry.py` — `get_tools()` stub
- `tools/time_tool.py` — `get_current_time()` implemented (no external API)
- `tools/weather_tool.py` — `get_weather()` stub with wttr.in pattern
- `tools/search_tool.py` — `web_search()` stub with DuckDuckGo pattern
- `tools/metrics_tool.py` — `get_metrics()` stub reading calls.jsonl
- `guardrails/llamaguard.py` — `GuardResult` dataclass, `CATEGORY_MAP` (S1–S13), `classify()` stub
- `guardrails/input_guard.py` — 3-stage pipeline stubs, `message_hash()`, `CANNED_REFUSAL`
- `guardrails/output_guard.py` — 2-stage pipeline stubs, `CANNED_OUTPUT_REFUSAL`
- `guardrails/validators.py` — `ToxicLanguage`, `DetectPII`, `RestrictToTopic` stubs
- `guardrails/nemo/config.yml` — NeMo Guardrails YAML configuration
- `guardrails/nemo/rails.co` — 4 declarative rails (identity, illegal, medical, jailbreak)
- `observability/logger.py` — `log_call()` with full JSONL schema, `read_calls()` helper
- `observability/pricing.py` — `fetch_pricing()`, `compute_cost()`, `hours_since_fetch()` stubs
- `observability/langfuse_query.py` — `get_langfuse_handler()`, `build_run_config()` stubs
- `app/streamlit_app.py` — session state init and layout scaffold
- `app/components/thread_sidebar.py` — sidebar layout stubs
- `app/components/chat_window.py` — message render with badge HTML pattern
- `app/components/state_panel.py` — THINKING → TOOL CALL → RESPONDING render stubs
- `app/components/stream_handler.py` — `handle_send()` and `stream_tokens()` stubs
- `app/pages/02_observability.py` — 5-row observability page scaffold
- `evaluation/framework.py` — `EvalFramework` class with all method stubs
- `evaluation/llm_judge.py` — full rubric map, `JudgeConfig`, result dataclasses, judge stubs
- `evaluation/deepeval_metrics.py` — 5 metric stubs with defined thresholds
- `evaluation/run_eval.py` — entry point with argparse (`--seed`, `--models`, etc.)
- `evaluation/langsmith_sync.py` — `sync_scores_to_langsmith()` stub
- `evaluation/charts.py` — `generate_bar_chart()` and `generate_radar_chart()` stubs
- `evaluation/benchmarks/loader.py` — `load_benchmark()` and `load_all()` stubs
- `evaluation/promptfoo.yaml` — base Promptfoo config with redteam section
- `evaluation/prompts/factual.json` — 3 sample factual prompts (15 needed)
- `evaluation/prompts/adversarial.json` — 3 sample adversarial prompts (15 needed)
- `evaluation/prompts/bias_sensitive.json` — 3 sample bias prompts (15 needed)
- `config/pricing_fallback.json` — static pricing for Claude Sonnet and Qwen
- `deployment/hf_spaces/app.py` — Gradio app stub for HF Spaces
- `deployment/hf_spaces/requirements.txt` — HF Spaces Python deps
- `tests/test_memory.py` — test stubs for memory layer (some tests already passing)
- `tests/test_tools.py` — test stubs for all 4 tools
- `tests/test_guardrails.py` — test stubs with `message_hash` test passing
- `tests/test_judge.py` — rubric selection and `ComparativeResult` tests passing
- `Makefile` — 7 targets: `run`, `eval`, `promptfoo`, `deploy-hf`, `install`, `lint`, `test`
- `README.md` — full skeleton with architecture, decisions, tradeoffs, cost table placeholder
- `TODO.md` — full project task list organised by phase
- `CHANGELOG.md` — this file
- `.env.example` — all required environment variable templates
