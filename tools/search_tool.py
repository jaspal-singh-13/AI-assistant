"""Web search tool — top 5 results via DuckDuckGo.

FR-TOOL-04: Uses duckduckgo-search Python package (free, no API key).
"""

from __future__ import annotations

# TODO (Phase 1): uncomment once langchain + duckduckgo-search are installed
# from langchain_core.tools import tool
# from duckduckgo_search import DDGS
#
# @tool
# def web_search(query: str) -> str:
#     """Search the web and return the top 5 results as title + snippet + URL."""
#     try:
#         with DDGS() as ddgs:
#             results = list(ddgs.text(query, max_results=5))
#         if not results:
#             return "No results found."
#         lines = []
#         for i, r in enumerate(results, start=1):
#             lines.append(f"{i}. {r['title']}\n   {r['body']}\n   {r['href']}")
#         return "\n\n".join(lines)
#     except Exception as e:
#         return f"Search failed: {e}"


def web_search(query: str) -> str:
    """Search the web and return top 5 results. (stub — Phase 1)"""
    raise NotImplementedError("Phase 1 — web_search")
