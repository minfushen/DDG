"""Whitelist registry for CodeAct tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.codeact.financial_tools import calculate_financial_ratios, validate_financial_statements
from app.codeact.t1_package_tools import validate_t1_data_package

from .schemas import CodeActToolSpec


def _evaluate_report_quality(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.agents.research_engine.report_quality_evaluator import evaluate_report_quality

    report = payload.get("report")
    if not isinstance(report, dict):
        raise ValueError("payload.report must be a report JSON object")
    sample = payload.get("sample")
    if sample is not None and not isinstance(sample, dict):
        raise ValueError("payload.sample must be an object when provided")
    return evaluate_report_quality(report, sample=sample)


_TOOLS: Dict[str, CodeActToolSpec] = {
    "evaluate_report_quality": CodeActToolSpec(
        name="evaluate_report_quality",
        display_name="报告质量评测",
        description="Evaluate a due-diligence report against the deterministic quality rubric.",
        handler=_evaluate_report_quality,
        timeout_seconds=30,
        source_type="codeact_evaluation",
    ),
    "calculate_financial_ratios": CodeActToolSpec(
        name="calculate_financial_ratios",
        display_name="财务指标计算",
        description="Calculate deterministic financial ratios from income statement, balance sheet, and cash flow records.",
        handler=calculate_financial_ratios,
        timeout_seconds=30,
        source_type="codeact_financial_metric",
    ),
    "validate_financial_statements": CodeActToolSpec(
        name="validate_financial_statements",
        display_name="三大表勾稽校验",
        description="Validate core reconciliation rules across financial statements.",
        handler=validate_financial_statements,
        timeout_seconds=30,
        source_type="codeact_financial_validation",
    ),
    "validate_t1_data_package": CodeActToolSpec(
        name="validate_t1_data_package",
        display_name="前置机数据包校验",
        description="Validate private-deployment T+1 front-machine data package schema and auditability.",
        handler=validate_t1_data_package,
        timeout_seconds=30,
        source_type="codeact_t1_package_validation",
    ),
}


def get_codeact_tool(name: str) -> Optional[CodeActToolSpec]:
    return _TOOLS.get(str(name or "").strip())


def list_registered_codeact_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "display_name": spec.display_name,
            "description": spec.description,
            "timeout_seconds": spec.timeout_seconds,
            "source_type": spec.source_type,
        }
        for spec in _TOOLS.values()
    ]
