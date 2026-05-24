"""Modal deployment — Presidio PII detection service.

Exposes a POST /detect endpoint that accepts {"text": "..."} and returns
{"entities": [{entity_type, start, end, score}, ...]} using Presidio with
spaCy en_core_web_lg for full NER (PERSON, LOCATION, ORGANIZATION, etc.).

Runs on CPU (no GPU needed). The spaCy model is baked into the container image
so there is no runtime download and no permission issues.

Deploy:
    modal deploy serve/presidio_modal.py

After deploying, copy the printed URL into .env / Streamlit Cloud secrets:
    PRESIDIO_SERVE_URL=https://<workspace>--presidio-serve-serve.modal.run
"""

from __future__ import annotations

import modal

MINUTES = 60

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "presidio-analyzer>=2.2",
        "presidio-anonymizer>=2.2",
        "spacy>=3.7",
        "fastapi>=0.111",
        "uvicorn>=0.29",
    )
    .run_commands("python -m spacy download en_core_web_lg")
)

app = modal.App("presidio-serve")


@app.function(
    image=image,
    scaledown_window=15 * MINUTES,
    timeout=5 * MINUTES,
)
@modal.asgi_app()
def serve():
    from fastapi import FastAPI
    from presidio_analyzer import AnalyzerEngine

    api = FastAPI(title="Presidio PII Detector")
    _analyzer = AnalyzerEngine()

    @api.get("/health")
    def health():
        return {"status": "ok", "service": "presidio-pii"}

    @api.post("/detect")
    def detect(payload: dict):
        text = payload.get("text", "")
        if not text:
            return {"entities": []}
        results = _analyzer.analyze(text=text, language="en")
        entities = [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": round(r.score, 4),
            }
            for r in results
        ]
        return {"entities": entities}

    return api
