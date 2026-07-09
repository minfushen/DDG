# backend/app/api/tools.py
"""单步工具调用 API。

把项目内部常用的检索/查询工具暴露为无状态的 HTTP 端点，供 Dify 等外部编排平台
通过 Custom Tool 或 HTTP 节点直接调用。每个端点只做一次工具调用，不触发
DeepResearch 引擎，也不维护任务状态。
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.tools.bocha_search_tool import search_with_bocha
from app.agents.tools.yuandian_company_tool import build_business_profile
from app.agents.tools.yuandian_legal_tool import build_legal_risk_profile

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """公开搜索请求"""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=500)
    max_results: int = Field(default=8, description="返回结果数量", ge=1, le=50)
    freshness: str = Field(default="noLimit", description="时间范围：noLimit / oneDay / oneWeek / oneMonth / oneYear")
    include: str = Field(default="", description="限定域名，多个用 | 分隔")
    exclude: str = Field(default="", description="排除域名，多个用 | 分隔")


class BusinessRequest(BaseModel):
    """企业工商信息查询请求"""
    enterprise_name: str = Field(..., description="企业全称或关键词", min_length=2, max_length=200)


class LegalRequest(BaseModel):
    """企业司法风险查询请求"""
    enterprise_name: str = Field(..., description="企业全称或关键词", min_length=2, max_length=200)
    top_k: int = Field(default=10, description="返回案例数量", ge=1, le=50)


class ToolResponse(BaseModel):
    """统一工具响应"""
    success: bool
    provider: str
    query: Optional[str] = None
    enterprise_name: Optional[str] = None
    data: Dict[str, Any]
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tools/search", response_model=ToolResponse, tags=["tools"])
async def tool_search(request: SearchRequest):
    """公开网页搜索（Bocha）。

    示例请求：
        {"query": "华为技术有限公司 年报", "max_results": 5}
    """
    result = await asyncio.to_thread(
        search_with_bocha,
        query=request.query,
        max_results=request.max_results,
        freshness=request.freshness,
        summary=True,
        include=request.include,
        exclude=request.exclude,
    )
    if not result.get("success") and not result.get("results"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "搜索未返回有效结果",
        )
    return ToolResponse(
        success=result.get("success", True),
        provider=result.get("provider", "bocha"),
        query=result.get("query"),
        data={
            "results": result.get("results", []),
            "total_estimated_matches": result.get("total_estimated_matches"),
            "log_id": result.get("log_id"),
        },
        error=result.get("error"),
    )


@router.post("/tools/business", response_model=ToolResponse, tags=["tools"])
async def tool_business(request: BusinessRequest):
    """企业工商基础信息 + 涉诉统计（元典）。

    示例请求：
        {"enterprise_name": "华为技术有限公司"}
    """
    result = await asyncio.to_thread(build_business_profile, request.enterprise_name)
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "企业信息查询失败",
        )
    return ToolResponse(
        success=True,
        provider="yuandian_company",
        enterprise_name=result.get("enterprise_name"),
        data={
            "enterprise_id": result.get("enterprise_id"),
            "tyshxydm": result.get("tyshxydm"),
            "basic_info": result.get("basic_info", {}),
            "risk_summary": result.get("risk_summary", {}),
        },
    )


@router.post("/tools/legal", response_model=ToolResponse, tags=["tools"])
async def tool_legal(request: LegalRequest):
    """企业司法风险画像（元典案例库）。

    示例请求：
        {"enterprise_name": "华为技术有限公司", "top_k": 10}
    """
    result = await asyncio.to_thread(
        build_legal_risk_profile,
        enterprise_name=request.enterprise_name,
        top_k=request.top_k,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "司法风险查询失败",
        )
    return ToolResponse(
        success=True,
        provider="yuandian_case",
        enterprise_name=result.get("enterprise_name"),
        data={
            "total": result.get("total", 0),
            "case_summaries": result.get("case_summaries", []),
            "summary": result.get("summary", {}),
        },
    )
