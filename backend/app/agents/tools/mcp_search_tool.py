"""Optional MCP search providers for public due-diligence signals.

The project can run without these MCP servers. When configured through env,
Exa MCP results are normalized into the same shape used by Tavily-backed tools.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import shlex

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters, stdio_client

from app.config import settings


_MCP_SYNC_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mcp-search-sync")


def _split_args(args: str) -> List[str]:
    return shlex.split(args or "")


def _provider_config(provider: str) -> Optional[Dict[str, str]]:
    if provider == "exa":
        url = settings.EXA_MCP_URL
        command = settings.EXA_MCP_COMMAND
        args = settings.EXA_MCP_ARGS
        tool = settings.EXA_MCP_TOOL
    else:
        return None
    if not command and not url:
        return None
    return {"url": url, "command": command, "args": args, "tool": tool}


def configured_mcp_search_providers() -> List[str]:
    return [provider for provider in ["exa"] if _provider_config(provider)]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content or "")


def _coerce_items(raw_text: str, provider: str) -> List[Dict[str, Any]]:
    text = (raw_text or "").strip()
    if not text:
        return []
    if text.lower().startswith("error:") or "Failed to get the VQD" in text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [{"title": f"{provider} 搜索摘要", "url": None, "content": text[:1200], "source": provider}]

    candidates = parsed.get("results") if isinstance(parsed, dict) else parsed
    if isinstance(candidates, dict):
        candidates = candidates.get("results") or candidates.get("items") or [candidates]
    if not isinstance(candidates, list):
        candidates = [parsed]
    items = []
    for item in candidates[:8]:
        if not isinstance(item, dict):
            items.append({"title": f"{provider} 搜索结果", "url": None, "content": str(item)[:1000], "source": provider})
            continue
        items.append({
            "title": item.get("title") or item.get("name") or f"{provider} 搜索结果",
            "url": item.get("url") or item.get("link"),
            "content": item.get("content") or item.get("text") or item.get("snippet") or item.get("summary") or "",
            "raw_content": item.get("raw_content") or item.get("rawContent") or "",
            "score": item.get("score", 0),
            "source": provider,
        })
    return items


async def _call_mcp_search(provider: str, query: str, max_results: int) -> Dict[str, Any]:
    config = _provider_config(provider)
    if not config:
        return {"success": False, "provider": provider, "error": "MCP provider not configured", "results": []}

    async def run_session(read: Any, write: Any) -> Dict[str, Any]:
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            tool_name = config.get("tool") or next((tool.name for tool in tools if "search" in tool.name.lower()), None)
            if not tool_name:
                return {"success": False, "provider": provider, "error": "No search-like MCP tool found", "results": []}
            payload_variants = [
                {"query": query, "num_results": max_results},
                {"query": query, "max_results": max_results},
                {"q": query, "max_results": max_results},
            ]
            last_error = ""
            for payload in payload_variants:
                try:
                    result = await session.call_tool(tool_name, payload)
                    raw_text = _content_to_text(result.content)
                    if raw_text.lower().strip().startswith("error:") or "Failed to get the VQD" in raw_text:
                        last_error = raw_text.strip()[:500]
                        continue
                    return {
                        "success": True,
                        "provider": provider,
                        "tool": tool_name,
                        "answer": raw_text[:1200],
                        "results": _coerce_items(raw_text, provider)[:max_results],
                    }
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
            return {"success": False, "provider": provider, "tool": tool_name, "error": last_error, "results": []}

    if config.get("url"):
        headers = {"Authorization": f"Bearer {settings.EXA_API_KEY}"} if provider == "exa" and settings.EXA_API_KEY else None
        async with streamablehttp_client(config["url"], headers=headers, timeout=settings.MCP_SEARCH_TIMEOUT_SECONDS) as (read, write, _session_id):
            return await run_session(read, write)

    server = StdioServerParameters(command=config["command"], args=_split_args(config.get("args", "")))
    async with stdio_client(server) as (read, write):
        return await run_session(read, write)


def search_with_mcp_providers(query: str, max_results: int = 6, providers: Optional[List[str]] = None) -> Dict[str, Any]:
    providers = providers or configured_mcp_search_providers()
    if not providers:
        return {"success": False, "error": "未配置 MCP 搜索服务", "results": [], "providers": []}

    async def run_all() -> List[Dict[str, Any]]:
        tasks = [_call_mcp_search(provider, query, max_results) for provider in providers]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def run_with_timeout() -> List[Dict[str, Any]]:
        return asyncio.run(asyncio.wait_for(run_all(), timeout=settings.MCP_SEARCH_TIMEOUT_SECONDS))

    try:
        try:
            asyncio.get_running_loop()
            outputs = _MCP_SYNC_EXECUTOR.submit(run_with_timeout).result(timeout=settings.MCP_SEARCH_TIMEOUT_SECONDS + 5)
        except RuntimeError:
            outputs = run_with_timeout()
    except Exception as exc:
        return {"success": False, "error": f"MCP 搜索超时或失败: {type(exc).__name__}", "results": [], "providers": providers}

    results: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    for output in outputs:
        if isinstance(output, Exception):
            attempts.append({"success": False, "error": f"{type(output).__name__}: {output}"})
            continue
        attempts.append({k: output.get(k) for k in ["provider", "tool", "success", "error"] if output.get(k) is not None})
        for item in output.get("results", []):
            item.setdefault("trust_level", "low")
            item.setdefault("confidence", 0.55)
            results.append(item)
    return {"success": bool(results), "results": results[:max_results], "attempts": attempts, "providers": providers}
