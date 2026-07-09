"""元典企业信息工具（Yuandian Open Platform）。

直接通过 streamable-HTTP MCP 调用 company 端点，获取：
- 企业基础信息（股东、法定代表人、注册资本等）
- 企业涉诉统计（案件数量、案由分布）
- 经营异常、行政处罚、股权冻结等风险摘要

返回统一结构供 ``tool_router.py`` 使用。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.config.settings import settings

from .yuandian_mcp_client import YuandianMcpClient, YuandianMcpError

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5


def _company_client() -> YuandianMcpClient:
    return YuandianMcpClient(
        base_url=settings.YUANDIAN_COMPANY_MCP_URL,
        api_key=settings.YUANDIAN_API_KEY,
        timeout=float(settings.YUANDIAN_MCP_TIMEOUT_SECONDS),
    )


def _extract_records(raw: Dict[str, Any]) -> List[Any]:
    """Extract record list from Yuandian's varying response envelopes."""
    if not isinstance(raw, dict):
        return []
    for key in ("structuredContent", "dataPreview"):
        node = raw.get(key)
        if isinstance(node, dict):
            data = node.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
    for key in ("data", "records", "result"):
        val = raw.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            return [val]
    return []


def _normalize_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Yuandian API response to the contract used by tool_router."""
    if isinstance(raw, dict) and "success" in raw and not raw.get("ok"):
        return raw
    if not isinstance(raw, dict):
        return {"success": False, "error": f"unexpected response type: {type(raw).__name__}", "records": []}

    records = _extract_records(raw)
    if raw.get("ok") is False or (isinstance(raw.get("status"), int) and raw["status"] >= 400):
        message = raw.get("message") or raw.get("error") or "Yuandian API error"
        return {"success": False, "error": message, "records": records}

    return {
        "success": True,
        "total": raw.get("itemCount") or raw.get("total") or len(records),
        "records": records,
    }


def _guard_config() -> Optional[Dict[str, Any]]:
    if not settings.YUANDIAN_API_KEY:
        return {"success": False, "error": "YUANDIAN_API_KEY not configured", "records": []}
    return None


def _safe_id(company_info: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Extract id / tyshxydm from a company info record."""
    if not isinstance(company_info, dict):
        return None, None
    records = _extract_records(company_info)
    if not records:
        return None, None
    record = records[0] if isinstance(records, list) else company_info
    if not isinstance(record, dict):
        return None, None
    enterprise_id = (
        record.get("id")
        or record.get("enterpriseId")
        or record.get("企业ID")
    )
    tyshxydm = (
        record.get("tyshxydm")
        or record.get("creditCode")
        or record.get("统一社会信用代码")
        or record.get("统一社会信用代码码")
    )
    return enterprise_id, tyshxydm


# ──────────────────────────────────────────────────────────────
# Company lookup
# ──────────────────────────────────────────────────────────────

def search_company(
    name: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """按企业名称关键词检索企业候选列表。"""
    guard = _guard_config()
    if guard:
        return guard
    try:
        raw = _company_client().call_tool(
            "yuandian_rh_enterpriseSearch",
            {"name": name, "top_k": top_k},
        )
        return _normalize_result(raw)
    except YuandianMcpError as exc:
        logger.warning("yuandian company search failed: %s", exc)
        return {"success": False, "error": str(exc), "records": []}


def get_company_base_info(
    enterprise_id: str = "",
    tyshxydm: str = "",
) -> Dict[str, Any]:
    """查询企业工商基础信息（股东、法人、注册资本等）。"""
    guard = _guard_config()
    if guard:
        return guard
    if not enterprise_id and not tyshxydm:
        return {"success": False, "error": "enterprise_id or tyshxydm required", "records": []}
    try:
        args: Dict[str, Any] = {}
        if enterprise_id:
            args["id"] = enterprise_id
        if tyshxydm:
            args["tyshxydm"] = tyshxydm
        raw = _company_client().call_tool("yuandian_rh_enterpriseBaseInfo", args)
        return _normalize_result(raw)
    except YuandianMcpError as exc:
        logger.warning("yuandian company base info failed: %s", exc)
        return {"success": False, "error": str(exc), "records": []}


def get_company_risk_summary(
    enterprise_id: str = "",
    tyshxydm: str = "",
) -> Dict[str, Any]:
    """查询企业涉诉信息统计。"""
    guard = _guard_config()
    if guard:
        return guard
    if not enterprise_id and not tyshxydm:
        return {"success": False, "error": "enterprise_id or tyshxydm required", "records": []}
    try:
        args: Dict[str, Any] = {}
        if enterprise_id:
            args["id"] = enterprise_id
        if tyshxydm:
            args["tyshxydm"] = tyshxydm
        raw = _company_client().call_tool("yuandian_rh_enterpriseWritAgg", args)
        return _normalize_result(raw)
    except YuandianMcpError as exc:
        logger.warning("yuandian company risk summary failed: %s", exc)
        return {"success": False, "error": str(exc), "records": []}


# ──────────────────────────────────────────────────────────────
# Composite business profile
# ──────────────────────────────────────────────────────────────

def build_business_profile(
    enterprise_name: str,
) -> Dict[str, Any]:
    """构建企业工商+司法风险画像。

    流程：
    1. 通过名称查询企业详情，拿到 id / 统一社会信用代码。
    2. 查询企业工商基础信息。
    3. 查询涉诉统计。
    """
    guard = _guard_config()
    if guard:
        return guard

    search_result = search_company(enterprise_name)
    if not search_result.get("success"):
        return {
            "success": False,
            "error": search_result.get("error") or "企业检索失败",
            "enterprise_name": enterprise_name,
            "basic_info": {},
            "risk_summary": {},
        }

    enterprise_id, tyshxydm = _safe_id(search_result)
    if not enterprise_id and not tyshxydm:
        return {
            "success": False,
            "error": "企业检索未返回有效 ID 或统一社会信用代码",
            "enterprise_name": enterprise_name,
            "basic_info": {},
            "risk_summary": {},
        }

    base_info = get_company_base_info(enterprise_id or "", tyshxydm or "")
    risk_summary = get_company_risk_summary(enterprise_id or "", tyshxydm or "")

    # Surface upstream failures without pretending success.
    if not base_info.get("success") and not risk_summary.get("success"):
        return {
            "success": False,
            "error": base_info.get("error") or risk_summary.get("error") or "企业详情接口调用失败",
            "enterprise_name": enterprise_name,
            "basic_info": base_info,
            "risk_summary": risk_summary,
        }

    return {
        "success": True,
        "enterprise_name": enterprise_name,
        "enterprise_id": enterprise_id,
        "tyshxydm": tyshxydm,
        "basic_info": base_info,
        "risk_summary": risk_summary,
    }
