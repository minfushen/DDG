# ========================================
# 服务层 — 行业分析服务
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.agents.sub_agents.industry_agent import run_industry_agent

logger = logging.getLogger(__name__)


class IndustryService:
    """行业分析服务 — 封装行业分析子Agent。"""

    async def analyze(self, industry_name: str) -> Dict[str, Any]:
        """执行行业分析。

        Args:
            industry_name: 行业名称

        Returns:
            行业分析结果字典
        """
        logger.info("[IndustryService] industry=%s", industry_name)

        try:
            result = run_industry_agent(industry_name)
        except Exception as exc:
            logger.warning("[IndustryService] 分析失败: %s", exc)
            return {
                "success": False,
                "industry_name": industry_name,
                "data": {},
                "error": str(exc),
            }

        return {
            "success": True,
            "industry_name": industry_name,
            "data": result,
            "error": None,
        }

    async def analyze_summary(self, industry_name: str) -> Dict[str, Any]:
        """行业分析摘要（简化版）。"""
        result = await self.analyze(industry_name)
        if not result.get("success"):
            return result

        data = result.get("data", {})
        return {
            "success": True,
            "industry_name": industry_name,
            "data": {
                "market_size": data.get("market_size"),
                "growth_rate": data.get("growth_rate"),
                "competitive_landscape": data.get("competitive_landscape", ""),
                "key_trends": data.get("key_trends", []),
                "risk_factors": data.get("risk_factors", []),
            },
            "error": None,
        }


# 单例
_industry_service: Optional[IndustryService] = None


def get_industry_service() -> IndustryService:
    """获取行业服务单例。"""
    global _industry_service
    if _industry_service is None:
        _industry_service = IndustryService()
    return _industry_service
