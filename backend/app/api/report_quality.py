"""Report quality evaluation API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.codeact import run_codeact_tool


router = APIRouter()


class ReportQualityEvaluateRequest(BaseModel):
    report: Dict[str, Any] = Field(..., description="Generated due-diligence report JSON")
    sample: Optional[Dict[str, Any]] = Field(default=None, description="Optional regression sample metadata")


@router.post("/report-quality/evaluate")
async def evaluate_report(request: ReportQualityEvaluateRequest) -> Dict[str, Any]:
    if not isinstance(request.report, dict) or not request.report:
        raise HTTPException(status_code=400, detail="缺少有效的报告 JSON")
    try:
        codeact_result = run_codeact_tool("evaluate_report_quality", {"report": request.report, "sample": request.sample})
        if not codeact_result.get("success"):
            raise ValueError(codeact_result.get("error") or "CodeAct report quality evaluation failed")
        result = dict(codeact_result.get("result") or {})
        result["codeact_meta"] = {
            "tool_name": codeact_result.get("tool_name"),
            "display_name": codeact_result.get("display_name"),
            "elapsed_ms": codeact_result.get("elapsed_ms"),
            "source_type": codeact_result.get("source_type"),
        }
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"报告质量评测失败：{type(exc).__name__}: {exc}") from exc
