# ========================================
# 服务层 — 搜索工具服务
# 解耦工具调用，供 Dify 适配层和核心引擎共同使用
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agents.tools.bocha_search_tool import search_with_bocha

logger = logging.getLogger(__name__)


class SearchService:
    """搜索工具服务 — 可被 Dify 直接调用，也可被核心引擎内部调用。

    封装 Bocha 搜索，提供缓存感知和标准化输出。
    """

    async def search(
        self,
        query: str,
        max_results: int = 8,
        freshness: str = "noLimit",
        include: str = "",
        exclude: str = "",
        summary: bool = True,
    ) -> Dict[str, Any]:
        """执行网页搜索。

        Args:
            query: 搜索关键词
            max_results: 返回结果数量（1-50）
            freshness: 时间范围
            include: 限定域名
            exclude: 排除域名
            summary: 是否生成摘要

        Returns:
            标准化搜索结果字典
        """
        logger.info("[SearchService] query=%s max_results=%s", query, max_results)

        result = search_with_bocha(
            query=query,
            max_results=max_results,
            freshness=freshness,
            summary=summary,
            include=include,
            exclude=exclude,
        )

        if not result.get("success") and not result.get("results"):
            logger.warning("[SearchService] 搜索未返回有效结果: %s", result.get("error"))
            return {
                "success": False,
                "provider": "bocha",
                "query": query,
                "results": [],
                "total_estimated_matches": 0,
                "error": result.get("error") or "搜索未返回有效结果",
            }

        return {
            "success": result.get("success", True),
            "provider": result.get("provider", "bocha"),
            "query": result.get("query"),
            "results": result.get("results", []),
            "total_estimated_matches": result.get("total_estimated_matches"),
            "log_id": result.get("log_id"),
            "error": result.get("error"),
        }

    async def search_enterprise(self, enterprise_name: str, max_results: int = 8) -> Dict[str, Any]:
        """企业专用搜索 — 自动优化查询词。"""
        query = f"{enterprise_name} 企业信息 工商 财务 年报"
        return await self.search(query=query, max_results=max_results)

    async def search_legal(self, enterprise_name: str, max_results: int = 8) -> Dict[str, Any]:
        """法律风险专用搜索。"""
        query = f"{enterprise_name} 诉讼 仲裁 法律风险 判决"
        return await self.search(query=query, max_results=max_results)

    async def search_industry(self, industry_name: str, max_results: int = 8) -> Dict[str, Any]:
        """行业分析专用搜索。"""
        query = f"{industry_name} 行业分析 市场规模 竞争格局 发展趋势"
        return await self.search(query=query, max_results=max_results)


# 单例
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """获取搜索服务单例。"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
