"""Automatic report quality gate backed by CodeAct."""

from __future__ import annotations

from typing import Any, Dict, List

from app.codeact import run_codeact_tool

from .state import timeline_event


def evaluate_report_with_codeact(report: Dict[str, Any]) -> Dict[str, Any]:
    """Run deterministic quality evaluation and return a report patch."""
    if not isinstance(report, dict) or not report:
        return {
            "quality_evaluation": None,
            "quality_score": None,
            "quality_passed": False,
            "quality_issues": [{
                "severity": "P0",
                "dimension": "report_payload",
                "message": "报告为空，无法执行质量评测。",
                "recommendation": "检查报告合成层是否成功返回 report JSON。",
            }],
            "quality_gate_meta": {"success": False, "error": "empty report"},
        }

    result = run_codeact_tool("evaluate_report_quality", {"report": report})
    if not result.get("success"):
        return {
            "quality_evaluation": None,
            "quality_score": None,
            "quality_passed": False,
            "quality_issues": [{
                "severity": "P1",
                "dimension": "quality_gate",
                "message": f"报告质量评测执行失败：{result.get('error') or '未知错误'}",
                "recommendation": "检查 CodeAct 质量评测工具配置和报告 JSON 结构。",
            }],
            "quality_gate_meta": _meta(result),
        }

    evaluation = result.get("result") or {}
    return {
        "quality_evaluation": evaluation,
        "quality_score": evaluation.get("overall_score"),
        "quality_grade": evaluation.get("grade"),
        "quality_passed": bool(evaluation.get("passed")),
        "quality_issues": evaluation.get("issues") or [],
        "quality_recommendations": evaluation.get("recommendations") or [],
        "quality_gate_meta": _meta(result),
    }


def build_quality_timeline_event(quality_patch: Dict[str, Any]) -> Dict[str, Any]:
    issues = quality_patch.get("quality_issues") or []
    p0_count = len([item for item in issues if item.get("severity") == "P0"])
    p1_count = len([item for item in issues if item.get("severity") == "P1"])
    score = quality_patch.get("quality_score")
    passed = bool(quality_patch.get("quality_passed"))
    if passed:
        status = "completed"
        content = "报告自动质检通过"
        detail = f"质量评分{score}分，结构、证据引用和语言质量达到当前阈值。"
    else:
        status = "completed"
        content = "报告自动质检需复核"
        detail = f"质量评分{score if score is not None else '不可用'}分，发现P0 {p0_count}项、P1 {p1_count}项。"
    event = timeline_event("报告质检", content, detail, status, "analysis")
    event["findings"] = _top_issue_texts(issues)
    event["quality_score"] = score
    event["quality_passed"] = passed
    event["p0_count"] = p0_count
    event["p1_count"] = p1_count
    return event


def apply_report_quality_gate(report: Dict[str, Any]) -> Dict[str, Any]:
    """Attach quality evaluation fields to a report and return the patch."""
    patch = evaluate_report_with_codeact(report)
    report.update(patch)
    return patch


def _meta(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool_name": result.get("tool_name"),
        "display_name": result.get("display_name"),
        "elapsed_ms": result.get("elapsed_ms"),
        "source_type": result.get("source_type"),
        "success": result.get("success"),
        "error": result.get("error"),
    }


def _top_issue_texts(issues: List[Dict[str, Any]]) -> List[str]:
    rows = []
    for item in issues[:5]:
        severity = item.get("severity") or "P?"
        message = item.get("message") or item.get("dimension") or "质量问题待复核"
        rows.append(f"{severity}：{message}")
    return rows or ["未发现阻断性质量问题"]
