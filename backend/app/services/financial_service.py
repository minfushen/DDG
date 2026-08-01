# ========================================
# 服务层 — 财务分析服务
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.agents.sub_agents.financial_agent import run_financial_agent, run_financial_agent_with_uploaded_data
from app.agents.sub_agents.public_financial_agent import run_public_financial_agent

logger = logging.getLogger(__name__)


class FinancialService:
    """财务分析服务 — 封装财务分析子Agent，支持公开数据和上传数据。"""

    async def analyze_public(self, enterprise_name: str, stock_code: Optional[str] = None) -> Dict[str, Any]:
        """基于公开数据进行财务分析。

        Args:
            enterprise_name: 企业名称
            stock_code: 股票代码（可选）

        Returns:
            财务分析结果字典
        """
        logger.info("[FinancialService] analyze_public enterprise=%s", enterprise_name)

        try:
            result = await run_public_financial_agent(enterprise_name, stock_code)
        except Exception as exc:
            logger.warning("[FinancialService] 公开财务分析失败: %s", exc)
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

    async def analyze_full(self, enterprise_name: str, financial_data: Dict[str, Any], industry_name: Optional[str] = None) -> Dict[str, Any]:
        """基于上传的财报数据进行完整财务分析。

        Args:
            enterprise_name: 企业名称
            financial_data: 财务数据（包含利润表、资产负债表、现金流量表）
            industry_name: 行业名称（可选，用于 P2.1 同业中位数对标）

        Returns:
            财务分析结果字典
        """
        logger.info("[FinancialService] analyze_full enterprise=%s industry=%s", enterprise_name, industry_name)

        try:
            result = await run_financial_agent_with_uploaded_data(
                enterprise_name, financial_data, industry_name=industry_name
            )
        except Exception as exc:
            logger.warning("[FinancialService] 完整财务分析失败: %s", exc)
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

    async def analyze_summary(self, enterprise_name: str, stock_code: Optional[str] = None) -> Dict[str, Any]:
        """财务分析摘要（简化版，供 Dify 快速展示）。"""
        result = await self.analyze_public(enterprise_name, stock_code)
        if not result.get("success"):
            return result

        data = result.get("data", {})
        report = data.get("report", {})
        dashboard = data.get("dashboard", {})

        return {
            "success": True,
            "enterprise_name": enterprise_name,
            "data": {
                "revenue": dashboard.get("revenue"),
                "net_profit": dashboard.get("net_profit"),
                "debt_ratio": dashboard.get("debt_ratio"),
                "gross_margin": dashboard.get("gross_margin"),
                "roa": dashboard.get("roa"),
                "roe": dashboard.get("roe"),
                "risk_level": data.get("risk_level", "未知"),
                "risk_score": data.get("risk_score", 0),
                "key_warnings": data.get("key_warnings", []),
            },
            "error": None,
        }


# 单例
_financial_service: Optional[FinancialService] = None


def get_financial_service() -> FinancialService:
    """获取财务服务单例。"""
    global _financial_service
    if _financial_service is None:
        _financial_service = FinancialService()
    return _financial_service
