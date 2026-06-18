"""Optional Sequential Thinking MCP adapter for the research engine.

The engine must remain useful without MCP. This module therefore keeps all MCP
imports lazy and returns structured fallback metadata instead of raising.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional
import asyncio
import json
import shlex

import httpx

from app.config import settings


_SEQUENTIAL_TOOLS_CACHE: Optional[Dict[str, Any]] = None
_SEQUENTIAL_TOOLS_LOCK: Optional[asyncio.Lock] = None


def _mcp_timeout() -> int:
    # npx stdio MCP servers are usually fast after warm-up, but cold starts and
    # npm cache checks can occasionally exceed 20-30 seconds on local networks.
    return max(int(settings.SEQUENTIAL_THINKING_MCP_TIMEOUT_SECONDS or 20), 45)


def _get_tools_lock() -> asyncio.Lock:
    global _SEQUENTIAL_TOOLS_LOCK
    if _SEQUENTIAL_TOOLS_LOCK is None:
        _SEQUENTIAL_TOOLS_LOCK = asyncio.Lock()
    return _SEQUENTIAL_TOOLS_LOCK


def _split_args(args: str) -> List[str]:
    return shlex.split(args or "")


def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    value = (text or "").strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"items": parsed}
    except json.JSONDecodeError:
        pass

    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(value[start : end + 1])
            return parsed if isinstance(parsed, dict) else {"items": parsed}
        except json.JSONDecodeError:
            return None
    return None


def _tool_output_to_text(output: Any) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or item))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        for key in ["text", "content", "output", "result"]:
            if output.get(key):
                return str(output[key])
        return json.dumps(output, ensure_ascii=False)
    content = getattr(output, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(output)


def _build_server_config() -> Dict[str, Any]:
    if str(settings.SEQUENTIAL_THINKING_TRANSPORT or "stdio").lower() in {"streamable_http", "streamable-http", "http"}:
        return {
            "sequential-thinking": {
                "url": settings.SEQUENTIAL_THINKING_REMOTE_URL,
                "transport": "streamable_http",
            }
        }
    return {
        "sequential-thinking": {
            "command": settings.SEQUENTIAL_THINKING_MCP_COMMAND,
            "args": _split_args(settings.SEQUENTIAL_THINKING_MCP_ARGS),
            "transport": "stdio",
        }
    }


async def load_sequential_thinking_tools() -> Dict[str, Any]:
    """Load Sequential Thinking MCP tools through langchain_mcp_adapters.

    Returns a small status object instead of throwing. This makes the feature
    suitable for private deployments where Node/npm access may be restricted.
    """

    if not settings.ENABLE_SEQUENTIAL_THINKING:
        return {"available": False, "tools": [], "error": "disabled"}

    transport = str(settings.SEQUENTIAL_THINKING_TRANSPORT or "stdio").lower()
    if transport in {"streamable_http", "streamable-http", "http"}:
        return {
            "available": bool(settings.SEQUENTIAL_THINKING_REMOTE_URL),
            "tools": [],
            "tool_names": ["sequentialthinking"],
            "transport": "streamable_http",
            "remote_url": settings.SEQUENTIAL_THINKING_REMOTE_URL,
            "error": "" if settings.SEQUENTIAL_THINKING_REMOTE_URL else "remote url not configured",
        }

    global _SEQUENTIAL_TOOLS_CACHE
    if _SEQUENTIAL_TOOLS_CACHE and _SEQUENTIAL_TOOLS_CACHE.get("available"):
        return _SEQUENTIAL_TOOLS_CACHE

    async with _get_tools_lock():
        if _SEQUENTIAL_TOOLS_CACHE and _SEQUENTIAL_TOOLS_CACHE.get("available"):
            return _SEQUENTIAL_TOOLS_CACHE

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except Exception as exc:  # pragma: no cover - depends on optional package
            return {"available": False, "tools": [], "error": f"import failed: {type(exc).__name__}: {exc}"}

        try:
            client = MultiServerMCPClient(_build_server_config())
            tools = await asyncio.wait_for(client.get_tools(), timeout=_mcp_timeout())
        except asyncio.TimeoutError:  # pragma: no cover - depends on external MCP runtime
            return {
                "available": False,
                "tools": [],
                "error": f"load timeout after {_mcp_timeout()}s; MCP will be skipped for this task",
            }
        except Exception as exc:  # pragma: no cover - depends on external MCP runtime
            return {"available": False, "tools": [], "error": f"load failed: {type(exc).__name__}: {exc}"}

        status = {
            "available": bool(tools),
            "tools": tools,
            "tool_names": [getattr(tool, "name", "") for tool in tools],
            "transport": "stdio",
            "error": "" if tools else "no tools returned",
        }
        if status.get("available"):
            _SEQUENTIAL_TOOLS_CACHE = status
        return status


def _pick_sequential_tool(tools: List[Any]) -> Optional[Any]:
    for tool in tools:
        name = getattr(tool, "name", "").lower()
        if "sequential" in name or "thinking" in name:
            return tool
    return tools[0] if tools else None


async def call_sequential_thinking(prompt: str, tools: Optional[List[Any]] = None) -> Dict[str, Any]:
    transport = str(settings.SEQUENTIAL_THINKING_TRANSPORT or "stdio").lower()
    if transport in {"streamable_http", "streamable-http", "http"}:
        return await call_sequential_thinking_step({
            "thought": prompt,
            "nextThoughtNeeded": False,
            "thoughtNumber": 1,
            "totalThoughts": 1,
        })

    loaded: Dict[str, Any] = {"available": True, "tools": tools or []}
    if tools is None:
        loaded = await load_sequential_thinking_tools()
        tools = loaded.get("tools", [])
    if not loaded.get("available") and not tools:
        return {"success": False, "error": loaded.get("error") or "Sequential Thinking MCP unavailable"}

    tool = _pick_sequential_tool(tools or [])
    if not tool:
        return {"success": False, "error": "No Sequential Thinking tool found"}

    payload_variants = [
        {"thought": prompt, "nextThoughtNeeded": False, "thoughtNumber": 1, "totalThoughts": 1},
        {"input": prompt},
        {"query": prompt},
    ]
    last_error = ""
    for payload in payload_variants:
        try:
            output = await asyncio.wait_for(tool.ainvoke(payload), timeout=_mcp_timeout())
            text = _tool_output_to_text(output)
            return {
                "success": True,
                "tool": getattr(tool, "name", "sequential-thinking"),
                "text": text,
                "json": _safe_json_loads(text),
            }
        except Exception as exc:  # pragma: no cover - depends on external MCP runtime
            last_error = f"{type(exc).__name__}: {exc}"
    return {"success": False, "tool": getattr(tool, "name", ""), "error": last_error}


async def call_sequential_thinking_step(payload: Dict[str, Any], tools: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Call Sequential Thinking with the official structured payload."""

    transport = str(settings.SEQUENTIAL_THINKING_TRANSPORT or "stdio").lower()
    if transport in {"streamable_http", "streamable-http", "http"}:
        if not settings.ENABLE_SEQUENTIAL_THINKING:
            return {"success": False, "error": "disabled"}
        if not settings.SEQUENTIAL_THINKING_REMOTE_URL:
            return {"success": False, "error": "remote url not configured"}
        try:
            async with httpx.AsyncClient(timeout=_mcp_timeout()) as client:
                response = await client.post(settings.SEQUENTIAL_THINKING_REMOTE_URL, json=payload)
                response.raise_for_status()
                data = response.json()
            text = _tool_output_to_text(data.get("result") if isinstance(data, dict) and data.get("result") else data)
            return {
                "success": True,
                "tool": "sequentialthinking",
                "transport": "streamable_http",
                "text": text,
                "json": _safe_json_loads(text),
            }
        except Exception as exc:  # pragma: no cover - depends on external service
            return {"success": False, "tool": "sequentialthinking", "transport": "streamable_http", "error": f"{type(exc).__name__}: {exc}"}

    loaded: Dict[str, Any] = {"available": True, "tools": tools or []}
    if tools is None:
        loaded = await load_sequential_thinking_tools()
        tools = loaded.get("tools", [])
    if not loaded.get("available") and not tools:
        return {"success": False, "error": loaded.get("error") or "Sequential Thinking MCP unavailable"}

    tool = _pick_sequential_tool(tools or [])
    if not tool:
        return {"success": False, "error": "No Sequential Thinking tool found"}
    try:
        output = await asyncio.wait_for(tool.ainvoke(payload), timeout=_mcp_timeout())
        text = _tool_output_to_text(output)
        return {
            "success": True,
            "tool": getattr(tool, "name", "sequential-thinking"),
            "transport": "stdio",
            "text": text,
            "json": _safe_json_loads(text),
        }
    except Exception as exc:  # pragma: no cover - depends on external MCP runtime
        return {"success": False, "tool": getattr(tool, "name", ""), "transport": "stdio", "error": f"{type(exc).__name__}: {exc}"}


async def run_sequential_thought_loop(
    enterprise_name: str,
    objective: str,
    default_tasks: List[Dict[str, Any]],
    tools: Optional[List[Any]] = None,
    session_id: Optional[str] = None,
    on_step: Optional[Callable[[Dict[str, Any], List[Dict[str, Any]]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """Record a short public research thought loop before LLM planning."""

    if not settings.ENABLE_SEQUENTIAL_THINKING:
        return {"success": False, "steps": [], "plan_context": "", "error": "disabled"}

    task_categories = sorted({str(task.get("category") or "general") for task in default_tasks})
    step_payloads = [
        {
            "thought": f"启动{enterprise_name}贷前尽调研究。先确认主体边界、研究目标和公开资料数据边界，避免简称、集团主体和上市主体混淆。目标：{objective}。",
            "thoughtNumber": 1,
            "totalThoughts": 3,
            "nextThoughtNeeded": True,
        },
        {
            "thought": "把研究拆成主体治理、近三年财务、司法合规、行业经营环境和授信边界五类证据需求，并优先调用权威数据、公开公告、RAG和客户上传材料。",
            "thoughtNumber": 2,
            "totalThoughts": 3,
            "nextThoughtNeeded": True,
        },
        {
            "thought": "形成计划生成上下文：每个研究任务必须可工具执行、可产生Evidence、可绑定Claim，并显式标注数据边界、人工确认点和二轮补证触发条件。",
            "thoughtNumber": 3,
            "totalThoughts": 3,
            "nextThoughtNeeded": False,
        },
    ]

    if session_id:
        for payload in step_payloads:
            payload["session_id"] = session_id

    steps: List[Dict[str, Any]] = []
    errors: List[str] = []
    for payload in step_payloads:
        result = await call_sequential_thinking_step(payload, tools=tools)
        if result.get("success"):
            parsed = result.get("json") if isinstance(result.get("json"), dict) else {}
            steps.append({
                "thoughtNumber": payload.get("thoughtNumber"),
                "totalThoughts": parsed.get("totalThoughts", payload.get("totalThoughts")),
                "nextThoughtNeeded": parsed.get("nextThoughtNeeded", payload.get("nextThoughtNeeded")),
                "summary": payload.get("thought"),
                "raw": parsed,
            })
            if on_step:
                await on_step(steps[-1], list(steps))
        else:
            errors.append(str(result.get("error") or "Sequential Thinking call failed"))
            break

    if not steps:
        return {"success": False, "steps": [], "plan_context": "", "error": "; ".join(errors) or "no steps recorded"}

    plan_context = "\n".join([
        f"研究思考链步骤{step['thoughtNumber']}：{step['summary']}" for step in steps
    ])
    plan_context += "\n覆盖风险域：" + "、".join(task_categories)
    return {
        "success": not errors,
        "steps": steps,
        "plan_context": plan_context,
        "error": "; ".join(errors),
    }


async def sequential_plan_review(enterprise_name: str, objective: str, tasks: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> Dict[str, Any]:
    categories = sorted({str(task.get("category") or "general") for task in tasks})
    prompt = "\n".join([
        "金融尽调研究计划检查点。",
        f"企业：{enterprise_name}",
        f"目标：{objective}",
        f"任务数量：{len(tasks)}",
        "任务类别：" + "、".join(categories),
        "下一步：按优先级执行工具检索，形成 Evidence、Claim 和 Gap。",
    ])
    result = await call_sequential_thinking(prompt, tools=tools)
    if result.get("success") and not isinstance(result.get("json"), dict):
        result["json"] = {
            "plan_notes": "Sequential Thinking MCP 已记录研究计划检查点；当前由规则规划器负责结构化任务生成。",
            "add_tasks": [],
            "evidence_priorities": ["权威主体信息", "近三年财务数据", "司法合规线索", "行业与授信政策知识"],
            "risk_focus": categories,
        }
    return result


async def sequential_gap_review(task: Dict[str, Any], evidence: List[Dict[str, Any]], gaps: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> Dict[str, Any]:
    high_trust_count = len([item for item in evidence if item.get("trust_level") == "high" or item.get("reliability") == "high"])
    prompt = "\n".join([
        "金融尽调证据缺口检查点。",
        "任务：" + str(task.get("question") or task.get("id") or ""),
        f"证据数量：{len(evidence)}",
        f"高可信证据数量：{high_trust_count}",
        f"规则识别缺口数量：{len(gaps)}",
        "下一步：如缺少权威来源或核心材料，进入补充检索/人工复核清单。",
    ])
    result = await call_sequential_thinking(prompt, tools=tools)
    if result.get("success") and not isinstance(result.get("json"), dict):
        result["json"] = {
            "gap_notes": "Sequential Thinking MCP 已记录证据缺口检查点；当前由规则 reflector 负责结构化缺口生成。",
            "extra_gaps": [],
            "follow_up_queries": [],
            "confidence_adjustment": 0,
        }
    return result
