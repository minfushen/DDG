# ========================================
# 服务层 — 工商查询服务
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.agents.tools.yuandian_company_tool import build_business_profile

logger = logging.getLogger(__name__)


class BusinessService:
    """工商查询服务 — 封装天眼查/企查查等企业工商信息查询。"""

    async def query(self, enterprise_name: str) -> Dict[str, Any]:
        """查询企业工商信息。

        Args:
            enterprise_name: 企业全称或关键词

        Returns:
            标准化工商信息字典
        """
        logger.info("[BusinessService] enterprise=%s", enterprise_name)

        try:
            result = build_business_profile(enterprise_name)
        except Exception as exc:
            logger.warning("[BusinessService] 查询失败: %s", exc)
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

    async def query_basic(self, enterprise_name: str) -> Dict[str, Any]:
        """查询企业基础工商信息（简化版）。"""
        result = await self.query(enterprise_name)
        if not result.get("success"):
            return result

        data = result.get("data", {})
        # 提取关键字段
        basic = data.get("basic_info", {})
        return {
            "success": True,
            "enterprise_name": enterprise_name,
            "data": {
                "name": basic.get("name") or enterprise_name,
                "credit_code": basic.get("credit_code"),
                "legal_person": basic.get("legal_person"),
                "registered_capital": basic.get("registered_capital"),
                "establishment_date": basic.get("establishment_date"),
                "business_scope": basic.get("business_scope"),
                "enterprise_type": basic.get("enterprise_type"),
                "address": basic.get("address"),
                "status": basic.get("status"),
            },
            "error": None,
        }


# 单例
_business_service: Optional[BusinessService] = None


def get_business_service() -> BusinessService:
    """获取工商服务单例。"""
    global _business_service
    if _business_service is None:
        _business_service = BusinessService()
    return _business_service
