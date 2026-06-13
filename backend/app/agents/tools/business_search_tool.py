# ========================================
# 工商公开信息搜索工具
# 使用 Tavily 获取企业工商信息候选来源
# ========================================

from typing import Type, Dict, Any, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx
import json

from app.config import settings
from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.mcp_search_tool import search_with_mcp_providers
from app.agents.tools.bocha_search_tool import search_with_bocha


class SearchBusinessInfoInput(BaseModel):
    """搜索工商信息输入"""
    enterprise_name: str = Field(description="企业名称")


HIGH_TRUST_DOMAINS = ["gsxt.gov.cn", "cninfo.com.cn", "static.cninfo.com.cn"]
MEDIUM_TRUST_DOMAINS = ["aiqicha.baidu.com", "qcc.com", "tianyancha.com", "qixin.com"]


def source_confidence(url: str) -> tuple[str, float]:
    if any(domain in url for domain in HIGH_TRUST_DOMAINS):
        return "high", 0.9
    if any(domain in url for domain in MEDIUM_TRUST_DOMAINS):
        return "medium", 0.75
    return "low", 0.55


class TavilyBusinessSearchTool(BaseTool):
    """Tavily 工商信息搜索工具"""
    name: str = "tavily_business_search"
    description: str = "通过 Tavily 搜索企业工商信息、上市公司公告和企业信息平台公开摘要。"
    args_schema: Type[BaseModel] = SearchBusinessInfoInput

    def _mcp_fallback(self, enterprise_name: str, query: str) -> Dict[str, Any]:
        bocha_result = search_with_bocha(query=query, max_results=8, summary=True)
        if bocha_result.get("success"):
            return {
                "success": True,
                "enterprise_name": enterprise_name,
                "answer": "",
                "results": bocha_result.get("results", []),
                "bocha_log_id": bocha_result.get("log_id"),
                "generated_from": "博查公开搜索兜底",
            }
        mcp_result = search_with_mcp_providers(query=query, max_results=8)
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
        query = f"{normalized_name} 工商信息 统一社会信用代码 法定代表人 注册资本 成立日期 经营范围"
        if not settings.TAVILY_API_KEY:
            return json.dumps(self._mcp_fallback(normalized_name, query), ensure_ascii=False)

        payload: Dict[str, Any] = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": True,
            "max_results": 8,
        }
        try:
            response = httpx.post("https://api.tavily.com/search", json=payload, timeout=20)
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
            bocha_result = search_with_bocha(query=query, max_results=4, summary=True)
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
                "error": str(e),
                "enterprise_name": enterprise_name,
                "results": [],
            }, ensure_ascii=False)


tavily_business_search = TavilyBusinessSearchTool()
