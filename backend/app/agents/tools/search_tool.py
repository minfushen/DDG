"""Compatibility search tool wrappers for legacy sub-agents.

The project no longer keeps the old mock search implementation. These wrappers
preserve import compatibility without fabricating business, legal, or financial
facts. Current DeepResearch flows should prefer the dedicated providers in
``research_engine/tool_router.py``.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def _json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


class _UnavailableTool:
    name = "legacy_search_unavailable"

    def _run(self, enterprise_name: str, **_: Any) -> str:
        return _json({
            "success": False,
            "enterprise_name": enterprise_name,
            "error": "旧版搜索工具已移除，请使用当前公开资料检索、上市公司公开财报或上传材料链路。",
        })


class _EnterpriseInfoTool(_UnavailableTool):
    name = "legacy_enterprise_info_unavailable"

    def _run(self, enterprise_name: str, **_: Any) -> str:
        return _json({
            "success": False,
            "enterprise_name": enterprise_name,
            "统一社会信用代码": "",
            "注册资本": "",
            "成立日期": "",
            "经营范围": "",
            "股东信息": [],
            "对外投资": [],
            "error": "旧版工商搜索工具已移除，请使用公开资料检索或权威工商数据源。",
        })


class _LegalRecordsTool(_UnavailableTool):
    name = "legacy_legal_records_unavailable"

    def _run(self, enterprise_name: str, **_: Any) -> str:
        return _json({
            "success": False,
            "enterprise_name": enterprise_name,
            "裁判文书": [],
            "行政处罚": [],
            "失信被执行人": [],
            "error": "旧版司法搜索工具已移除，请使用公开资料检索或权威司法数据源。",
        })


class _FinancialDataTool(_UnavailableTool):
    name = "legacy_financial_data_unavailable"


search_enterprise_info = _EnterpriseInfoTool()
search_legal_records = _LegalRecordsTool()
search_financial_data = _FinancialDataTool()
