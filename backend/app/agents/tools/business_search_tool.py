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

    def _run(self, enterprise_name: str) -> str:
        if not settings.TAVILY_API_KEY:
            return json.dumps({
                "success": False,
                "error": "未配置 TAVILY_API_KEY",
                "enterprise_name": enterprise_name,
                "results": [],
            }, ensure_ascii=False)

        listed_company = resolve_listed_company(enterprise_name)
        normalized_name = listed_company.get("company_name") if listed_company else enterprise_name
        query = f"{normalized_name} 工商信息 统一社会信用代码 法定代表人 注册资本 成立日期 经营范围"
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
            return json.dumps({
                "success": True,
                "enterprise_name": normalized_name,
                "original_input": enterprise_name,
                "answer": data.get("answer", ""),
                "results": results,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "enterprise_name": enterprise_name,
                "results": [],
            }, ensure_ascii=False)


tavily_business_search = TavilyBusinessSearchTool()
