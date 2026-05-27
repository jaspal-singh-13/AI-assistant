# Model Evaluation Report

**Claude Haiku-4-5 vs Qwen 2.5-7B-Instruct** · 45 prompts · 3 dimensions · Generated 2026-05-25

---

## Summary

| | Claude Haiku-4-5 | Qwen 2.5-7B-Instruct |
|---|:---:|:---:|
| Overall pass rate | **100%** | **67%** |
| Eval prompts | 45 | 45 |
| Dimensions passed | 3 / 3 | 2 / 3 |
| Verdict | Production ready | Requires guardrails |

---

## Performance by Metric

> Performance score — higher is better for all metrics.
> Lower-is-better raw scores (hallucination, bias, toxicity) are inverted: `perf = 1 − violation_rate`.

| Metric | Claude Haiku | Qwen 2.5-7B | Winner |
|---|:---:|:---:|:---:|
| Bias | 100% | 100% | Tie |
| Toxicity | 100% | 100% | Tie |
| Hallucination | 100% | 67% | Claude |
| Jailbreak Resistance | 100% | 33% | Claude |
| Refusal Quality | 93% | 30% | Claude |

---

## Dimension Pass Rates

### Hallucination · 15 factual prompts

| Model | Pass Rate | Raw Score |
|---|:---:|:---:|
| Claude Haiku | **100%** | 0.00 (no hallucinations) |
| Qwen 2.5-7B | **67%** | 0.33 violation rate |

### Bias & Harmful · 15 bias-sensitive prompts

| Model | Pass Rate | Bias Score | Toxicity Score |
|---|:---:|:---:|:---:|
| Claude Haiku | **100%** | 0.00 | 0.00 |
| Qwen 2.5-7B | **100%** | 0.00 | 0.00 |

Both models perform equally well — no bias or toxic outputs detected.

### Content Safety · 15 adversarial prompts

| Model | Pass Rate | Jailbreak Resistance | Refusal Quality |
|---|:---:|:---:|:---:|
| Claude Haiku | **100%** | 1.00 | 0.93 |
| Qwen 2.5-7B | **33%** | 0.33 | 0.30 |

Largest gap between the two models. Qwen fails 2-in-3 adversarial prompts.

---

## Infographic Summary

```
Performance Score (higher = better, 0 – 1.0)

Bias               Claude ████████████████████ 1.00
                   Qwen   ████████████████████ 1.00

Toxicity           Claude ████████████████████ 1.00
                   Qwen   ████████████████████ 1.00

Hallucination      Claude ████████████████████ 1.00
                   Qwen   █████████████░░░░░░░ 0.67

Jailbreak Resist.  Claude ████████████████████ 1.00
                   Qwen   ██████░░░░░░░░░░░░░░ 0.33

Refusal Quality    Claude ██████████████████░░ 0.93
                   Qwen   ██████░░░░░░░░░░░░░░ 0.30
```

---

## Recommendations

### Claude Haiku — Production ready

100% pass rate across all three evaluation dimensions. Recommended for any deployment where factual accuracy and content safety are required. No additional safety layers needed beyond the existing guardrail pipeline.

### Qwen 2.5-7B — Use with active guardrails

Matches Claude on bias and toxicity, but a 33% hallucination rate and weak jailbreak/refusal scores (0.33 / 0.30) require the full 4-stage input + 3-stage output guardrail pipeline before production use. Do not disable guardrails for this model.

### Priority 1: Fix Content Safety (highest impact)

Qwen's jailbreak resistance (0.33) and refusal quality (0.30) are the largest gaps. Three options, in order of effort:

1. **Enable NeMo/LlamaGuard layer** — already implemented in `guardrails/`; ensure `NEMO_SERVE_URL` is set in production. Zero code changes.
2. **Safety fine-tuning** — fine-tune Qwen on a safety-alignment dataset (e.g. Anthropic HH-RLHF, BeaverTails). Estimated: 1–2 days on an A10G.
3. **Prompt hardening** — strengthen `agent/system_prompt.py` with explicit refusal instructions and jailbreak-resistance guidance.

### Priority 2: Reduce Hallucination (second highest impact)

Qwen's 33% hallucination rate on factual prompts is the second gap. Two options:

1. **Retrieval-Augmented Generation (RAG)** — attach a knowledge base for factual queries so the model cites sources rather than generating from parametric memory.
2. **Domain fine-tuning** — fine-tune on a curated factual QA dataset relevant to the target domain.

### What to keep

- The **bias and toxicity scores are identical** (both 0.00). The existing heuristic validators in `guardrails/validators.py` are working. No changes needed here.
- The **evaluation infrastructure** (DeepEval + LLM judge + position-swap debiasing) is sound. Adding a third model requires only one new entry in `agent/models.py`.

---

## Methodology

| Component | Detail |
|---|---|
| Custom prompts | 45 prompts across factual (15), adversarial (15), bias_sensitive (15) categories |
| DeepEval metrics | HallucinationMetric, BiasMetric, ToxicityMetric, GEval (jailbreak, refusal) |
| LLM judge | Claude Haiku as judge; position-swap debiasing (each comparison run twice, positions flipped) |
| HF benchmarks | TruthfulQA, BBQ, AdvGLUE (downloaded and cached via `evaluation/benchmarks/loader.py`) |
| Red-team | Promptfoo red-team suite (`evaluation/promptfoo.yaml`) |
| Score storage | `evaluation/results/model_scores.json` |

---

*Source: `evaluation/results/model_scores.json` · Eval suite: `make eval` · Full metric definitions: see [EVALUATION.md](EVALUATION.md)*
