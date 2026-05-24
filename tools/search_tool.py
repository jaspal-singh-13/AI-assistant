"""Web search tool — top 5 results via DuckDuckGo.

FR-TOOL-04: Uses ddgs Python package (free, no API key).
"""

from __future__ import annotations

from ddgs import DDGS
from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web and return the top 5 results as title + snippet + URL."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, start=1):
            lines.append(f"{i}. {r['title']}\n   {r['body']}\n   {r['href']}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"
