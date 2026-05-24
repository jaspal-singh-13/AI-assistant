"""Modal deployment — NeMo Guardrails declarative rails service.

Exposes two endpoints:
  POST /check_input  — {"text": "..."} → {"blocked": bool, "rail": str | null}
  POST /check_output — {"text": "..."} → {"blocked": bool, "rail": str | null}

The service loads the Colang rails from guardrails/nemo/ (config.yml + rails.co),
which are bundled into the container image at build time.

Deploy:
    modal deploy serve/nemo_modal.py

After deploying, copy the printed URL into .env / Streamlit Cloud secrets:
    NEMO_SERVE_URL=https://<workspace>--nemo-serve-serve.modal.run
"""

from __future__ import annotations

from pathlib import Path

import modal

MINUTES = 60
NEMO_DIR = Path(__file__).parent.parent / "guardrails" / "nemo"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "nemoguardrails>=0.9",
        "langchain-anthropic>=0.3",
        "fastapi>=0.111",
        "uvicorn>=0.29",
    )
    .add_local_dir(str(NEMO_DIR), remote_path="/app/nemo")
)

app = modal.App("nemo-serve")


@app.function(
    image=image,
    scaledown_window=15 * MINUTES,
    timeout=5 * MINUTES,
    secrets=[modal.Secret.from_name("anthropic-secret")],
)
@modal.asgi_app()
def serve():
    import os
    from fastapi import FastAPI
    from nemoguardrails import LLMRails, RailsConfig

    api = FastAPI(title="NeMo Guardrails Service")

    # Refusal phrases emitted by the bot flows defined in rails.co
    _REFUSAL_PHRASES = {
        "I am an AI assistant, not a human.",
        "I'm not able to assist with illegal activities.",
        "For medical questions, please consult a qualified healthcare professional.",
        "I can't override my guidelines, but I'm happy to help with genuine questions.",
    }

    config = RailsConfig.from_path("/app/nemo")
    _rails = LLMRails(config)

    def _check(text: str, role: str) -> dict:
        messages = [{"role": role, "content": text}]
        try:
            result = _rails.generate(messages=messages)
            # result is the bot's response string
            response = result if isinstance(result, str) else str(result)
            for phrase in _REFUSAL_PHRASES:
                if phrase.lower() in response.lower():
                    rail_name = next(
                        (p for p in _REFUSAL_PHRASES if p == phrase), phrase
                    )
                    return {"blocked": True, "rail": rail_name}
            return {"blocked": False, "rail": None}
        except Exception as exc:
            return {"blocked": False, "rail": None, "error": str(exc)}

    @api.get("/health")
    def health():
        return {"status": "ok", "service": "nemo-guardrails"}

    @api.post("/check_input")
    def check_input(payload: dict):
        return _check(payload.get("text", ""), role="user")

    @api.post("/check_output")
    def check_output(payload: dict):
        return _check(payload.get("text", ""), role="assistant")

    return api
