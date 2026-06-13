"""完整尽调报告构建器。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.evidence import normalize_evidence


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
        return 55
    if report.get("generated_from") in {"旧模拟司法工具兜底", "模拟财务数据"}:
        return min(default, 60)
    score = report.get("risk_score")
    if isinstance(score, (int, float)):
        return max(0, min(100, int(score)))
    return _score_from_rating(report.get("risk_rating"), default)


def _first_items(items: List[str], limit: int = 3) -> List[str]:
    return [item for item in items if item][:limit]


def _as_text_list(value: Any, limit: int = 5) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item][:limit]
    return [str(value)][:limit]


def _report_risks(report: Optional[Dict[str, Any]]) -> List[str]:
    if not report:
        return ["本专项尚未取得可用数据，报告仅提示需补充核验，不作为正式风险结论。"]
    if report.get("generated_from") == "旧模拟司法工具兜底":
        return ["司法公开搜索未取得稳定结果，需人工复核裁判文书、执行、失信和行政处罚等权威渠道。"]
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
    financial = sub_reports.get("financial") or {}
    is_public_pre_dd = financial.get("financial_data_status") == "public_clues_only"

    if is_public_pre_dd:
        return {
            "suggestion": "有条件初步准入",
            "risk_score": score,
            "credit_limit_advice": "当前不建议直接给出正式额度；额度需待近三年财报、银行流水、纳税资料和担保明细核验后确定。",
            "term_advice": "如需先行推进，可限于短周期、小敞口、强担保的预审批方案。",
            "collateral_advice": "优先落实实际控制人及配偶连带责任保证、核心资产抵质押、回款账户监管和受托支付。",
            "post_loan_monitoring": [
                "正式审批前补充近三年审计报告或年度财务报表，并复核资产负债率、现金流覆盖和应收账款质量。",
                "核验近12个月银行流水、纳税申报、主要销售合同和采购合同，确认收入真实性与贷款用途。",
                "持续跟踪企业工商变更、股权质押、对外投资和异常经营名录变化。",
                "监测裁判文书、被执行、行政处罚和重大舆情新增情况。",
            ],
        }

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
    financial = sub_reports.get("financial") or {}
    if financial.get("financial_data_status") == "public_clues_only":
        return [
            f"本次报告为{enterprise_name}公开资料预尽调，基于工商、司法、行业公开资料和公开财务线索形成初步判断。",
            "目标企业未识别为上市公司且未上传近三年财报，因此暂不计算毛利率、净利率、资产负债率、现金流覆盖等核心财务指标。",
            "当前结论适用于贷前初筛、客户访谈准备和资料清单生成，不可替代正式授信财务审查。",
            financial.get("recommendation") or "建议补充近三年财报、银行流水、纳税资料和主要合同后升级为财报增强尽调。",
        ]

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
    has_business = bool(sub_reports.get("business"))
    has_industry = bool(sub_reports.get("industry"))
    has_legal = bool(sub_reports.get("legal")) and legal.get("generated_from") != "司法公开搜索不可用"

    findings = [
        {
            "title": "财务表现与经营范围匹配度",
            "risk_level": "medium" if not financial else _rating_from_score(_safe_score(financial, 70)),
            "conclusion": "当前未获取近三年财报，仅能基于公开经营线索观察经营基础；正式判断需补充收入、利润、现金流、合同、发票和流水核验。" if financial.get("financial_data_status") == "public_clues_only" else ("已结合工商经营范围和财务专项指标观察主营业务收入、盈利质量及现金流匹配关系；若收入高增长但经营范围或资质信息不足，需补充合同、发票和流水核验。" if has_business else "财务专项已取得公开财报指标，但工商经营范围和资质信息尚未形成可用证据链，需补充核验后再判断收入来源匹配度。"),
            "evidence_refs": ["工商经营范围", "公开经营线索", "待补充财报"] if financial.get("financial_data_status") == "public_clues_only" else (["工商经营范围", "营业收入", "经营性净现金流"] if has_business else ["营业收入", "经营性净现金流", "待补充工商证据"]),
        },
        {
            "title": "司法风险对授信安全边际的影响",
            "risk_level": legal.get("risk_rating", "medium"),
            "conclusion": legal.get("recommendation") if has_legal else "司法数据源暂未形成可用证据链，需人工复核后再纳入正式授信判断。",
            "evidence_refs": ["裁判文书", "被执行", "行政处罚"],
        },
        {
            "title": "行业环境与客户经营韧性",
            "risk_level": industry.get("risk_rating", "medium"),
            "conclusion": industry.get("recommendation") if has_industry else "行业专项尚未形成可用证据链，需结合主营业务、年报经营讨论和行业知识库补充识别。",
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
        normalized = normalize_evidence(item, agent=item.get("agent") or "system")
        source = normalized.get("source") or "分析过程证据"
        key = (normalized.get("label"), normalized.get("value"), source)
        if key in seen:
            continue
        seen.add(key)
        docs.append({
            "id": normalized.get("id"),
            "name": normalized.get("label") or "证据项",
            "source": source,
            "source_name": normalized.get("source_name"),
            "source_url": normalized.get("source_url"),
            "source_type": normalized.get("source_type"),
            "value": normalized.get("value", ""),
            "claim": normalized.get("claim"),
            "confidence": normalized.get("confidence"),
            "reliability": normalized.get("reliability"),
            "trust_level": normalized.get("trust_level"),
            "requires_manual_review": normalized.get("requires_manual_review"),
            "status": normalized.get("status"),
            "agent": normalized.get("agent"),
            "domain": normalized.get("domain"),
        })
    return docs[:30]


def _business_highlights(report: Optional[Dict[str, Any]]) -> List[str]:
    if not report:
        return ["工商专项未取得可用结构化数据，需人工复核国家企业信用信息公示系统、上市公司公告和工商变更记录。"]
    basic_info = report.get("basic_info") or {}
    highlights = []
    for field in ["企业名称", "统一社会信用代码", "法定代表人", "注册资本", "成立日期", "经营状态"]:
        item = basic_info.get(field)
        value = item.get("value") if isinstance(item, dict) else item
        if value:
            highlights.append(f"{field}：{value}")
    return highlights[:6] or _report_risks(report)


def _industry_highlights(report: Optional[Dict[str, Any]]) -> List[str]:
    if not report:
        return ["行业专项未取得可用结构化数据，需结合主营业务、年报经营讨论和行业知识库重新识别。"]
    diagnostic_summary = _as_text_list(report.get("industry_diagnostic_summary"), 5)
    if diagnostic_summary:
        return diagnostic_summary[:5]
    industry = report.get("industry") or {}
    highlights = []
    name = industry.get("semantic_industry_name") or industry.get("name")
    if name:
        highlights.append(f"识别行业：{name}")
    path = industry.get("path")
    if path:
        highlights.append(f"标准行业路径：{' > '.join(path)}")
    highlights.extend(_as_text_list(report.get("recommendation"), 1))
    return highlights[:5] or _report_risks(report)


def _financial_highlights(report: Optional[Dict[str, Any]]) -> List[str]:
    if not report:
        return ["财务专项尚未完成，非上市企业需上传近三年三大表。"]
    if report.get("financial_data_status") == "public_clues_only":
        return [
            "当前未取得近三年财务报表，核心财务指标不可计算。",
            "财务结论仅用于公开资料预尽调，不可替代正式授信财务审查。",
            report.get("recommendation") or "建议补充财报、流水、纳税资料和主要合同后复核。",
        ]
    narrative_summary = _as_text_list(report.get("narrative_summary"), 6)
    if narrative_summary:
        return narrative_summary
    metrics = report.get("key_metrics") or {}
    if metrics:
        latest_year = metrics.get("latest_year") or "最新年度"
        return [
            f"{latest_year}年营业收入为{metrics.get('revenue', '数据不可用')}，较上年增长{metrics.get('revenue_growth', '数据不可用')}。",
            f"盈利能力方面，{latest_year}年毛利率为{metrics.get('gross_margin', '数据不可用')}，销售净利率为{metrics.get('net_margin', '数据不可用')}，净利润为{metrics.get('net_profit', '数据不可用')}。",
            f"偿债能力方面，{latest_year}年资产负债率为{metrics.get('debt_ratio', '数据不可用')}，流动比率为{metrics.get('current_ratio', '数据不可用')}。",
            f"现金流与营运质量方面，{latest_year}年经营活动产生的现金流量净额为{metrics.get('operating_cash_flow', '数据不可用')}，应收账款余额为{metrics.get('receivable', '数据不可用')}。",
            report.get("recommendation") or "财务专项已形成结构化结论。",
        ]
    highlights = []
    years = report.get("years") or []
    if years:
        highlights.append(f"已解析财务年度：{'、'.join(str(year) for year in years)}")
    highlights.extend(_as_text_list(report.get("recommendation"), 1))
    highlights.extend(_as_text_list(report.get("risk_summary"), 3))
    return highlights[:5] or ["财务专项已形成结构化结论，核心指标详见专项报告。"]


def _legal_highlights(report: Optional[Dict[str, Any]]) -> List[str]:
    if not report:
        return ["司法专项尚未形成稳定结论，需人工复核权威司法渠道。"]
    if report.get("generated_from") == "旧模拟司法工具兜底":
        return ["司法公开搜索未取得稳定结果。本章节不展示模拟案件，仅列为人工核验事项。"]
    summary = report.get("summary") or {}
    highlights = []
    for key, label in [("case_count", "裁判文书"), ("execution_count", "执行线索"), ("punishment_count", "行政处罚"), ("dishonest_count", "失信线索")]:
        value = summary.get(key)
        if isinstance(value, (int, float)):
            highlights.append(f"{label}：{int(value)}条")
    highlights.extend(_as_text_list(report.get("recommendation"), 1))
    return highlights[:5] or _report_risks(report)


def _build_report_chapters(
    enterprise_name: str,
    report_mode: str,
    summary: List[str],
    dimensions: List[Dict[str, Any]],
    cross_findings: List[Dict[str, Any]],
    credit_decision: Dict[str, Any],
    sub_reports: Dict[str, Optional[Dict[str, Any]]],
    data_boundary: str,
    required_documents: List[str],
    unavailable_metrics: List[str],
    evidence_docs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    business = sub_reports.get("business")
    financial = sub_reports.get("financial")
    legal = sub_reports.get("legal")
    industry = sub_reports.get("industry")
    mode_label = "公开资料预尽调" if report_mode == "public_pre_dd" else "财报增强尽调"
    risk_map = {item["key"]: item for item in dimensions if item.get("key")}

    return [
        {
            "id": "overview",
            "title": "报告导言与核心概要",
            "subtitle": f"{mode_label} · 面向贷前准入初筛与授信审查",
            "summary": summary,
            "highlights": [
                f"目标企业：{enterprise_name}",
                f"报告模式：{mode_label}",
                f"数据边界：{data_boundary}",
            ],
            "risks": [],
            "evidence_refs": ["完整尽调流程", "专项Agent输出", "Evidence Store"],
        },
        {
            "id": "business",
            "title": "企业基本情况与治理结构",
            "subtitle": "工商登记、经营状态、股权治理与关联风险",
            "summary": _business_highlights(business),
            "highlights": _business_highlights(business),
            "risks": _report_risks(business),
            "score": risk_map.get("business", {}).get("score"),
            "risk_level": risk_map.get("business", {}).get("status"),
            "evidence_refs": ["工商基础信息", "股东结构", "工商变更", "对外投资"],
        },
        {
            "id": "industry",
            "title": "行业环境与经营分析",
            "subtitle": "行业识别、景气度、竞争格局、政策环境与上下游",
            "summary": _industry_highlights(industry),
            "highlights": _industry_highlights(industry),
            "risks": _report_risks(industry),
            "score": risk_map.get("industry", {}).get("score"),
            "risk_level": risk_map.get("industry", {}).get("status"),
            "evidence_refs": ["行业代码库", "行业知识库", "授信审查重点"],
        },
        {
            "id": "financial",
            "title": "财务状况与偿债能力",
            "subtitle": "收入利润、资产负债、现金流、财务真实性与还款来源",
            "summary": _financial_highlights(financial),
            "highlights": _financial_highlights(financial),
            "risks": _report_risks(financial),
            "score": risk_map.get("financial", {}).get("score"),
            "risk_level": risk_map.get("financial", {}).get("status"),
            "unavailable_metrics": unavailable_metrics,
            "required_documents": required_documents,
            "evidence_refs": ["近三年三大表", "银行流水", "纳税资料", "主要合同"],
        },
        {
            "id": "legal",
            "title": "司法与合规风险",
            "subtitle": "裁判文书、被执行、失信、行政处罚与重大负面线索",
            "summary": _legal_highlights(legal),
            "highlights": _legal_highlights(legal),
            "risks": _report_risks(legal),
            "score": risk_map.get("legal", {}).get("score"),
            "risk_level": risk_map.get("legal", {}).get("status"),
            "evidence_refs": ["裁判文书", "执行信息", "行政处罚", "公开搜索线索"],
        },
        {
            "id": "risks",
            "title": "重大风险识别与交叉验证",
            "subtitle": "将工商、财务、司法、行业专项结论合并审查",
            "summary": [item.get("conclusion", "") for item in cross_findings if item.get("conclusion")],
            "highlights": [item.get("title", "交叉发现") for item in cross_findings],
            "risks": [item.get("conclusion", "") for item in cross_findings if item.get("risk_level") != "low"],
            "findings": cross_findings,
            "evidence_refs": ["专项报告摘要", "交叉风险规则", "CrewAI综合审查"],
        },
        {
            "id": "credit",
            "title": "调查结论与信贷建议",
            "subtitle": "准入意见、额度边界、期限结构、担保条件和审批前置要求",
            "summary": [
                f"准入建议：{credit_decision.get('suggestion') or '待审查'}",
                credit_decision.get("credit_limit_advice") or "额度需结合财务真实性、担保覆盖和回款闭环测算。",
                credit_decision.get("term_advice") or "建议短周期、分阶段、可监控的授信安排。",
                credit_decision.get("collateral_advice") or "需落实实际控制人责任和有效担保结构。",
            ],
            "highlights": [credit_decision.get("suggestion") or "待审查"],
            "risks": [],
            "evidence_refs": ["综合评分", "授信政策知识库", "专项风险结论"],
        },
        {
            "id": "post_loan",
            "title": "贷后管理要求",
            "subtitle": "提款条件、资金用途、回款账户、风险预警与复核频率",
            "summary": _as_text_list(credit_decision.get("post_loan_monitoring"), 8),
            "highlights": _as_text_list(credit_decision.get("post_loan_monitoring"), 4),
            "risks": [],
            "evidence_refs": ["贷后检查模板", "资金用途核验", "回款监测"],
        },
        {
            "id": "evidence",
            "title": "数据来源、证据与待补充材料",
            "subtitle": "证据链、置信度、人工复核项和资料补充清单",
            "summary": [data_boundary],
            "highlights": [f"已归集证据项：{len(evidence_docs)}项"],
            "risks": ["标记为待复核的证据不得直接作为最终审批依据。"],
            "required_documents": required_documents,
            "unavailable_metrics": unavailable_metrics,
            "evidence_refs": [doc.get("name") or doc.get("source") or "证据项" for doc in evidence_docs[:8]],
        },
    ]


def merge_crew_review(
    report: Dict[str, Any],
    crew_review: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """将 CrewAI 综合审查结果合并到规则报告。"""
    if not crew_review:
        return report
    # CrewAI review is advisory only for now. Earlier free-form generations
    # polluted customer-facing text, so do not let it override deterministic
    # report fields until a stricter schema and quality gate are in place.
    report["crew_review"] = {
        "status": "advisory_ignored",
        "reviewer": "CrewAI 综合审查",
        "reason": "综合审查结果暂不覆盖正式报告正文，避免生成文本污染授信结论。",
    }
    report["crew_review_advisory"] = crew_review
    return report


def build_full_due_diligence_report(
    enterprise_name: str,
    sub_reports: Dict[str, Optional[Dict[str, Any]]],
    evidence: Optional[List[Dict[str, Any]]] = None,
    crew_review: Optional[Dict[str, Any]] = None,
    pending_upload: bool = False,
    report_mode: str = "financial_enhanced_dd",
    financial_data_status: Optional[str] = None,
) -> Dict[str, Any]:
    """基于四个专项报告生成完整尽调报告。"""
    dimensions = [_dimension(key, sub_reports.get(key)) for key in ["business", "financial", "legal", "industry"]]
    score = _weighted_score(dimensions)
    missing_keys = [key for key in ["business", "legal", "industry"] if not sub_reports.get(key)]
    if missing_keys:
        score = min(score, 72)
    legal_report = sub_reports.get("legal") or {}
    if legal_report.get("generated_from") in {"司法公开搜索不可用", "旧模拟司法工具兜底"}:
        score = min(score, 75)
    if pending_upload:
        score = min(score, 68)
    if report_mode == "public_pre_dd":
        score = min(score, 72)
    rating = _rating_from_score(score)
    financial = sub_reports.get("financial") or {}
    required_documents = financial.get("required_documents") or []
    unavailable_metrics = financial.get("unavailable_metrics") or []
    summary = _executive_summary(enterprise_name, dimensions, sub_reports)
    credit_decision = _credit_decision(rating, score, sub_reports)
    cross_findings = _cross_findings(sub_reports)
    evidence_docs = _evidence_docs(evidence or [])
    if report_mode == "public_pre_dd":
        data_boundary = "当前未获取近三年财务报表，财务结论仅基于公开资料线索；正式授信前必须补充财报并复核核心指标。"
    elif missing_keys or legal_report.get("generated_from") == "司法公开搜索不可用":
        data_boundary = "当前报告已取得部分公开财务数据，但工商、行业或司法证据链尚不完整；本报告只能用于客户经理初筛和访谈准备，不可直接作为授信审批依据。"
    else:
        data_boundary = "当前报告已包含专项财务数据，仍需结合原始凭证和人工尽调复核。"
    report_mode_label = "公开资料预尽调" if report_mode == "public_pre_dd" else "财报增强尽调"
    report = {
        "report_type": "full_due_diligence",
        "report_mode": report_mode,
        "report_mode_label": report_mode_label,
        "financial_data_status": financial_data_status or financial.get("financial_data_status") or "complete",
        "financial_enhancement_available": report_mode == "public_pre_dd",
        "enterprise_name": enterprise_name,
        "risk_rating": rating,
        "risk_score": score,
        "recommendation": _recommendation(rating, score),
        "generated_from": "四个专项Agent + 规则综合评分",
        "executive_summary": summary,
        "risk_dimensions": dimensions,
        "credit_decision": credit_decision,
        "cross_findings": cross_findings,
        "sub_reports": sub_reports,
        "evidence_docs": evidence_docs,
        "data_boundary": data_boundary,
        "unavailable_metrics": unavailable_metrics,
        "required_documents": required_documents,
        "report_chapters": _build_report_chapters(
            enterprise_name=enterprise_name,
            report_mode=report_mode,
            summary=summary,
            dimensions=dimensions,
            cross_findings=cross_findings,
            credit_decision=credit_decision,
            sub_reports=sub_reports,
            data_boundary=data_boundary,
            required_documents=required_documents,
            unavailable_metrics=unavailable_metrics,
            evidence_docs=evidence_docs,
        ),
        "due_diligence_questions": [
            "近三年审计报告意见类型、主要附注和或有负债情况是否存在异常？",
            "前五大客户及供应商集中度、关联关系和结算周期是否与收入规模匹配？",
            "新增授信用途、还款来源、回款账户和资金闭环安排是否明确？",
            "企业及实控人是否存在新增诉讼、执行、行政处罚或重大负面舆情？",
            "所属行业政策、价格周期、项目进度或核心客户信用变化是否影响订单执行？",
        ],
        "pending_upload": pending_upload,
    }
    if missing_keys or legal_report.get("generated_from") == "司法公开搜索不可用":
        report["recommendation"] = f"建议作为初步尽调结果使用。当前综合评分{score}分，但工商、行业或司法证据链仍需补齐，正式授信前应完成权威工商登记、司法公开信息和行业经营事实核验。"
        report["credit_decision"]["suggestion"] = "初步谨慎准入"
        for chapter in report.get("report_chapters", []):
            if chapter.get("id") == "credit":
                chapter["summary"] = [
                    "准入建议：初步谨慎准入",
                    "当前仅可作为客户经理初筛和访谈准备材料，暂不建议直接进入正式额度审批。",
                    "正式授信前需补齐工商、行业、司法证据链，并复核财务原始凭证、审计意见和贷款用途。",
                    report["credit_decision"].get("collateral_advice") or "需落实有效担保结构和回款闭环。",
                ]
                chapter["highlights"] = ["初步谨慎准入"]
    if report_mode == "public_pre_dd":
        report["recommendation"] = "当前建议作为公开资料预尽调结论使用。目标企业具备进一步尽调价值时，应在补充近三年财报、银行流水、纳税资料、主要合同和担保明细后，再形成正式授信额度、期限和风险定价建议。"
        report["crew_review"] = {"status": "skipped", "reason": "公开资料预尽调阶段不调用综合审查模型，避免基于缺失财务数据过度推断"}
        return report
    if pending_upload:
        report["upload_required"] = True
        report["recommendation"] = "完整尽调已完成工商、司法、行业初步分析；因目标企业未识别为上市公司，需上传近三年三大财务报表后形成最终授信建议。"
        report["crew_review"] = {"status": "skipped", "reason": "等待财务报表上传"}
        return report
    return merge_crew_review(report, crew_review)
