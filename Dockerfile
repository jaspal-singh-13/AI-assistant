# Single image for both the FastAPI model server and the Streamlit app.
# The GPU-capable base image includes CUDA + cuDNN so bitsandbytes quantization works.
#
# Build:  docker compose build
# Run:    docker compose up
#
# The image is tagged as ai-assistant. Both services share it; the entrypoint
# differs via the `command:` override in docker-compose.yml.

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# ── System deps ────────────────────────────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-dev \
        python3-pip \
        build-essential \
        git \
        curl \
    && ln -sf python3.11 /usr/bin/python3 \
    && ln -sf python3 /usr/bin/python \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────────────────────
WORKDIR /app

# ── Python deps (separate layer so code changes don't bust the cache) ─────────
# Install uv via pip, then use it for the fast dependency resolution.
# --system: no virtualenv inside the container, install straight into Python.
# sed strips inline comments so uv doesn't misparse version specs like
#   bitsandbytes>=0.46.1  # 0.49.2 tested …
RUN pip install --no-cache-dir --upgrade pip uv

COPY requirements.txt .
RUN sed 's/[[:space:]]*#.*//' requirements.txt > /tmp/req_clean.txt \
    && uv pip install --system --no-cache-dir -r /tmp/req_clean.txt

# ── Application code ───────────────────────────────────────────────────────────
COPY . .

# ── Streamlit config ───────────────────────────────────────────────────────────
# Disable browser auto-open and allow connections from outside the container.
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose both service ports
EXPOSE 8000 8501
