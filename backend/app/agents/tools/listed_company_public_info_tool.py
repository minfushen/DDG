"""Listed company public-information package tool.

Collects lightweight, auditable public context for A-share listed companies:
business review, main business composition, announcements, pledge/guarantee
clues, industry position and research-report summaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type
import json
import re

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx

from app.config import settings
from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.mcp_search_tool import search_with_mcp_providers
from app.agents.tools.bocha_search_tool import search_with_bocha


class FetchListedCompanyPublicInfoInput(BaseModel):
    enterprise_name: str = Field(description="企业名称")
    stock_code: str = Field(default="", description="股票代码")
    stock_exchange: str = Field(default="", description="上市交易所")


EASTMONEY_F10_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://emweb.securities.eastmoney.com/",
}


def _clean_text(text: Any, limit: int = 900) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value[:limit]


def _format_amount(value: Any) -> str:
    if value is None:
        return "数据不可用"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 100000000:
        return f"{number / 100000000:.2f}亿元"
    if abs(number) >= 10000:
        return f"{number / 10000:.2f}万元"
    return f"{number:.2f}元"


def _format_percent(value: Any) -> str:
    if value is None:
        return "数据不可用"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1:
        number *= 100
    return f"{number:.2f}%"


def _fetch_f10(secu_code: str, report_name: str, page_size: int = 10) -> List[Dict[str, Any]]:
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECUCODE="{secu_code}")',
        "pageNumber": "1",
        "pageSize": str(page_size),
        "source": "HSF10",
        "client": "PC",
    }
    response = httpx.get(EASTMONEY_F10_URL, params=params, headers=HEADERS, timeout=12)
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result") or {}
    return result.get("data", []) if isinstance(result, dict) else []


def _latest_annual_business_review(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    annual = [row for row in rows if "年报" in str(row.get("REPORT_NAME", ""))]
    row = (annual or rows or [{}])[0]
    return {
        "report_name": row.get("REPORT_NAME"),
        "report_date": str(row.get("REPORT_DATE") or "")[:10],
        "business_review": _clean_text(row.get("BUSINESS_REVIEW"), 1800),
    }


def _main_business(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    annual = [row for row in rows if "年报" in str(row.get("REPORT_NAME", ""))]
    latest_report = next((row.get("REPORT_NAME") for row in annual), None)
    selected = [row for row in annual if row.get("REPORT_NAME") == latest_report] if latest_report else annual[:8]
    business = []
    for row in selected[:10]:
        business.append({
            "report_name": row.get("REPORT_NAME"),
            "item_name": _clean_text(row.get("ITEM_NAME"), 80),
            "income": _format_amount(row.get("MAIN_BUSINESS_INCOME")),
            "income_ratio": _format_percent(row.get("MBI_RATIO")),
            "gross_margin": _format_percent(row.get("GROSS_RPOFIT_RATIO")),
            "rank": row.get("RANK") or row.get("RANKNEW"),
        })
    return [item for item in business if item.get("item_name")]


def _basic_info(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "org_name": row.get("ORG_NAME"),
        "security_name": row.get("SECURITY_NAME_ABBR"),
        "industry": row.get("EM2016"),
        "concepts": row.get("BLGAINIAN"),
        "region": row.get("REGIONBK"),
        "main_business": row.get("MAIN_BUSINESS"),
        "profile": _clean_text(row.get("ORG_PROFIE"), 1600),
        "website": row.get("ORG_WEB"),
        "employees": row.get("TOTAL_NUM"),
    }


def _tavily_search(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    bocha_result = search_with_bocha(query=query, max_results=max_results, summary=True)
    if bocha_result.get("success"):
        results.extend(bocha_result.get("results", []))
        if len(results) >= max_results:
            return results[:max_results]
    if not settings.TAVILY_API_KEY:
        mcp_result = search_with_mcp_providers(query=query, max_results=max(1, max_results - len(results)))
        if mcp_result.get("success"):
            results.extend(mcp_result.get("results", []))
        return results[:max_results]
    else:
        payload = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "max_results": max_results,
        }
        try:
            response = httpx.post("https://api.tavily.com/search", json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data.get("answer"):
                results.append({"title": "Tavily 搜索摘要", "url": None, "content": data.get("answer", ""), "source": "Tavily"})
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content", ""),
                    "source": item.get("url") or "Tavily 搜索结果",
                })
        except Exception:
            results = []
    mcp_result = search_with_mcp_providers(query=query, max_results=max(1, max_results - len(results)))
    if mcp_result.get("success"):
        results.extend(mcp_result.get("results", []))
    return results[:max_results]


def _search_packages(company: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
    name = company.get("company_name") or company.get("security_name") or ""
    short = company.get("security_name") or name
    queries = {
        "litigation_announcements": f"{name} {short} 重大诉讼 仲裁 诉讼公告 巨潮资讯 东方财富",
        "guarantee_pledge_announcements": f"{name} {short} 对外担保 股权质押 担保公告 巨潮资讯 东方财富",
        "industry_position": f"{name} {short} 行业地位 市占率 排名 竞争格局 年报",
        "research_summaries": f"{name} {short} 研报 摘要 行业 竞争优势 风险",
    }
    return {key: _tavily_search(query) for key, query in queries.items()}


def fetch_listed_company_public_info_data(enterprise_name: str, stock_code: str = "", stock_exchange: str = "") -> Dict[str, Any]:
    company = resolve_listed_company(enterprise_name, stock_code, stock_exchange)
    if not company:
        return {"success": False, "error": "未识别到上市公司证券代码", "enterprise_name": enterprise_name}

    try:
        basic_rows = _fetch_f10(company["secu_code"], "RPT_F10_ORG_BASICINFO", 3)
        mainop_rows = _fetch_f10(company["secu_code"], "RPT_F10_FN_MAINOP", 60)
        business_rows = _fetch_f10(company["secu_code"], "RPT_F10_OP_BUSINESSANALYSIS", 6)
        searches = _search_packages(company)
        basic = _basic_info(basic_rows[0] if basic_rows else {})
        business_review = _latest_annual_business_review(business_rows)
        main_business = _main_business(mainop_rows)
        evidence = [
            {"label": "上市公司基础资料", "value": basic.get("main_business") or basic.get("industry"), "source": "东方财富F10"},
            {"label": "主营构成", "value": f"{len(main_business)}项", "source": "东方财富F10主营构成"},
            {"label": "年报经营讨论", "value": business_review.get("report_name") or "已获取", "source": "东方财富F10经营分析"},
        ]
        for key, items in searches.items():
            if items:
                evidence.append({"label": key, "value": f"{len(items)}条公开线索", "source": "Tavily定向搜索"})
        return {
            "success": True,
            "enterprise_name": enterprise_name,
            "security_name": company.get("security_name"),
            "company_name": company.get("company_name"),
            "stock_code": company.get("stock_code"),
            "stock_exchange": company.get("stock_exchange"),
            "secu_code": company.get("secu_code"),
            "data_source": "东方财富F10 + Tavily公开搜索",
            "basic_info": basic,
            "main_business_composition": main_business,
            "annual_business_review": business_review,
            "search_clues": searches,
            "evidence": evidence,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"获取上市公司公开资料包失败: {type(exc).__name__}: {exc}",
            "enterprise_name": enterprise_name,
            "stock_code": company.get("stock_code"),
            "stock_exchange": company.get("stock_exchange"),
        }


class FetchListedCompanyPublicInfoTool(BaseTool):
    name: str = "fetch_listed_company_public_info"
    description: str = "获取上市公司公开资料包，包括年报经营讨论、主营构成、诉讼公告、担保质押、行业地位和研报摘要。"
    args_schema: Type[BaseModel] = FetchListedCompanyPublicInfoInput

    def _run(self, enterprise_name: str, stock_code: str = "", stock_exchange: str = "") -> str:
        return json.dumps(fetch_listed_company_public_info_data(enterprise_name, stock_code, stock_exchange), ensure_ascii=False)


fetch_listed_company_public_info = FetchListedCompanyPublicInfoTool()
