from __future__ import annotations

import logging
from typing import Any

from services.config import settings

logger = logging.getLogger(__name__)


def search_web(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    """Search the public web via DuckDuckGo (ddgs package)."""
    limit = top_k or settings.web_top_k
    from ddgs import DDGS

    results = list(DDGS().text(query, max_results=limit))
    logger.info("web_search query=%r hits=%d", query[:80], len(results))
    return results
