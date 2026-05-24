"""FastAPI model server — OpenAI-compatible /v1/chat/completions endpoint.

Loads the OSS model once on GPU at startup. The Streamlit app connects to this
server via ChatOpenAI(base_url=OSS_SERVE_URL) so inference runs on GPU, not in
the Streamlit process.

Environment variables (read from .env or shell):
  OSS_MODEL_NAME   HuggingFace repo, default "Qwen/Qwen2.5-7B-Instruct"
  OSS_QUANT        "4bit" | "8bit" | "16bit" (default "16bit")
  OSS_HOST         bind host, default "0.0.0.0"
  OSS_PORT         bind port, default 8000

Run:
  python serve/model_server.py
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Iterator

import torch
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

load_dotenv()

MODEL_NAME: str = os.environ.get("OSS_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
QUANT: str = os.environ.get("OSS_QUANT", "16bit").lower()
HOST: str = os.environ.get("OSS_HOST", "0.0.0.0")
PORT: int = int(os.environ.get("OSS_PORT", "8000"))

app = FastAPI(title="OSS Model Server", version="1.0.0")

# ── Model + tokenizer (loaded once at startup) ────────────────────────────────
_model: AutoModelForCausalLM | None = None
_tokenizer: AutoTokenizer | None = None


def _load_model() -> None:
    global _model, _tokenizer
    print(f"[model_server] Loading {MODEL_NAME} in {QUANT} mode …", flush=True)
    t0 = time.time()

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

    if QUANT == "4bit":
        from transformers import BitsAndBytesConfig
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=bnb,
            device_map="auto",
            trust_remote_code=True,
        )
    elif QUANT == "8bit":
        from transformers import BitsAndBytesConfig
        bnb = BitsAndBytesConfig(load_in_8bit=True)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=bnb,
            device_map="auto",
            trust_remote_code=True,
        )
    else:  # 16bit
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )

    _model.eval()
    elapsed = time.time() - t0
    print(f"[model_server] Model ready in {elapsed:.1f}s  (quant={QUANT})", flush=True)


# ── Request / response schemas ────────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = MODEL_NAME
    messages: list[Message]
    max_tokens: int = 512
    temperature: float = 0.7
    stream: bool = False


# ── Generation helpers ────────────────────────────────────────────────────────

def _build_input_ids(messages: list[Message]) -> torch.Tensor:
    hf_messages = [{"role": m.role, "content": m.content} for m in messages]
    text = _tokenizer.apply_chat_template(
        hf_messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _tokenizer(text, return_tensors="pt").to(_model.device)
    return inputs


def _sse_chunk(delta: str, model: str, finish: str | None = None) -> str:
    """Format a single SSE data line in OpenAI streaming format."""
    payload = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": delta} if delta else {},
                "finish_reason": finish,
            }
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"


def _stream_response(request: ChatRequest) -> Iterator[str]:
    inputs = _build_input_ids(request.messages)
    streamer = TextIteratorStreamer(
        _tokenizer, skip_prompt=True, skip_special_tokens=True
    )
    gen_kwargs = {
        **inputs,
        "streamer": streamer,
        "max_new_tokens": request.max_tokens,
        "do_sample": request.temperature > 0,
        "temperature": request.temperature if request.temperature > 0 else 1.0,
    }
    thread = threading.Thread(target=_model.generate, kwargs=gen_kwargs)
    thread.start()

    for token in streamer:
        yield _sse_chunk(token, request.model)

    thread.join()
    yield _sse_chunk("", request.model, finish="stop")
    yield "data: [DONE]\n\n"


def _full_response(request: ChatRequest) -> str:
    inputs = _build_input_ids(request.messages)
    with torch.no_grad():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            do_sample=request.temperature > 0,
            temperature=request.temperature if request.temperature > 0 else 1.0,
        )
    # Decode only the newly generated tokens
    input_len = inputs["input_ids"].shape[1]
    new_ids = output_ids[0][input_len:]
    return _tokenizer.decode(new_ids, skip_special_tokens=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "quant": QUANT,
        "device": str(next(_model.parameters()).device) if _model else "not_loaded",
    }


@app.post("/v1/chat/completions")
def chat_completions(request: ChatRequest):
    if _model is None or _tokenizer is None:
        return JSONResponse(status_code=503, content={"error": "Model not loaded yet"})

    if request.stream:
        return StreamingResponse(
            _stream_response(request),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    t0 = time.time()
    text = _full_response(request)
    latency = time.time() - t0

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "latency_ms": round(latency * 1000, 1),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _load_model()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
