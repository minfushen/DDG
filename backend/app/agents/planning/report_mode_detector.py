"""Determine which due diligence report mode should be used."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from app.agents.tools.listed_company_tool import resolve_listed_company


ReportMode = Literal["public_pre_dd", "financial_enhanced_dd"]


def detect_report_mode(
    enterprise_name: str,
    parsed_financial_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return report mode and the reason used by the full due diligence runner."""
    listed_info = resolve_listed_company(enterprise_name)
    if listed_info:
        return {
            "report_mode": "financial_enhanced_dd",
            "company_type": "listed",
            "reason": "已识别为上市公司，可通过公开财报工具取数。",
            "listed_info": listed_info,
            "financial_data_status": "public_financial_report",
        }

    if parsed_financial_data:
        return {
            "report_mode": "financial_enhanced_dd",
            "company_type": "private",
            "reason": "已接收用户上传的近三年财务报表。",
            "listed_info": None,
            "financial_data_status": "uploaded_financial_statement",
        }

    return {
        "report_mode": "public_pre_dd",
        "company_type": "private_or_unknown",
        "reason": "未识别为上市公司且未上传财务报表，进入公开资料预尽调模式。",
        "listed_info": None,
        "financial_data_status": "public_clues_only",
    }

