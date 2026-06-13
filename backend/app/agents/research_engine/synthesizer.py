"""Synthesize a DeepResearch-style due-diligence report."""

from __future__ import annotations

from typing import Any, Dict, List

from .state import ResearchState


def _source_summary(evidence: List[Dict[str, Any]]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for item in evidence:
        key = item.get("source_type") or "unknown"
        summary[key] = summary.get(key, 0) + 1
    return summary


def _category_items(items: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    return [item for item in items if item.get("category") == category or item.get("domain") == category or item.get("task_id", "").find(category) >= 0]


def _score_dimension(total: int, high_gaps: int, no_evidence: bool = False) -> int:
    if no_evidence:
        return 55
    score = 82 - high_gaps * 12 - max(total - high_gaps, 0) * 4
    return max(45, min(88, score))


def _risk_status(score: int) -> str:
    if score >= 78:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


def _dimension(name: str, score: int, weight: float, details: List[str]) -> Dict[str, Any]:
    return {"name": name, "score": score, "max_score": 100, "weight": weight, "status": _risk_status(score), "details": details[:4]}


def _summary_for_category(claims: List[Dict[str, Any]], tasks: List[Dict[str, Any]], category: str, fallback: str) -> List[str]:
    task_ids = {task.get("id") for task in tasks if task.get("category") == category}
    rows = [claim.get("text") for claim in claims if claim.get("task_id") in task_ids and claim.get("text")]
    return rows[:4] or [fallback]


def _financial_report_summary(evidence: List[Dict[str, Any]]) -> List[str]:
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        if report:
            return (report.get("narrative_summary") or [])[:6]
    return []


def _industry_report_summary(evidence: List[Dict[str, Any]]) -> List[str]:
    for item in evidence:
        report = ((item.get("metadata") or {}).get("industry_analysis_report") or {})
        if report:
            return (report.get("industry_diagnostic_summary") or report.get("risk_summary") or [])[:6]
    return []


def _financial_required_documents(evidence: List[Dict[str, Any]]) -> List[str]:
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        diagnostics = report.get("narrative_diagnostics") or {}
        docs: List[str] = []
        for row in diagnostics.get("diagnostics") or []:
            docs.extend(str(value) for value in row.get("missing_items") or [] if value)
        if docs:
            return list(dict.fromkeys(docs))[:8]
    return ["近三年审计报告或三大表", "银行流水", "纳税申报", "主要销售合同"]


def synthesize_research_report(state: ResearchState) -> Dict[str, Any]:
    tasks = state.get("tasks", [])
    claims = state.get("claims", [])
    gaps = state.get("gaps", [])
    evidence = state.get("evidence", [])
    high_gaps = [gap for gap in gaps if gap.get("severity") == "high"]
    enterprise_name = state.get("enterprise_name")
    financial_gaps = [gap for gap in gaps if gap.get("task_id") and "financial" in gap.get("task_id", "")]
    legal_gaps = [gap for gap in gaps if gap.get("task_id") and "legal" in gap.get("task_id", "")]
    business_gaps = [gap for gap in gaps if gap.get("task_id") and ("business" in gap.get("task_id", "") or "identity" in gap.get("task_id", ""))]
    industry_gaps = [gap for gap in gaps if gap.get("task_id") and "industry" in gap.get("task_id", "")]

    business_score = _score_dimension(len(business_gaps), len([gap for gap in business_gaps if gap.get("severity") == "high"]), not _category_items(evidence, "business"))
    financial_score = _score_dimension(len(financial_gaps), len([gap for gap in financial_gaps if gap.get("severity") == "high"]), not _category_items(evidence, "financial"))
    legal_score = _score_dimension(len(legal_gaps), len([gap for gap in legal_gaps if gap.get("severity") == "high"]), not _category_items(evidence, "legal"))
    industry_score = _score_dimension(len(industry_gaps), len([gap for gap in industry_gaps if gap.get("severity") == "high"]), not _category_items(evidence, "industry"))
    weighted_score = round(business_score * 0.2 + financial_score * 0.35 + legal_score * 0.25 + industry_score * 0.2)
    risk_rating = _risk_status(weighted_score)
    suggestion = "有条件准入" if weighted_score >= 72 else "审慎准入" if weighted_score >= 60 else "暂缓准入"

    summary = [
        f"{enterprise_name}本次智能尽调形成综合评分{weighted_score}分，建议为“{suggestion}”。",
        f"系统已归集{len(evidence)}项证据并形成{len(claims)}条可追踪结论，其中仍有{len(high_gaps)}项高优先级证据缺口需要客户经理复核。",
        "当前报告适合作为公开资料预尽调和客户经理初审底稿，正式授信前仍需补充权威工商、司法、财报及客户原始材料。",
    ]
    financial_summary = _financial_report_summary(evidence) or _summary_for_category(claims, tasks, "financial", "财务专项尚未形成充分证据。")
    industry_summary = _industry_report_summary(evidence) or _summary_for_category(claims, tasks, "industry", "行业分析已形成初步判断。")

    risk_dimensions = [
        _dimension("工商与治理", business_score, 0.20, _summary_for_category(claims, tasks, "business", "主体识别已完成，仍需权威工商源复核。")),
        _dimension("财务健康度", financial_score, 0.35, financial_summary),
        _dimension("司法合规", legal_score, 0.25, _summary_for_category(claims, tasks, "legal", "司法证据不足，需人工查询权威司法和行政处罚来源。")),
        _dimension("行业与经营环境", industry_score, 0.20, industry_summary),
    ]

    report_chapters = [
        {
            "id": "overview",
            "title": "报告导言与核心概要",
            "subtitle": "智能尽调综合结论",
            "summary": summary,
            "highlights": [f"证据{len(evidence)}项", f"结论{len(claims)}条", f"高优先缺口{len(high_gaps)}项"],
        },
        {"id": "business", "title": "企业基本情况与治理结构", "summary": _summary_for_category(claims, tasks, "business", "工商主体信息尚需权威源复核。"), "risks": [gap.get("description") for gap in business_gaps]},
        {"id": "financial", "title": "财务状况与偿债能力", "summary": financial_summary, "risks": [gap.get("description") for gap in financial_gaps], "required_documents": _financial_required_documents(evidence)},
        {"id": "legal", "title": "司法与合规风险", "summary": _summary_for_category(claims, tasks, "legal", "司法线索尚需权威渠道复核。"), "risks": [gap.get("description") for gap in legal_gaps]},
        {"id": "industry", "title": "行业环境与经营分析", "summary": industry_summary, "risks": [gap.get("description") for gap in industry_gaps]},
        {"id": "credit", "title": "调查结论与信贷建议", "summary": [f"准入建议：{suggestion}", "建议控制首笔额度，额度释放与真实订单、回款、纳税流水和项目进度挂钩。", "对高优先级证据缺口设置为授信前置条件。"]},
        {"id": "evidence", "title": "证据链与过程附录", "summary": ["研究计划、Claim-Evidence、证据缺口和数据来源分布见本章节。"]},
    ]

    return {
        "report_type": "deepresearch_due_diligence",
        "enterprise_name": enterprise_name,
        "objective": state.get("objective"),
        "risk_rating": risk_rating,
        "risk_score": weighted_score,
        "recommendation": f"建议{suggestion}。正式授信前需补齐高优先级证据缺口，并以权威工商、司法、财报和客户原始材料复核。",
        "executive_summary": summary,
        "risk_dimensions": risk_dimensions,
        "credit_decision": {
            "suggestion": suggestion,
            "risk_score": weighted_score,
            "credit_limit_advice": "建议先控制首笔授信额度，待财务真实性、司法风险和回款闭环核实后再逐步释放额度。",
            "term_advice": "建议短期限、分阶段提款，并设置按月/季复核机制。",
            "collateral_advice": "优先落实实际控制人连带责任、核心资产抵质押、应收账款回款监管或项目回款闭环。",
            "post_loan_monitoring": ["持续跟踪工商变更、司法新增和行政处罚", "按月核验销售回款、流水和纳税申报匹配", "关注行业周期、价格波动和核心客户信用变化"],
        },
        "report_chapters": report_chapters,
        "research_plan": tasks,
        "research_rounds": state.get("research_rounds", []),
        "follow_up_tasks": state.get("follow_up_tasks", []),
        "claims": claims,
        "evidence": evidence,
        "gaps": gaps,
        "summary": summary,
        "source_reliability_summary": _source_summary(evidence),
        "data_boundary": "本报告由智能尽调 DeepResearch 引擎基于公开资料、知识库和本地工具生成。公开搜索结果仅作为线索，正式授信前需结合权威工商、司法、财报和客户原始材料人工复核。",
        "timeline": state.get("timeline", []),
    }
