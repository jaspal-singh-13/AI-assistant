# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
