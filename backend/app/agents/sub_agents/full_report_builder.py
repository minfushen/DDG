"""完整尽调报告构建器。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


SUB_REPORT_KEYS = {
    "business": "business_analysis_report",
    "financial": "financial_analysis_report",
    "legal": "legal_analysis_report",
    "industry": "industry_analysis_report",
}

DIMENSION_META = {
    "business": {"name": "工商与治理", "weight": 0.20},
    "financial": {"name": "财务健康度", "weight": 0.35},
    "legal": {"name": "司法合规", "weight": 0.25},
    "industry": {"name": "行业与经营环境", "weight": 0.20},
}


def _rating_from_score(score: int) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


def _score_from_rating(rating: Optional[str], default: int = 75) -> int:
    return {"low": 85, "medium": 70, "high": 50}.get(rating or "", default)


def _safe_score(report: Optional[Dict[str, Any]], default: int) -> int:
    if not report:
        return default
    score = report.get("risk_score")
    if isinstance(score, (int, float)):
        return max(0, min(100, int(score)))
    return _score_from_rating(report.get("risk_rating"), default)


def _first_items(items: List[str], limit: int = 3) -> List[str]:
    return [item for item in items if item][:limit]


def _report_risks(report: Optional[Dict[str, Any]]) -> List[str]:
    if not report:
        return ["专项报告暂未形成，需补充数据后复核。"]
    risks = report.get("risk_summary") or []
    if risks:
        return _first_items([str(item) for item in risks])
    recommendation = report.get("recommendation")
    return [str(recommendation)] if recommendation else ["未发现明确重大异常，仍需结合底层证据复核。"]


def _dimension(key: str, report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    meta = DIMENSION_META[key]
    default_scores = {"business": 75, "financial": 70, "legal": 75, "industry": 72}
    score = _safe_score(report, default_scores[key])
    return {
        "key": key,
        "name": meta["name"],
        "score": score,
        "max_score": 100,
        "weight": meta["weight"],
        "status": _rating_from_score(score),
        "details": _report_risks(report),
    }


def _weighted_score(dimensions: List[Dict[str, Any]]) -> int:
    total_weight = sum(item.get("weight", 0) for item in dimensions) or 1
    score = sum(item.get("score", 0) * item.get("weight", 0) for item in dimensions) / total_weight
    return max(0, min(100, round(score)))


def _recommendation(rating: str, score: int) -> str:
    if rating == "low":
        return f"建议准入，可在落实常规担保、用途核验和贷后监测条件后推进授信。综合风险评分{score}分，整体风险可控。"
    if rating == "medium":
        return f"建议谨慎准入，需补充核实财务真实性、涉诉事项、核心客户回款及行业周期风险后再确定额度。综合风险评分{score}分。"
    return f"建议暂缓准入，待重大风险事项排查、财务数据补充和负面司法/经营信号解除后再议。综合风险评分{score}分。"


def _credit_decision(rating: str, score: int, sub_reports: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    if rating == "low":
        suggestion = "建议准入"
        limit_advice = "额度可结合近三年收入、经营现金流、担保覆盖和同业授信余额测算，优先匹配真实经营周转需求。"
        term_advice = "建议以一年期流动资金贷款或银行承兑/保函等短周期产品为主。"
    elif rating == "medium":
        suggestion = "谨慎准入"
        limit_advice = "建议控制首笔额度，额度释放与订单、回款、纳税流水和项目进度挂钩。"
        term_advice = "建议短期限、分批提款、按月/季监控回款表现。"
    else:
        suggestion = "暂缓准入"
        limit_advice = "暂不建议新增信用敞口，待关键风险缓释后重新评估。"
        term_advice = "如确需合作，应采用强担保、低敞口、短周期方案。"

    monitoring = [
        "持续跟踪企业工商变更、股权质押、对外投资和异常经营名录变化。",
        "按月核验销售回款、应收账款账龄、银行流水和纳税申报匹配情况。",
        "监测裁判文书、被执行、行政处罚和重大舆情新增情况。",
        "关注所属行业政策、价格周期、上下游集中度和核心客户信用变化。",
    ]
    if not sub_reports.get("financial"):
        monitoring.insert(0, "当前缺少财务专项结论，须补充近三年三大表后再形成最终额度意见。")

    return {
        "suggestion": suggestion,
        "risk_score": score,
        "credit_limit_advice": limit_advice,
        "term_advice": term_advice,
        "collateral_advice": "优先落实实际控制人连带责任、核心资产抵质押、应收账款回款监管或项目回款闭环。",
        "post_loan_monitoring": monitoring,
    }


def _executive_summary(enterprise_name: str, dimensions: List[Dict[str, Any]], sub_reports: Dict[str, Optional[Dict[str, Any]]]) -> List[str]:
    summary = [
        f"本次完整尽调围绕{enterprise_name}的工商治理、财务健康、司法合规和行业环境四个维度展开。",
        "综合评分采用专项报告风险分数加权形成，其中财务维度权重最高，司法与行业信号用于修正准入判断。",
    ]
    weakest = sorted(dimensions, key=lambda item: item["score"])[0]
    summary.append(f"当前相对薄弱维度为{weakest['name']}，评分{weakest['score']}分，需优先核验：{'；'.join(weakest.get('details', [])[:2])}。")
    financial = sub_reports.get("financial")
    if financial:
        summary.append(financial.get("recommendation") or "财务专项已形成结构化结论。")
    else:
        summary.append("财务专项尚未完成，非上市企业需上传近三年利润表、资产负债表和现金流量表后形成最终财务判断。")
    return summary


def _cross_findings(sub_reports: Dict[str, Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    business = sub_reports.get("business") or {}
    financial = sub_reports.get("financial") or {}
    legal = sub_reports.get("legal") or {}
    industry = sub_reports.get("industry") or {}

    findings = [
        {
            "title": "财务表现与经营范围匹配度",
            "risk_level": "medium" if not financial else _rating_from_score(_safe_score(financial, 70)),
            "conclusion": "已结合工商经营范围和财务专项指标观察主营业务收入、盈利质量及现金流匹配关系；若收入高增长但经营范围或资质信息不足，需补充合同、发票和流水核验。",
            "evidence_refs": ["工商经营范围", "营业收入", "经营性净现金流"],
        },
        {
            "title": "司法风险对授信安全边际的影响",
            "risk_level": legal.get("risk_rating", "medium"),
            "conclusion": legal.get("recommendation") or "司法专项未发现可直接量化的重大风险，但仍需查询权威司法网站确认新增执行和失信情况。",
            "evidence_refs": ["裁判文书", "被执行", "行政处罚"],
        },
        {
            "title": "行业环境与客户经营韧性",
            "risk_level": industry.get("risk_rating", "medium"),
            "conclusion": industry.get("recommendation") or "行业专项已输出景气度、竞争格局、政策环境和授信审查重点，可作为额度、期限和贷后监控条件的约束依据。",
            "evidence_refs": ["行业分类", "行业风险", "授信审查重点"],
        },
    ]
    if business.get("risk_summary"):
        findings.append({
            "title": "工商治理与关联风险",
            "risk_level": business.get("risk_rating", "medium"),
            "conclusion": "工商专项提示需持续核验股权结构、实控人、对外投资和异常变更，避免关联交易或治理不稳定影响偿债来源。",
            "evidence_refs": ["股东结构", "对外投资", "工商变更"],
        })
    return findings


def _evidence_docs(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    seen = set()
    for item in evidence:
        source = item.get("source") or "分析过程证据"
        key = (item.get("label"), source)
        if key in seen:
            continue
        seen.add(key)
        docs.append({
            "name": item.get("label") or "证据项",
            "source": source,
            "value": item.get("value", ""),
            "status": "verified" if source not in {"模拟财务数据", "旧模拟司法工具"} else "pending",
        })
    return docs[:30]


def merge_crew_review(
    report: Dict[str, Any],
    crew_review: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """将 CrewAI 综合审查结果合并到规则报告。"""
    if not crew_review:
        return report
    merged = {**report}
    for key in ["executive_summary", "cross_findings", "credit_decision", "due_diligence_questions"]:
        value = crew_review.get(key)
        if value:
            merged[key] = value
    if crew_review.get("recommendation"):
        merged["recommendation"] = crew_review["recommendation"]
    merged["crew_review"] = {
        "status": "completed",
        "reviewer": "CrewAI 综合审查",
    }
    return merged


def build_full_due_diligence_report(
    enterprise_name: str,
    sub_reports: Dict[str, Optional[Dict[str, Any]]],
    evidence: Optional[List[Dict[str, Any]]] = None,
    crew_review: Optional[Dict[str, Any]] = None,
    pending_upload: bool = False,
) -> Dict[str, Any]:
    """基于四个专项报告生成完整尽调报告。"""
    dimensions = [_dimension(key, sub_reports.get(key)) for key in ["business", "financial", "legal", "industry"]]
    score = _weighted_score(dimensions)
    if pending_upload:
        score = min(score, 68)
    rating = _rating_from_score(score)
    report = {
        "report_type": "full_due_diligence",
        "enterprise_name": enterprise_name,
        "risk_rating": rating,
        "risk_score": score,
        "recommendation": _recommendation(rating, score),
        "generated_from": "四个专项Agent + 规则综合评分",
        "executive_summary": _executive_summary(enterprise_name, dimensions, sub_reports),
        "risk_dimensions": dimensions,
        "credit_decision": _credit_decision(rating, score, sub_reports),
        "cross_findings": _cross_findings(sub_reports),
        "sub_reports": sub_reports,
        "evidence_docs": _evidence_docs(evidence or []),
        "due_diligence_questions": [
            "近三年审计报告意见类型、主要附注和或有负债情况是否存在异常？",
            "前五大客户及供应商集中度、关联关系和结算周期是否与收入规模匹配？",
            "新增授信用途、还款来源、回款账户和资金闭环安排是否明确？",
            "企业及实控人是否存在新增诉讼、执行、行政处罚或重大负面舆情？",
            "所属行业政策、价格周期、项目进度或核心客户信用变化是否影响订单执行？",
        ],
        "pending_upload": pending_upload,
    }
    if pending_upload:
        report["upload_required"] = True
        report["recommendation"] = "完整尽调已完成工商、司法、行业初步分析；因目标企业未识别为上市公司，需上传近三年三大财务报表后形成最终授信建议。"
        report["crew_review"] = {"status": "skipped", "reason": "等待财务报表上传"}
        return report
    return merge_crew_review(report, crew_review)
