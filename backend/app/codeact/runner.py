"""Runner for registered CodeAct tools."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from time import perf_counter
from typing import Any, Dict, List, Optional

from app.config.settings import settings

from .registry import get_codeact_tool, list_registered_codeact_tools
from .schemas import CodeActRunResult


def list_codeact_tools() -> List[Dict[str, Any]]:
    return list_registered_codeact_tools()


def run_codeact_tool(tool_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run one whitelisted CodeAct tool and return a structured result."""
    started = perf_counter()
    normalized_name = str(tool_name or "").strip()
    if not getattr(settings, "ENABLE_CODEACT_TOOLS", True):
        return _result(
            success=False,
            tool_name=normalized_name,
            display_name="代码工具执行",
            started=started,
            error="CodeAct tools are disabled by configuration",
        )

    spec = get_codeact_tool(normalized_name)
    if not spec:
        return _result(
            success=False,
            tool_name=normalized_name,
            display_name="代码工具执行",
            started=started,
            error=f"Unknown CodeAct tool: {normalized_name}",
        )

    safe_payload = payload or {}
    if not isinstance(safe_payload, dict):
        return _result(
            success=False,
            tool_name=spec.name,
            display_name=spec.display_name,
            source_type=spec.source_type,
            started=started,
            error="CodeAct payload must be a JSON object",
        )

    timeout = int(spec.timeout_seconds or getattr(settings, "CODEACT_DEFAULT_TIMEOUT_SECONDS", 30) or 30)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(spec.handler, safe_payload)
            result = future.result(timeout=timeout)
        return _result(
            success=True,
            tool_name=spec.name,
            display_name=spec.display_name,
            source_type=spec.source_type,
            started=started,
            result=_json_safe(result),
        )
    except FutureTimeoutError:
        return _result(
            success=False,
            tool_name=spec.name,
            display_name=spec.display_name,
            source_type=spec.source_type,
            started=started,
            error=f"CodeAct tool timed out after {timeout}s",
        )
    except Exception as exc:
        return _result(
            success=False,
            tool_name=spec.name,
            display_name=spec.display_name,
            source_type=spec.source_type,
            started=started,
            error=str(exc),
        )


def _result(
    *,
    success: bool,
    tool_name: str,
    display_name: str,
    started: float,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    source_type: str = "codeact_tool",
) -> Dict[str, Any]:
    return CodeActRunResult(
        success=success,
        tool_name=tool_name,
        display_name=display_name,
        elapsed_ms=int((perf_counter() - started) * 1000),
        result=result,
        error=error,
        source_type=source_type,
    ).to_dict()


def _json_safe(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        json.dumps(value, ensure_ascii=False)
        return value
    json.dumps(value, ensure_ascii=False)
    return {"value": value}
