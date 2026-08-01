"""Streamable HTTP wrapper for Sequential Thinking MCP.

This service exposes a small HTTP-compatible MCP-ish endpoint for local and
private deployments. The MVP intentionally keeps a built-in state recorder so
DDG-Agent can use the same request/response contract even when the official
stdio MCP server is not available in the runtime image.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os
import uuid

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field


HOST = os.getenv("SEQUENTIAL_WRAPPER_HOST", "0.0.0.0")
PORT = int(os.getenv("SEQUENTIAL_WRAPPER_PORT", "38001"))
MCP_PATH = os.getenv("SEQUENTIAL_WRAPPER_PATH", "/mcp")


class SequentialThinkingInput(BaseModel):
    thought: str = Field(..., description="Current thinking step")
    nextThoughtNeeded: bool = Field(..., description="Whether another thought step is needed")
    thoughtNumber: int = Field(..., ge=1, description="Current thought number")
    totalThoughts: int = Field(..., ge=1, description="Estimated total thoughts needed")
    isRevision: bool = Field(False, description="Whether this revises a previous thought")
    revisesThought: Optional[int] = Field(None, ge=1, description="Thought number being revised")
    branchFromThought: Optional[int] = Field(None, ge=1, description="Branching thought number")
    branchId: Optional[str] = Field(None, description="Branch identifier")
    needsMoreThoughts: bool = Field(False, description="Whether more thoughts are needed")
    session_id: Optional[str] = Field(None, description="Optional task/session isolation key")


app = FastAPI(title="Sequential Thinking Wrapper", version="0.1.0")
_history_by_session: Dict[str, List[Dict[str, Any]]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_id(payload: SequentialThinkingInput) -> str:
    return payload.session_id or "default"


def _record_thought(payload: SequentialThinkingInput) -> Dict[str, Any]:
    session_id = _session_id(payload)
    history = _history_by_session.setdefault(session_id, [])
    total_thoughts = max(payload.totalThoughts, payload.thoughtNumber)
    branches = sorted({item.get("branchId") for item in history if item.get("branchId")})
    if payload.branchId and payload.branchId not in branches:
        branches.append(payload.branchId)

    entry = {
        "id": f"thought_{uuid.uuid4().hex[:12]}",
        "session_id": session_id,
        "thought": payload.thought,
        "thoughtNumber": payload.thoughtNumber,
        "totalThoughts": total_thoughts,
        "nextThoughtNeeded": payload.nextThoughtNeeded,
        "isRevision": payload.isRevision,
        "revisesThought": payload.revisesThought,
        "branchFromThought": payload.branchFromThought,
        "branchId": payload.branchId,
        "needsMoreThoughts": payload.needsMoreThoughts,
        "created_at": _utc_now(),
    }
    history.append(entry)
    return {
        "thoughtNumber": payload.thoughtNumber,
        "totalThoughts": total_thoughts,
        "nextThoughtNeeded": payload.nextThoughtNeeded,
        "branches": branches,
        "thoughtHistoryLength": len(history),
        "session_id": session_id,
        "isRevision": payload.isRevision,
        "revisesThought": payload.revisesThought,
    }


def _mcp_text_response(data: Dict[str, Any]) -> Dict[str, Any]:
    # Match the common MCP tool response shape enough for langchain adapters and
    # direct HTTP fallback clients to parse the result deterministically.
    import json

    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "sequential-thinking-wrapper", "path": MCP_PATH}


@app.post("/sequentialthinking")
async def sequentialthinking_direct(payload: SequentialThinkingInput) -> Dict[str, Any]:
    return _mcp_text_response(_record_thought(payload))


@app.post(MCP_PATH)
async def mcp_entrypoint(request: Request) -> Dict[str, Any]:
    body = await request.json()

    # JSON-RPC-ish MCP request.
    if isinstance(body, dict) and "params" in body:
        params = body.get("params") or {}
        arguments = params.get("arguments") if isinstance(params, dict) else None
        payload_data = arguments or params
        payload = SequentialThinkingInput(**payload_data)
        result = _mcp_text_response(_record_thought(payload))
        if "id" in body:
            return {"jsonrpc": "2.0", "id": body.get("id"), "result": result}
        return result

    payload = SequentialThinkingInput(**body)
    return _mcp_text_response(_record_thought(payload))


if __name__ == "__main__":
    import uvicorn

    print(f"Starting Sequential Thinking wrapper at http://{HOST}:{PORT}{MCP_PATH}")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
