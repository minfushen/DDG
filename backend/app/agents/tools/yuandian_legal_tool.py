"""元典法律/案例数据工具（Yuandian Open Platform）。

直接通过 streamable-HTTP MCP 调用：
- law 端点：法律法规语义/关键词检索
- case 端点：裁判文书/案例语义检索

返回统一的 ``{"success": bool, "total": int, "records": [...], "error": str}``
结构，方便 ``tool_router.py`` 做降级处理。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config.settings import settings

from .yuandian_mcp_client import YuandianMcpClient, YuandianMcpError

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 10


def _law_client() -> YuandianMcpClient:
    return YuandianMcpClient(
        base_url=settings.YUANDIAN_LAW_MCP_URL,
        api_key=settings.YUANDIAN_API_KEY,
        timeout=float(settings.YUANDIAN_MCP_TIMEOUT_SECONDS),
    )


def _case_client() -> YuandianMcpClient:
    return YuandianMcpClient(
        base_url=settings.YUANDIAN_CASE_MCP_URL,
        api_key=settings.YUANDIAN_API_KEY,
        timeout=float(settings.YUANDIAN_MCP_TIMEOUT_SECONDS),
    )


def _extract_records(raw: Dict[str, Any]) -> List[Any]:
    """Extract record list from Yuandian's varying response envelopes."""
    if not isinstance(raw, dict):
        return []
    # case/law vector search uses dataPreview.extra.wenshu or extra.wenshu
    for key in ("dataPreview", "structuredContent"):
        node = raw.get(key)
        if isinstance(node, dict):
            extra = node.get("extra")
            if isinstance(extra, dict):
                if "wenshu" in extra and isinstance(extra["wenshu"], list):
                    return extra["wenshu"]
                if "fatiao" in extra and isinstance(extra["fatiao"], list):
                    return extra["fatiao"]
    extra = raw.get("extra") or {}
    if isinstance(extra, dict):
        if "wenshu" in extra and isinstance(extra["wenshu"], list):
            return extra["wenshu"]
        if "fatiao" in extra and isinstance(extra["fatiao"], list):
            return extra["fatiao"]
    # structuredContent.data or dataPreview.data
    for key in ("structuredContent", "dataPreview"):
        node = raw.get(key)
        if isinstance(node, dict):
            data = node.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
    # direct data/records/result
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
    # If the API reports failure via ok/status, surface it.
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


# ──────────────────────────────────────────────────────────────
# Laws & regulations
# ──────────────────────────────────────────────────────────────

def search_laws(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """法律法规语义检索。"""
    guard = _guard_config()
    if guard:
        return guard
    try:
        raw = _law_client().call_tool(
            "yuandian_law_vector_search",
            {"query": query, "return_num": top_k},
        )
        return _normalize_result(raw)
    except YuandianMcpError as exc:
        logger.warning("yuandian law search failed: %s", exc)
        return {"success": False, "error": str(exc), "records": []}


# ──────────────────────────────────────────────────────────────
# Cases / judicial risk
# ──────────────────────────────────────────────────────────────

def search_cases(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """裁判文书/案例语义检索。"""
    guard = _guard_config()
    if guard:
        return guard
    try:
        raw = _case_client().call_tool(
            "yuandian_case_vector_search",
            {"query": query, "return_num": top_k},
        )
        return _normalize_result(raw)
    except YuandianMcpError as exc:
        logger.warning("yuandian case search failed: %s", exc)
        return {"success": False, "error": str(exc), "records": []}


def search_cases_by_keyword(
    keyword: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """普通案例关键词检索。"""
    guard = _guard_config()
    if guard:
        return guard
    try:
        raw = _case_client().call_tool(
            "yuandian_rh_ptal_search",
            {"keyword": keyword, "top_k": top_k},
        )
        return _normalize_result(raw)
    except YuandianMcpError as exc:
        logger.warning("yuandian case keyword search failed: %s", exc)
        return {"success": False, "error": str(exc), "records": []}


# ──────────────────────────────────────────────────────────────
# Case summary extraction
# ──────────────────────────────────────────────────────────────

def _format_judgment_date(date_value: Any) -> Optional[str]:
    """Convert Yuandian date int (YYYYMMDD) or str to ISO date."""
    if date_value is None or date_value == "":
        return None
    s = str(date_value)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


_CAUSE_KEYWORDS = (
    "物业服务合同", "买卖合同", "股权转让", "商标权", "著作权", "专利权",
    "不正当竞争", "行政处罚", "行政非诉", "行政强制", "非诉执行审查",
    "非诉", "执行审查", "执行", "审查", "处罚", "强制", "侵权",
    "罚款", "行政",
)


def _strip_cause_keyword(text: str) -> str:
    """Remove common trailing case-cause keywords from a party string."""
    while True:
        stripped = text
        for kw in _CAUSE_KEYWORDS:
            if stripped.endswith(kw):
                stripped = stripped[: -len(kw)]
                break
        if stripped == text:
            return stripped
        text = stripped


def _parse_parties(title: str) -> Dict[str, List[str]]:
    """Heuristically extract parties from a case title.

    Typical formats:
    - ``刘露与才元勋买卖合同纠纷二审裁定书``
    - ``华为技术有限公司、东阳市横店博睿电脑商行侵害商标权纠纷二审民事裁定书``
    - ``绍兴市越城区沥海街道办事处;绍兴某有限公司;行政处罚...``

    Returns ``plaintiffs`` / ``defendants`` only when a clear separator
    ("与"/"和") is present; otherwise all candidates go into ``parties``.
    This is best-effort parsing from the list view; exact roles need detail view.
    """
    if not title:
        return {"parties": [], "plaintiffs": [], "defendants": []}

    # Strip trailing procedure / document suffixes.
    stripped = title
    for suffix in (
        "一审", "二审", "再审", "行政", "民事", "刑事", "执行",
        "裁定书", "判决书", "调解书", "决定书", "通知书",
    ):
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)]

    # Find the first occurrence of a case-cause marker and cut there.
    for marker in ("纠纷", "争议", "申请", "执行", "处罚", "赔偿"):
        idx = stripped.find(marker)
        if idx != -1:
            stripped = stripped[:idx]
            break

    # Clear plaintiff/defendant separator.
    if "与" in stripped:
        left, right = stripped.split("与", 1)
        plaintiffs = [p for p in (_strip_cause_keyword(p.strip()) for p in left.split("、")) if p]
        defendants = [p for p in (_strip_cause_keyword(p.strip()) for p in right.split("、")) if p]
        return {"parties": plaintiffs + defendants, "plaintiffs": plaintiffs, "defendants": defendants}
    if "和" in stripped:
        left, right = stripped.split("和", 1)
        plaintiffs = [p for p in (_strip_cause_keyword(p.strip()) for p in left.split("、")) if p]
        defendants = [p for p in (_strip_cause_keyword(p.strip()) for p in right.split("、")) if p]
        return {"parties": plaintiffs + defendants, "plaintiffs": plaintiffs, "defendants": defendants}

    # No clear role separator: collect all party candidates.
    for sep in (";", "、"):
        if sep in stripped:
            parts = [p for p in (_strip_cause_keyword(p.strip()) for p in stripped.split(sep)) if p]
            return {"parties": parts, "plaintiffs": [], "defendants": []}

    # Fallback: whole prefix as a single party.
    single = _strip_cause_keyword(stripped.strip())
    return {"parties": [single] if single else [], "plaintiffs": [], "defendants": []}


def _extract_case_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structured summary from a Yuandian case record."""
    title = record.get("title") or ""
    parties = _parse_parties(title)
    return {
        "title": title,
        "case_number": record.get("ah") or "",
        "court": record.get("jbdw") or "",
        "court_level": record.get("cj") or "",
        "case_category": record.get("ajlb") or "",
        "trial_procedure": record.get("spcx") or "",
        "document_type": record.get("wszl") or "",
        "case_cause": ", ".join(record.get("anyou") or []),
        "judgment_date": _format_judgment_date(record.get("jaDate")),
        "parties": parties["parties"],
        "plaintiffs": parties["plaintiffs"],
        "defendants": parties["defendants"],
        "amount": None,  # 列表接口未直接返回涉案金额；如需可再调详情接口
        "url": record.get("url") or "",
    }


def _aggregate_distribution(records: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    dist: Dict[str, int] = {}
    for r in records:
        value = r.get(field)
        if isinstance(value, list):
            for v in value:
                key = str(v).strip()
                if key:
                    dist[key] = dist.get(key, 0) + 1
        elif value:
            key = str(value).strip()
            if key:
                dist[key] = dist.get(key, 0) + 1
    return dist


def build_legal_risk_profile(
    enterprise_name: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """构建企业司法风险画像。

    使用案例语义检索查询企业相关的诉讼、被执行、失信、行政处罚等记录，
    返回**结构化摘要**（涉案金额、原告/被告、审理法院等级等），
    不返回完整文书内容，供 ``tool_router.py`` 生成 evidence。
    """
    guard = _guard_config()
    if guard:
        return guard

    query = f"{enterprise_name} 诉讼 仲裁 被执行 失信 行政处罚"
    result = search_cases(query, top_k=top_k)
    if not result.get("success"):
        return result

    records = result.get("records") or []
    if not records and isinstance(result.get("data"), list):
        records = result["data"]

    case_summaries = [_extract_case_summary(r) for r in records if isinstance(r, dict)]

    return {
        "success": True,
        "enterprise_name": enterprise_name,
        "total": result.get("total", len(records)),
        "case_summaries": case_summaries,
        "summary": {
            "total": len(records),
            "court_level_distribution": _aggregate_distribution(records, "cj"),
            "case_category_distribution": _aggregate_distribution(records, "ajlb"),
            "case_cause_distribution": _aggregate_distribution(records, "anyou"),
            "trial_procedure_distribution": _aggregate_distribution(records, "spcx"),
        },
    }
