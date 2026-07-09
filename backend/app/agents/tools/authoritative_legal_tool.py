"""Stub for authoritative legal tool.

This module was removed during architecture refactoring. The legal agent
still references it for fallback. Returns a structured failure so callers
degrade gracefully.
"""

from __future__ import annotations

import json
from typing import Any


class _StubTool:
    name = "probe_authoritative_legal_sources"

    @staticmethod
    def _run(enterprise_name: str = "", **kwargs: Any) -> str:
        return json.dumps({
            "success": False,
            "error": "authoritative_legal_tool has been removed; use cninfo_webapi_tool instead",
            "attempts": [],
        }, ensure_ascii=False)


probe_authoritative_legal_sources = _StubTool()
