"""Modal deployment — Qwen2.5-7B-Instruct served via vLLM.

Exposes an OpenAI-compatible /v1/chat/completions endpoint so the Streamlit
app can call it via ChatOpenAI(base_url=OSS_SERVE_URL) with zero code changes.

Deploy:
    modal deploy serve/modal_server.py

After deploying, copy the printed URL into .env:
    OSS_SERVE_URL=https://<your-workspace>--qwen-serve.modal.run/v1

The endpoint scales to 0 when idle and cold-starts in ~60–90s.
Set scaledown_window higher if you want it to stay warm longer.
"""

from __future__ import annotations

import subprocess

import modal

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
GPU = "A10G"          # 24 GB VRAM — fits 7B in fp16 comfortably
N_GPU = 1
VLLM_PORT = 8000
MINUTES = 60

# ── Container image ───────────────────────────────────────────────────────────
# Modal provides CUDA drivers; we only need vLLM installed.
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04", add_python="3.11"
    )
    .entrypoint([])
    .uv_pip_install("vllm>=0.8.0", "huggingface_hub[hf_xet]>=0.27")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

# ── Persistent volume for model weights (survives redeployments) ──────────────
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)

# ── Modal app ─────────────────────────────────────────────────────────────────
app = modal.App("qwen-serve")


@app.function(
    image=image,
    gpu=f"{GPU}:{N_GPU}",
    scaledown_window=15 * MINUTES,
    timeout=10 * MINUTES,
    volumes={"/root/.cache/huggingface": hf_cache_vol},
)
@modal.concurrent(max_inputs=50)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve():
    cmd = [
        "vllm", "serve", MODEL_NAME,
        "--served-model-name", MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--dtype", "auto",
        "--max-model-len", "8192",
        "--enforce-eager",          # faster cold-start; remove for max throughput
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",
    ]
    print("Starting vLLM:", " ".join(cmd))
    subprocess.Popen(cmd)
