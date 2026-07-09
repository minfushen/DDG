"""Minimal streamable-HTTP MCP client for 元典 (Yuandian) Open Platform.

The three endpoints (law / case / company) all speak MCP over HTTP POST
(streamable HTTP).  This client performs the required initialize handshake and
exposes a single ``call_tool()`` method that returns the parsed tool result.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


class YuandianMcpError(Exception):
    """Raised when the MCP endpoint returns an error or invalid payload."""


class YuandianMcpClient:
    """Stateless MCP streamable-HTTP client for a single Yuandian endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not base_url or not api_key:
            raise YuandianMcpError("base_url and api_key are required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._protocol_version: Optional[str] = None

    # ── public ──────────────────────────────────────────────────────
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return the parsed JSON result.

        Always performs an initialize handshake first (the server appears
        stateless and does not return a persistent mcp-session-id).
        """
        self._initialize()
        return self._call_tool_internal(tool_name, arguments)

    # ── internals ───────────────────────────────────────────────────
    def _initialize(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": DEFAULT_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "ddg-agent", "version": "2.0.0"},
            },
        }
        data = self._post(payload)
        result = data.get("result") or {}
        self._protocol_version = result.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION

    def _call_tool_internal(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        data = self._post(payload)
        result = data.get("result") or {}
        if result.get("isError"):
            content_text = self._extract_text(result)
            raise YuandianMcpError(f"Tool {tool_name} returned error: {content_text[:500]}")
        return self._parse_content(result)

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.api_key}",
        }
        if self._protocol_version:
            headers["mcp-protocol-version"] = self._protocol_version

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.base_url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Yuandian MCP %s returned HTTP %s: %s", self.base_url, exc.response.status_code, exc.response.text[:300])
            raise YuandianMcpError(f"HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
        except httpx.RequestError as exc:
            logger.warning("Yuandian MCP %s request failed: %s", self.base_url, exc)
            raise YuandianMcpError(f"request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            logger.warning("Yuandian MCP %s returned non-JSON: %s", self.base_url, exc)
            raise YuandianMcpError(f"invalid JSON response: {exc}") from exc

    @staticmethod
    def _extract_text(result: Dict[str, Any]) -> str:
        content = result.get("content") or []
        if isinstance(content, list):
            parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _parse_content(result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse JSON embedded in the MCP tool result text."""
        text = YuandianMcpClient._extract_text(result)
        if not text:
            return {"success": False, "error": "empty tool result", "records": []}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Some tools may return plain text; wrap it.
            return {"success": True, "raw": text}
