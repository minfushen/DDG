"""Tool trace helpers with public-facing obfuscation.

Internal fields are useful for debugging, but frontend/report payloads should
only expose business capability names so the implementation toolchain is not
leaked in customer demos or exported reports.
"""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional

from .state import stable_id


TOOL_DISPLAY_NAMES = {
    "listed_company": ("上市主体识别", "本地企业线索库"),
    "financial_agent": ("财务专项分析", "专项分析引擎"),
    "industry_agent": ("行业专项分析", "专项分析引擎"),
    "listed_company_public_info": ("上市公司公开资料采集", "公开资料源"),
    "rag": ("授信知识库检索", "内部知识库"),
    "bocha": ("公开资料检索", "公开资料源"),
    "searxng": ("公开资料聚合检索", "搜索聚合网关"),
    "crawl4ai": ("网页正文解析", "网页解析服务"),
    "sequential_thinking": ("研究计划复核", "研究规划引擎"),
    "llm_planner": ("研究计划生成", "规划模型"),
}


def display_name_for(internal_tool_name: str) -> tuple[str, str]:
    return TOOL_DISPLAY_NAMES.get(internal_tool_name, ("专项工具调用", "内部工具服务"))


def start_tool_trace(
    *,
    research_task_id: str,
    internal_tool_name: str,
    query: str = "",
    query_summary: str = "",
    category: str = "general",
) -> Dict[str, Any]:
    display_tool_name, display_provider = display_name_for(internal_tool_name)
    started = datetime.now().isoformat()
    return {
        "tool_call_id": stable_id("tool", research_task_id, internal_tool_name, started),
        "research_task_id": research_task_id,
        "category": category,
        "internal_tool_name": internal_tool_name,
        "display_tool_name": display_tool_name,
        "provider": internal_tool_name,
        "display_provider": display_provider,
        "query": query,
        "query_summary": query_summary or _default_query_summary(internal_tool_name, category),
        "status": "running",
        "started_at": started,
        "ended_at": None,
        "elapsed_ms": None,
        "result_count": 0,
        "evidence_ids": [],
        "error": None,
        "_perf_started": perf_counter(),
    }


def finish_tool_trace(
    trace: Dict[str, Any],
    *,
    status: str,
    result_count: int = 0,
    evidence_ids: Optional[List[str]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    ended = datetime.now().isoformat()
    started = float(trace.pop("_perf_started", perf_counter()))
    trace.update({
        "status": status,
        "ended_at": ended,
        "elapsed_ms": int((perf_counter() - started) * 1000),
        "result_count": int(result_count or 0),
        "evidence_ids": evidence_ids or [],
        "error": error,
    })
    return trace


def public_tool_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    public_error = None
    if trace.get("status") == "failed":
        public_error = "调用失败，请检查后台配置或网络状态"
    return {
        "tool_call_id": trace.get("tool_call_id"),
        "research_task_id": trace.get("research_task_id"),
        "category": trace.get("category"),
        "display_tool_name": trace.get("display_tool_name"),
        "display_provider": trace.get("display_provider"),
        "query_summary": trace.get("query_summary"),
        "status": trace.get("status"),
        "started_at": trace.get("started_at"),
        "ended_at": trace.get("ended_at"),
        "elapsed_ms": trace.get("elapsed_ms"),
        "result_count": trace.get("result_count"),
        "evidence_ids": trace.get("evidence_ids") or [],
        "error": public_error,
    }


def public_tool_traces(traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [public_tool_trace(trace) for trace in traces]


def annotate_evidence(evidence: List[Dict[str, Any]], trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    for item in evidence:
        metadata = item.setdefault("metadata", {})
        metadata["tool_call_id"] = trace.get("tool_call_id")
        metadata["display_tool_name"] = trace.get("display_tool_name")
        metadata["display_provider"] = trace.get("display_provider")
        item["tool_call_id"] = trace.get("tool_call_id")
        item["display_tool_name"] = trace.get("display_tool_name")
        item["display_provider"] = trace.get("display_provider")
    return evidence


def _default_query_summary(internal_tool_name: str, category: str) -> str:
    if internal_tool_name == "bocha":
        return "检索公开资料线索"
    if internal_tool_name == "searxng":
        return "通过搜索聚合网关检索公开资料线索"
    if internal_tool_name == "crawl4ai":
        return "解析高价值网页正文"
    if internal_tool_name == "rag":
        return "检索授信审查知识片段"
    if internal_tool_name == "financial_agent":
        return "抽取并诊断财务专项指标"
    if internal_tool_name == "industry_agent":
        return "识别行业并生成经营环境诊断"
    if category:
        return f"执行{category}专项证据采集"
    return "执行专项工具调用"
