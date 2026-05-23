# Project TODO

> **`[x]`** = code implemented + `pytest` shows `PASSED` for its tests.
> **`[ ]`** = not done yet.
> Never mark `[x]` if the test is skipped, missing, or failing.

---

## Phase 1 — Model Handlers & Agent Creation

**Gate:** Both models respond, tool calls in `state_snapshot`, model switch preserves thread.
**Test gate:** No `FAILED`/`ERROR` in `tests/test_memory.py`, `test_tools.py`, `test_agent.py`.

### Scaffold (config / data files — no tests needed)
- [x] Project directories, `__init__.py` files, `requirements.txt`, `.env.example`
- [x] `config/pricing_fallback.json` — static pricing for Claude Sonnet + Qwen

### agent/models.py
- [x] `ModelConfig`, `MODELS` dict, `get_model()`, `list_models()` — 6 tests passing
- [x] `build_llm()` — ChatAnthropic for frontier, ChatHuggingFace for OSS

### agent/factory.py
- [x] `create_agent(llm, tools)` → CompiledGraph via `create_react_agent`
- [x] `run_agent()` — `graph.stream()` loop, returns `(response_str, state_snapshot)`
- [x] `_parse_message_to_step()` — AIMessage / ToolMessage → step dict with `call_id`

### memory/manager.py
- [x] `get_context_label()` — dynamic slider label — 2 tests passing
- [x] `create_thread()` — UUID, auto-title from first 6 words, write JSON + index
- [x] `save_thread()` — persist to disk, sync `message_count` in index.json
- [x] `get_llm_context()` — sliding window + merged summary SystemMessage
- [x] `update_summaries()` — incremental cursor advance, summary-of-summary

### memory/summariser.py
- [x] `summarise(prev_text, messages)` — LLM call, returns updated summary string
- [x] `merge(summaries[])` — formats summaries into single SystemMessage content

### memory/converters.py
- [x] `dicts_to_messages()` — thread dicts → HumanMessage / AIMessage / ToolMessage
- [x] `message_to_dict()` — BaseMessage → thread JSON dict with timestamp

### tools/
- [x] `tools/time_tool.py` — `get_current_time()` implemented with `@tool` decorator — 2 tests passing
- [x] `tools/weather_tool.py` — wttr.in call, temp + condition, city-not-found fallback
- [x] `tools/search_tool.py` — DuckDuckGo top-5 results (title + snippet + URL)
- [x] `tools/metrics_tool.py` — parse calls.jsonl, return per-model avg latency / cost / block rate
- [x] `tools/registry.py` — `get_tools()` returns `[time, weather, search, metrics]`

### tests/
- [x] `tests/test_agent.py` — unskip and implement `build_llm`, `create_agent`, `run_agent` tests
- [x] `tests/test_memory.py` — unskip and implement summarisation trigger + thread CRUD tests
- [x] `tests/test_tools.py` — unskip and implement weather (mocked), search (mocked), metrics tests

> Gate met — 2026-05-23

---

## Phase 2 — Streamlit UI

**Gate:** Full chat renders, badges correct, state panel shows tool args, context slider label accurate.
**Test gate:** No `FAILED`/`ERROR` in `tests/test_agent.py` integration tests.

### app/streamlit_app.py
- [x] Session state init, model dropdown, routing wired to sidebar + chat

### app/components/thread_sidebar.py
- [x] Thread list with active highlight, new thread button, auto-title from first 6 words
- [x] Context window slider (5–50, default 10) + dynamic label from `get_context_label()`

### app/components/chat_window.py
- [x] Render all messages; blue badge = frontier, coral badge = OSS; hover shows tokens + cost
- [x] Mid-thread switch divider: `── switched to {model_label} ──`

### app/components/state_panel.py
- [x] Collapsible THINKING → TOOL CALL (args table, 80-char truncate) → RESPONDING panel

### app/components/stream_handler.py
- [x] `handle_send()` — full pipeline: agent → log → save thread (guardrails wired in Phase 3)
- [x] `stream_tokens()` — `stream_and_collect()` in factory.py yields tokens via `st.write_stream()`
- [x] Chat auto-renaming — title updated from first 6 words of first user message

### app/components/thread_sidebar.py (additions)
- [x] Chat thread delete and edit name functionality
- [x] Separate 'New Chat' button which creates new chat

### agent/factory.py (fix)
- [x] Response should stream token by token (content block extraction fix)

- [x] Show typing till the assistant is generating token
- [x] Each tool call should be shown, instead of typing when tool being called. Like how chatgpt implemented thinking. similarly should be shown on UI


> Gate met — 2026-05-23
---

## Phase 3 — Monitoring & Guardrails

**Gate:** DAN blocked at Rebuff, hate blocked with category label, PII redacted, cost charts live.
**Test gate:** All of `tests/test_guardrails.py` and `tests/test_observability.py` unskipped and green.

### observability/logger.py
- [x] `log_call()`, `read_calls()` — full JSONL schema, file write — 6 tests passing
- [x] File lock for concurrent writes — filelock used, test passing

### observability/pricing.py
- [x] `hours_since_fetch()` — 1 test passing
- [x] `fetch_pricing()` — GET LiteLLM JSON, 24hr cache in session state, fallback on error — 1 test passing
- [x] `compute_cost()` — frontier: LiteLLM per-token prices; OSS: `(latency_ms/3_600_000) × $0.03` — 2 tests passing

### observability/langfuse_query.py
- [x] `get_langfuse_handler()` — return CallbackHandler or None if keys missing
- [x] `build_run_config()` — inject handler into LangGraph run config

### guardrails/llamaguard.py
- [x] `CATEGORY_MAP` (S1–S13) — 1 test passing
- [x] `classify(text, role)` — HF Inference API call, parse "safe"/"unsafe\nS{N}" response — 2 tests passing

### guardrails/input_guard.py
- [x] `message_hash()` — SHA-256 helper — 1 test passing
- [x] `_check_injection()` — heuristic regex injection detection (~1ms); rebuff==0.1.1 requires langchain<0.2 (incompatible)
- [x] `_detect_pii()` — Presidio entity detection (local, never blocks) — 1 test passing
- [x] `run_input_pipeline()` — injection check → LlamaGuard 3 → Presidio, first block wins — 2 tests passing

### guardrails/output_guard.py
- [x] `_check_validators()` — ToxicLanguage + RestrictToTopic heuristic validators
- [x] `run_output_pipeline()` — heuristic validators → LlamaGuard 3 re-check — 2 tests passing

### guardrails/validators.py
- [x] Implement `ToxicLanguage`, `DetectPII`, `RestrictToTopic` validator classes (heuristic, no broken dep)

### guardrails/nemo/
- [x] `config.yml` and `rails.co` — 4 declarative rails written
- [ ] End-to-end test that NeMo rails load and trigger correctly

### app/pages/02_observability.py
- [x] Row 1: metric cards — calls, avg latency, total cost, cost/1k per model
- [x] Row 2+3: cost per call line chart + cumulative cost area chart
- [x] Row 4: stacked bar — input vs output tokens per call
- [x] Row 5: safety log table — blocked calls, timestamp, category

### tests/
- [x] `tests/test_guardrails.py` — 10 tests passing
- [x] `tests/test_observability.py` — 10 tests passing (all pricing and cost tests green)

> Gate met — 2026-05-23

---

## Phase 4 — Evaluation, Deployment & Docs

**Gate:** `run_eval.py` completes, 3 CSVs written, Promptfoo `report.html`, two public URLs live.
**Test gate:** All of `tests/test_judge.py` and `tests/test_evaluation.py` unskipped and green.

### evaluation/prompts/
- [x] 3 sample prompts in each of `factual.json`, `adversarial.json`, `bias_sensitive.json`
- [ ] Expand each to 15 prompts (factual with context + expected_output)
- [ ] Run `npx promptfoo redteam generate` to add 5 adversarial prompts

### evaluation/benchmarks/loader.py
- [x] `load_benchmark()` from cache, `unknown` raises — 2 tests passing
- [ ] Implement HF datasets download + normalise + write cache

### evaluation/llm_judge.py
- [x] `get_rubric()`, `_RUBRICS` dict, `ComparativeResult.winner` — 6 tests passing
- [ ] `judge_absolute()` — LLM call with CoT rubric, returns `AbsoluteResult`
- [ ] `judge_comparative()` — position swap (run twice), consistency check, `low_confidence`

### evaluation/deepeval_metrics.py
- [x] Threshold constants (HALLUCINATION=0.5, BIAS=0.5, TOXICITY=0.5, JAILBREAK=0.7, REFUSAL=0.6) — 1 test passing
- [ ] Implement all 5 metric getters and `score_response()`

### evaluation/framework.py
- [ ] `load_prompts()` — loads 45 custom + benchmark samples
- [ ] `run_both_models()` — calls each agent, records response + metadata
- [ ] `score_with_deepeval()`, `score_with_judge()`, `score_against_benchmark()`
- [ ] `aggregate()` — writes `summary.csv` + `comparative.csv`, flags `low_confidence`
- [ ] `report()` — calls `charts.py` to generate PNG files

### evaluation/charts.py
- [ ] `generate_bar_chart()` — 3 metrics × 2 models, excludes `low_confidence` rows
- [ ] `generate_radar_chart()` — overall capability spider chart

### evaluation/langsmith_sync.py
- [ ] `sync_scores_to_langsmith()` — `client.create_feedback()` for each DeepEval score

### evaluation/run_eval.py
- [ ] Full pipeline: load → run both models → score all methods → aggregate → report
- [ ] `--seed` arg for reproducibility, partial result caching for judge outages

### evaluation/results/
- [x] `model_scores.schema.json` — JSON schema for per-model per-dimension scorecard (see EVALUATION.md)
- [ ] `model_scores.json` — written by `EvalFramework.aggregate()` after `run_eval.py` completes

### evaluation/promptfoo.yaml
- [x] Base config with 3 prompt files, `not-toxic` + `llm-rubric` asserts, redteam section
- [ ] Add HuggingFace provider for Qwen
- [ ] Add per-prompt asserts for factual prompts

### deployment/hf_spaces/app.py
- [ ] `chat()` — transformers pipeline inference for Qwen2.5-0.5B
- [ ] Gradio `ChatInterface`, `launch()`, HF Space secrets for tokens

### docs/
- [x] `README.md` skeleton — all required sections present
- [x] `EVALUATION.md` — full reference for all 3 dimensions, metric mapping, storage schema
- [ ] Fill in public URLs after deployment
- [ ] Fill in cost + latency table after Phase 3 is live
- [ ] Generate 1-page evaluation report PDF with bar chart + radar chart

### tests/
- [ ] `tests/test_judge.py` — unskip position swap tests as judge is implemented
- [ ] `tests/test_evaluation.py` — unskip framework + charts tests as Phase 4 lands

### deploy
- [ ] Push to Streamlit Community Cloud — verify `*.streamlit.app` URL
- [ ] Push to HuggingFace Spaces — verify public Gradio URL
- [ ] Run `make eval` locally before deploying — commit `evaluation/results/model_scores.json` so scores are visible on Streamlit without re-running evals (Streamlit filesystem is ephemeral)
- [ ] Verify `logs/calls.jsonl` is not expected on Streamlit Cloud — guardrail block rate in scorecard must come from a pre-run eval, not from live runtime logs

---

## Ongoing
- [ ] `make lint` and `make test` pass before every commit
- [ ] Update `CHANGELOG.md` with every meaningful change
- [ ] Keep this file updated — `[x]` only after tests pass
