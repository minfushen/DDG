"""Schemas for registered CodeAct tools.

The MVP deliberately supports only registered Python callables. It does not
execute arbitrary model-generated code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


CodeActCallable = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class CodeActToolSpec:
    name: str
    display_name: str
    description: str
    handler: CodeActCallable
    timeout_seconds: int = 30
    source_type: str = "codeact_tool"


@dataclass(frozen=True)
class CodeActRunResult:
    success: bool
    tool_name: str
    display_name: str
    elapsed_ms: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    source_type: str = "codeact_tool"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "display_name": self.display_name,
            "elapsed_ms": self.elapsed_ms,
            "result": self.result,
            "error": self.error,
            "source_type": self.source_type,
        }
