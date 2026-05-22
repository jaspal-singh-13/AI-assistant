"""Time tool — returns current datetime with timezone.

FR-TOOL-02: No external API, no API key required.
"""

from __future__ import annotations

# TODO (Phase 1): uncomment once langchain is installed
# from langchain_core.tools import tool
# from datetime import datetime, timezone
#
# @tool
# def get_current_time() -> str:
#     """Return the current date and time with UTC offset."""
#     now = datetime.now(timezone.utc).astimezone()
#     return now.strftime("%Y-%m-%d %H:%M:%S %Z")


def get_current_time() -> str:
    """Return the current date and time with UTC offset. (stub — Phase 1)"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).astimezone()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")
