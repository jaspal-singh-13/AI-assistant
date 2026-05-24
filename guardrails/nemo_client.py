"""HTTP client for the NeMo Guardrails Modal service.

Calls NEMO_SERVE_URL if set; returns (False, None) gracefully on any failure
or when the env var is absent — other guardrail stages are unaffected.
"""

from __future__ import annotations

import os

import requests as _requests


def check_input(text: str) -> tuple[bool, str | None]:
    """Check user input against NeMo declarative rails.

    Returns (blocked, rail_description). Returns (False, None) if the service
    is unreachable or NEMO_SERVE_URL is not configured.
    """
    return _call("/check_input", text)


def check_output(text: str) -> tuple[bool, str | None]:
    """Check assistant output against NeMo declarative rails.

    Returns (blocked, rail_description). Returns (False, None) if the service
    is unreachable or NEMO_SERVE_URL is not configured.
    """
    return _call("/check_output", text)


def _call(path: str, text: str) -> tuple[bool, str | None]:
    url = os.environ.get("NEMO_SERVE_URL")
    if not url:
        return False, None
    try:
        resp = _requests.post(
            f"{url.rstrip('/')}{path}",
            json={"text": text},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get("blocked")), data.get("rail")
    except Exception:
        return False, None
