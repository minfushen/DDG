# ========================================
# 服务层 — 法律查询服务
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.agents.tools.yuandian_legal_tool import build_legal_risk_profile
from app.config.rag_loader import get_legal_search_top_k

logger = logging.getLogger(__name__)


class LegalService:
    """法律查询服务 — 封装元典法律数据库查询。"""

    async def query(self, enterprise_name: str, top_k: int | None = None) -> Dict[str, Any]:
        """查询企业司法风险。

        Args:
            enterprise_name: 企业全称或关键词
            top_k: 返回案例数量；未指定时使用 rag.yaml 中的默认值

        Returns:
            标准化法律风险字典
        """
        top_k = top_k if top_k is not None else get_legal_search_top_k("default")
        logger.info("[LegalService] enterprise=%s top_k=%s", enterprise_name, top_k)

        try:
            result = build_legal_risk_profile(enterprise_name, top_k=top_k)
        except Exception as exc:
            logger.warning("[LegalService] 查询失败: %s", exc)
            return {
                "success": False,
                "enterprise_name": enterprise_name,
                "data": {},
                "error": str(exc),
            }

        return {
            "success": True,
            "enterprise_name": enterprise_name,
            "data": result,
            "error": None,
        }

    async def query_summary(self, enterprise_name: str) -> Dict[str, Any]:
        """查询法律风险摘要（简化版）。"""
        result = await self.query(enterprise_name, top_k=get_legal_search_top_k("summary"))
        if not result.get("success"):
            return result

        data = result.get("data", {})
        cases = data.get("cases", [])
        return {
            "success": True,
            "enterprise_name": enterprise_name,
            "data": {
                "case_count": len(cases),
                "risk_level": data.get("risk_level", "未知"),
                "risk_summary": data.get("risk_summary", ""),
                "key_cases": cases[:3] if cases else [],
            },
            "error": None,
        }


# 单例
_legal_service: Optional[LegalService] = None


def get_legal_service() -> LegalService:
    """获取法律服务单例。"""
    global _legal_service
    if _legal_service is None:
        _legal_service = LegalService()
    return _legal_service
