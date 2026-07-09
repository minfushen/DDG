"""Stub for business search tool (Tavily-based).

This module was removed during architecture refactoring. Returns a structured
failure so callers degrade gracefully.
"""

from __future__ import annotations

import json
from typing import Any


class _StubTool:
    name = "tavily_business_search"

    @staticmethod
    def _run(enterprise_name: str = "", **kwargs: Any) -> str:
        return json.dumps({
            "success": False,
            "error": "business_search_tool has been removed; use bocha_search_tool instead",
            "results": [],
        }, ensure_ascii=False)


tavily_business_search = _StubTool()
