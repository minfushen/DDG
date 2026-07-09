"""Stub for authoritative business registry tool.

This module was removed during architecture refactoring. The business agent
and industry agent still reference it for fallback. Returns a structured
failure so callers degrade gracefully.
"""

from __future__ import annotations

import json
from typing import Any


class _StubTool:
    name = "fetch_authoritative_business_info"

    @staticmethod
    def _run(enterprise_name: str = "", **kwargs: Any) -> str:
        return json.dumps({
            "success": False,
            "error": "authoritative_business_tool has been removed; use cninfo_webapi_tool instead",
            "basic_info": {},
        }, ensure_ascii=False)


fetch_authoritative_business_info = _StubTool()
