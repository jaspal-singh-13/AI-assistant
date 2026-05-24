"""Tool registry — returns the unified tool list for both models.

FR-TOOL-01: All tools defined here, same list passed to create_react_agent for both models.
NFR-EXT-02: Adding a new tool = one decorated function added to this file.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool


def get_tools() -> list[BaseTool]:
    """Return the list of all tools available to both models."""
    from tools.time_tool import get_current_time
    from tools.weather_tool import get_weather
    from tools.search_tool import web_search
    from tools.observability_tool import get_observability_summary
    from tools.evaluation_tool import get_evaluation_summary
    return [get_current_time, get_weather, web_search,
            get_observability_summary, get_evaluation_summary]
