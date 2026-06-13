# ========================================
# 司法公开信息搜索工具
# 使用 Tavily 获取企业涉诉、执行、处罚等公开候选来源
# ========================================

from __future__ import annotations

from typing import Any, Dict, List, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx
import json

from app.config import settings
from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.mcp_search_tool import search_with_mcp_providers
from app.agents.tools.bocha_search_tool import search_with_bocha


class SearchLegalInfoInput(BaseModel):
    """司法搜索输入。"""

    enterprise_name: str = Field(description="企业名称")


HIGH_TRUST_DOMAINS = [
    "court.gov.cn",
    "wenshu.court.gov.cn",
    "zxgk.court.gov.cn",
    "creditchina.gov.cn",
    "gsxt.gov.cn",
    "cninfo.com.cn",
    "static.cninfo.com.cn",
]
MEDIUM_TRUST_DOMAINS = ["qcc.com", "tianyancha.com", "aiqicha.baidu.com", "qixin.com", "lawtime.cn"]


def source_confidence(url: str) -> tuple[str, float]:
    if any(domain in url for domain in HIGH_TRUST_DOMAINS):
        return "high", 0.9
    if any(domain in url for domain in MEDIUM_TRUST_DOMAINS):
        return "medium", 0.75
    return "low", 0.55


class TavilyLegalSearchTool(BaseTool):
    """Tavily 司法公开信息搜索工具。"""

    name: str = "tavily_legal_search"
    description: str = "通过 Tavily 搜索企业裁判文书、被执行、失信、行政处罚、开庭公告等公开司法风险线索。"
    args_schema: Type[BaseModel] = SearchLegalInfoInput

    def _mcp_fallback(self, enterprise_name: str, query: str) -> Dict[str, Any]:
        bocha_result = search_with_bocha(query=query, max_results=10, freshness="oneYear", summary=True)
        if bocha_result.get("success"):
            return {
                "success": True,
                "enterprise_name": enterprise_name,
                "answer": "",
                "results": bocha_result.get("results", []),
                "bocha_log_id": bocha_result.get("log_id"),
                "generated_from": "博查公开搜索兜底",
            }
        mcp_result = search_with_mcp_providers(query=query, max_results=10)
        return {
            "success": mcp_result.get("success", False),
            "enterprise_name": enterprise_name,
            "answer": "",
            "results": mcp_result.get("results", []),
            "mcp_attempts": mcp_result.get("attempts", []),
            "generated_from": "MCP公开搜索兜底",
        }

    def _run(self, enterprise_name: str) -> str:
        listed_company = resolve_listed_company(enterprise_name)
        normalized_name = listed_company.get("company_name") if listed_company else enterprise_name
        query = (
            f"{normalized_name} 司法风险 裁判文书 被执行人 失信被执行 行政处罚 "
            "开庭公告 案由 案号 中国裁判文书网 中国执行信息公开网"
        )
        if not settings.TAVILY_API_KEY:
            return json.dumps(self._mcp_fallback(normalized_name, query), ensure_ascii=False)

        payload: Dict[str, Any] = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": True,
            "max_results": 10,
        }
        try:
            response = httpx.post("https://api.tavily.com/search", json=payload, timeout=24)
            response.raise_for_status()
            data = response.json()
            results: List[Dict[str, Any]] = []
            for item in data.get("results", []):
                url = item.get("url", "")
                trust_level, confidence = source_confidence(url)
                results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "content": item.get("content", ""),
                    "raw_content": item.get("raw_content", ""),
                    "score": item.get("score", 0),
                    "trust_level": trust_level,
                    "confidence": confidence,
                })
            bocha_result = search_with_bocha(query=query, max_results=5, freshness="oneYear", summary=True)
            if bocha_result.get("success"):
                results.extend(bocha_result.get("results", []))
            mcp_result = search_with_mcp_providers(query=query, max_results=4)
            if mcp_result.get("success"):
                results.extend(mcp_result.get("results", []))
            return json.dumps({
                "success": True,
                "enterprise_name": normalized_name,
                "original_input": enterprise_name,
                "answer": data.get("answer", ""),
                "results": results,
                "bocha_log_id": bocha_result.get("log_id") if 'bocha_result' in locals() else None,
                "mcp_attempts": mcp_result.get("attempts", []),
            }, ensure_ascii=False)
        except Exception as e:
            mcp_fallback = self._mcp_fallback(normalized_name, query)
            if mcp_fallback.get("success"):
                return json.dumps(mcp_fallback, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "enterprise_name": normalized_name,
                "error": str(e),
                "results": [],
            }, ensure_ascii=False)


tavily_legal_search = TavilyLegalSearchTool()
