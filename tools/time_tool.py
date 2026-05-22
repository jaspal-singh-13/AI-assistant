"""Time tool — returns current datetime with timezone.

FR-TOOL-02: No external API, no API key required.
"""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """Return the current date and time with UTC offset."""
    now = datetime.now(timezone.utc).astimezone()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")
