# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
