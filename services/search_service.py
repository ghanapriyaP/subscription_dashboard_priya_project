"""
search_service.py
-----------------
DuckDuckGo web search integration for real-time tool pricing and alternatives.
Free, no API key required.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> List[dict]:
    """
    Search the web using DuckDuckGo and return structured results.
    Used by the AI agent to fetch real-time pricing, alternatives, and feature info.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return [{"title": "Search unavailable", "snippet": str(e), "url": ""}]
