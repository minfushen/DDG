"""Synthesize a DeepResearch-style due-diligence report."""

from __future__ import annotations

from typing import Any, Dict, List

from .report_assembler import claim_findings, financial_findings, industry_findings, refs_for_category
from .state import ResearchState
from .tool_trace import public_tool_traces


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


def _finding_summary(findings: List[Dict[str, Any]], fallback: str) -> List[str]:
    rows = [str(item.get("conclusion")) for item in findings if item.get("conclusion")]
    return rows[:4] or [fallback]


def _summary_citations(summary: List[str], refs: List[str], findings: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    citations: List[Dict[str, Any]] = []
    for index, text in enumerate(summary):
        finding_refs = []
        if findings and index < len(findings):
            finding_refs = findings[index].get("evidence_refs") or []
        citations.append({
            "text": text,
            "evidence_refs": list(dict.fromkeys(finding_refs or refs))[:5],
        })
    return citations


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


def _has_financial_narrative(evidence: List[Dict[str, Any]]) -> bool:
    return bool(_financial_report_summary(evidence))


def _industry_report_summary(evidence: List[Dict[str, Any]]) -> List[str]:
    for item in evidence:
        report = ((item.get("metadata") or {}).get("industry_analysis_report") or {})
        if report:
            return (report.get("industry_diagnostic_summary") or report.get("risk_summary") or [])[:6]
    return []


def _has_category_evidence(evidence: List[Dict[str, Any]], category: str) -> bool:
    return bool(_category_items(evidence, category))


def _verified_summary_or_boundary(
    claims: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    category: str,
    no_evidence_message: str,
) -> List[str]:
    if not _has_category_evidence(evidence, category):
        return [no_evidence_message]
    return _summary_for_category(claims, tasks, category, no_evidence_message)


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


def _financial_structured_subsections(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Expose financial agent report sections as customer-facing chapter blocks."""
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        if not report:
            continue
        flattened = [sub for section in report.get("sections") or [] for sub in section.get("subsections") or []]
        title_map = {
            "3.1 收入与利润分析": ["利润表分析", "盈利能力分析"],
            "3.2 资产负债分析": ["资产分析", "负债分析", "所有者权益分析"],
            "3.3 盈利质量与营运效率": ["现金流量表分析", "营运能力分析"],
            "3.4 偿债能力与财务信号异常": ["偿债能力分析", "主要潜在风险提示"],
        }
        output: List[Dict[str, Any]] = []
        for title, names in title_map.items():
            items: List[str] = []
            for sub in flattened:
                if sub.get("title") not in names:
                    continue
                items.extend(str(text) for text in (sub.get("analysis") or []) if text)
                items.extend(str(risk) for risk in (sub.get("risks") or []) if risk)
                if sub.get("risk提示"):
                    items.append(str(sub.get("risk提示")))
            if items:
                output.append({"title": title, "items": items[:5], "evidence_refs": report.get("codeact_evidence_refs") or []})
        if output:
            return output
    return []


def _gap_descriptions(gaps: List[Dict[str, Any]]) -> List[str]:
    return [str(gap.get("description")) for gap in gaps if gap.get("description")]


def _business_implication(score: int, has_evidence: bool) -> str:
    if not has_evidence:
        return "基于现有公开资料，暂未形成充分的工商字段闭环；授信前应将工商登记、股权穿透、异常经营和行政处罚核验作为前置条件。"
    if score >= 78:
        return "基于已取得资料推断，企业主体存续和基础治理风险总体可控，但仍需复核实控人、股权质押和关联企业风险传导。"
    if score >= 60:
        return "基于现有资料判断，主体治理存在需关注事项，建议在准入前补充权威工商和关联企业穿透信息。"
    return "主体治理风险偏高或证据缺口较大，建议暂缓额度释放，优先完成权威工商和实控人风险核验。"


def _financial_implication(score: int, has_evidence: bool) -> str:
    if not has_evidence:
        return "财务资料尚不足以支持正式额度测算；可先作公开资料预尽调，授信前必须补齐近三年三大表、审计意见、银行流水和纳税资料。"
    if score >= 78:
        return "基于已解析财务资料推断，偿债基础总体可接受，授信额度可在核实现金流、应收回款和审计意见后审慎测算。"
    if score >= 60:
        return "财务表现存在一定压力，建议将盈利质量、经营现金流、应收账款和短期债务作为授信前置核查重点。"
    return "财务风险较高或关键指标缺口明显，建议暂缓新增敞口，待财务真实性和还款来源核验后再议。"


def _legal_implication(score: int, has_evidence: bool) -> str:
    if not has_evidence:
        return "公开资料暂未形成权威司法结论；授信前需通过裁判、执行、失信、行政处罚和监管公告渠道完成复核。"
    if score >= 78:
        return "基于当前司法线索，暂未见对授信安全边界构成重大冲击的事项，但需持续监控新增诉讼、执行和处罚。"
    if score >= 60:
        return "司法合规存在需跟踪事项，建议将新增案件、处罚整改和执行状态纳入准入条件或贷后监控。"
    return "司法合规风险偏高，建议在重大案件、执行或处罚事项查清前暂缓授信或压降敞口。"


def _industry_implication(score: int, has_evidence: bool) -> str:
    if not has_evidence:
        return "行业定位和景气判断仍需补充主营构成、年报经营讨论、行业研报或内部行业政策；当前仅能作审慎预判。"
    if score >= 78:
        return "基于现有资料推断，行业与经营环境总体具备支撑，但授信期限和额度仍应受行业周期、订单持续性和回款能力约束。"
    if score >= 60:
        return "行业环境存在周期或竞争压力，建议控制授信期限，并将核心客户回款、订单变化和价格周期纳入贷后监控。"
    return "行业与经营环境风险较高，建议谨慎准入，优先核验还款来源是否能穿越当前行业周期。"


def _risk_level_text(score: int) -> str:
    if score >= 78:
        return "低风险"
    if score >= 60:
        return "中风险"
    return "高风险"


def _completeness_level(has_evidence: bool, gaps: List[Dict[str, Any]]) -> str:
    if has_evidence and not gaps:
        return "高"
    if has_evidence:
        return "中"
    return "低"


def _completeness_rows(
    business_has_evidence: bool,
    financial_has_evidence: bool,
    legal_has_evidence: bool,
    industry_has_evidence: bool,
    business_gaps: List[Dict[str, Any]],
    financial_gaps: List[Dict[str, Any]],
    legal_gaps: List[Dict[str, Any]],
    industry_gaps: List[Dict[str, Any]],
    blueprint: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    has_by_chapter = {
        "business": business_has_evidence,
        "financial": financial_has_evidence,
        "industry": industry_has_evidence,
        "legal": legal_has_evidence,
    }
    gaps_by_chapter = {
        "business": business_gaps,
        "financial": financial_gaps,
        "industry": industry_gaps,
        "legal": legal_gaps,
    }
    matrix = (blueprint or {}).get("completeness_matrix") if isinstance(blueprint, dict) else None
    if isinstance(matrix, list) and matrix:
        rows: List[Dict[str, Any]] = []
        for item in matrix:
            if not isinstance(item, dict):
                continue
            chapter_id = str(item.get("chapter_id") or "")
            has_evidence = has_by_chapter.get(chapter_id, False)
            gaps = gaps_by_chapter.get(chapter_id, [])
            level = _completeness_level(has_evidence, gaps)
            level_text = item.get("high") if level == "高" else item.get("medium") if level == "中" else item.get("low")
            rows.append({
                "title": str(item.get("dimension") or chapter_id or "资料维度"),
                "items": [f"完整度：{level}", str(level_text or item.get("fallback_language") or "需补充资料后复核。")],
            })
        if rows:
            return rows
    return [
        {"title": "工商与治理资料", "items": [f"完整度：{_completeness_level(business_has_evidence, business_gaps)}", _business_implication(70 if business_has_evidence else 55, business_has_evidence)]},
        {"title": "财务与偿债资料", "items": [f"完整度：{_completeness_level(financial_has_evidence, financial_gaps)}", _financial_implication(70 if financial_has_evidence else 55, financial_has_evidence)]},
        {"title": "行业与经营资料", "items": [f"完整度：{_completeness_level(industry_has_evidence, industry_gaps)}", _industry_implication(70 if industry_has_evidence else 55, industry_has_evidence)]},
        {"title": "司法与合规资料", "items": [f"完整度：{_completeness_level(legal_has_evidence, legal_gaps)}", _legal_implication(70 if legal_has_evidence else 55, legal_has_evidence)]},
    ]


def _chapter(
    chapter_id: str,
    title: str,
    subtitle: str,
    summary: List[str],
    refs: List[str],
    findings: List[Dict[str, Any]] | None = None,
    subsections: List[Dict[str, Any]] | None = None,
    risks: List[str] | None = None,
    required_documents: List[str] | None = None,
    unavailable_metrics: List[str] | None = None,
    data_boundary: str | None = None,
) -> Dict[str, Any]:
    return {
        "id": chapter_id,
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "summary_citations": _summary_citations(summary, refs, findings),
        "subsections": subsections or [],
        "findings": findings or [],
        "risks": risks or [],
        "required_documents": required_documents or [],
        "unavailable_metrics": unavailable_metrics or [],
        "data_boundary": data_boundary,
        "evidence_refs": list(dict.fromkeys(refs))[:12],
    }


def synthesize_research_report(state: ResearchState) -> Dict[str, Any]:
    tasks = state.get("tasks", [])
    claims = state.get("claims", [])
    gaps = state.get("gaps", [])
    evidence = state.get("evidence", [])
    high_gaps = [gap for gap in gaps if gap.get("severity") == "high"]
    enterprise_name = state.get("enterprise_name")
    blueprint = (state.get("planner") or {}).get("metadata", {}).get("blueprint", {})
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
    business_has_evidence = bool(_category_items(evidence, "business"))
    financial_has_evidence = bool(_category_items(evidence, "financial"))
    legal_has_evidence = bool(_category_items(evidence, "legal"))
    industry_has_evidence = bool(_category_items(evidence, "industry"))

    summary = [
        f"{enterprise_name}本次贷前尽调综合评分{weighted_score}分，风险等级为{_risk_level_text(weighted_score)}，建议“{suggestion}”。",
        _financial_implication(financial_score, financial_has_evidence),
        _industry_implication(industry_score, industry_has_evidence),
        "授信执行上建议先控额度、短期限、分阶段提款，并将资料补充和风险核验结果作为额度释放条件。",
    ]
    business_fallback = _business_implication(business_score, business_has_evidence)
    financial_fallback = _financial_implication(financial_score, financial_has_evidence)
    legal_fallback = _legal_implication(legal_score, legal_has_evidence)
    industry_fallback = _industry_implication(industry_score, industry_has_evidence)

    business_findings = claim_findings(claims, tasks, "business", business_fallback)
    has_financial_narrative = _has_financial_narrative(evidence)
    financial_findings_rows = [] if has_financial_narrative else (financial_findings(evidence) or claim_findings(claims, tasks, "financial", financial_fallback))
    legal_findings = claim_findings(claims, tasks, "legal", legal_fallback)
    industry_findings_rows = industry_findings(evidence) or claim_findings(claims, tasks, "industry", industry_fallback)

    business_summary = _finding_summary(business_findings, business_fallback)
    financial_summary = _financial_report_summary(evidence) or _finding_summary(financial_findings_rows, financial_fallback)
    financial_structured_subsections = _financial_structured_subsections(evidence)
    legal_summary = _finding_summary(legal_findings, legal_fallback)
    industry_summary = _industry_report_summary(evidence) or _finding_summary(industry_findings_rows, industry_fallback)

    business_refs = refs_for_category(evidence, "business")
    financial_refs = refs_for_category(evidence, "financial")
    legal_refs = refs_for_category(evidence, "legal")
    industry_refs = refs_for_category(evidence, "industry")
    cross_findings = [
        {
            "title": "财务真实性与经营匹配",
            "risk_level": _risk_status(financial_score),
            "conclusion": "结合财务专项、工商主体和行业经营证据观察收入、利润、现金流与主营业务匹配度；若财务证据不足，应将近三年三大表、银行流水和纳税资料列为授信前置材料。",
            "evidence_refs": list(dict.fromkeys(financial_refs + business_refs + industry_refs))[:6],
        },
        {
            "title": "司法合规对授信边界的影响",
            "risk_level": _risk_status(legal_score),
            "conclusion": "司法、执行、处罚和公告线索会直接影响授信准入、额度释放和担保条件；公开搜索线索需以权威司法及交易所公告复核。",
            "evidence_refs": legal_refs[:6],
        },
        {
            "title": "行业周期与还款来源稳定性",
            "risk_level": _risk_status(industry_score),
            "conclusion": "行业定位、竞争格局、政策环境和上下游议价能力共同决定客户现金流韧性，应作为期限、额度和贷后监控频率的核心约束。",
            "evidence_refs": industry_refs[:6],
        },
    ]

    risk_dimensions = [
        _dimension("工商与治理", business_score, 0.20, [_business_implication(business_score, business_has_evidence)] + business_summary[:2]),
        _dimension("财务健康度", financial_score, 0.35, [_financial_implication(financial_score, financial_has_evidence)] + financial_summary[:2]),
        _dimension("司法合规", legal_score, 0.25, [_legal_implication(legal_score, legal_has_evidence)] + legal_summary[:2]),
        _dimension("行业与经营环境", industry_score, 0.20, [_industry_implication(industry_score, industry_has_evidence)] + industry_summary[:2]),
    ]

    all_core_refs = list(dict.fromkeys(business_refs + financial_refs + legal_refs + industry_refs))[:12]
    credit_refs = list(dict.fromkeys(financial_refs + legal_refs + industry_refs + business_refs))[:8]
    credit_summary = [
        f"准入建议：{suggestion}",
        "首笔额度建议审慎控制，后续释放与订单真实性、回款流水、纳税记录和项目进度挂钩。",
        "证据缺口不直接否定客户价值，但应转化为提款前置条件、担保条件或贷后监控指标。",
    ]
    credit_findings = [{
        "title": "授信策略",
        "risk_level": risk_rating,
        "conclusion": f"建议{suggestion}；额度和期限应与证据缺口补齐情况、财务真实性、司法风险和行业周期相匹配。",
        "evidence_refs": credit_refs,
    }]
    completeness_subsections = _completeness_rows(
        business_has_evidence,
        financial_has_evidence,
        legal_has_evidence,
        industry_has_evidence,
        business_gaps,
        financial_gaps,
        legal_gaps,
        industry_gaps,
        blueprint=blueprint,
    )
    report_chapters = [
        _chapter(
            "completeness",
            "一、资料完整度总览",
            "按主体、财务、行业、司法四类资料判断当前结论强度和补充动作",
            ["本报告先判断资料覆盖情况，再给出贷前初审结论。资料不足不直接否定客户价值，但会转化为授信前置条件、担保要求或贷后监控指标。"],
            all_core_refs,
            subsections=completeness_subsections,
            data_boundary="完整度反映当前任务可取得资料，不代表外部权威数据源最终结论。",
        ),
        _chapter(
            "overview",
            "二、报告摘要与授信建议",
            "综合评级、准入建议、核心风险、授信边界与数据边界",
            summary,
            all_core_refs,
            subsections=[
                {"title": "综合评级", "items": [f"综合评分：{weighted_score}分", f"风险等级：{risk_rating}"]},
                {"title": "准入建议", "items": [suggestion, f"建议{suggestion}。正式授信前需补齐高优先级证据缺口。"]},
                {"title": "核心风险", "items": _gap_descriptions(high_gaps)[:5] or ["基于当前资料暂未识别重大阻断项，但仍需核实财务真实性、司法合规和行业周期压力。"]},
                {"title": "授信边界", "items": ["额度、期限和提款条件应与财务真实性、司法合规、行业周期和回款闭环核实结果挂钩。"]},
                {"title": "数据边界", "items": ["本报告基于当前可取得资料形成审慎判断；未取得权威源字段以“疑似/需核实”处理，并转化为授信前置核查事项。"]},
            ],
            data_boundary="当前结论为贷前初审判断，正式授信前需以权威数据源和客户原始材料复核。",
        ),
        _chapter(
            "business",
            "三、企业主体与治理结构",
            "工商登记信息、股权结构与实控人、关联企业与对外投资、异常经营/行政处罚",
            business_summary,
            business_refs,
            business_findings,
            subsections=[
                {"title": "工商登记信息", "items": business_summary[:2]},
                {"title": "股权结构与实控人", "items": ["需结合年报、工商登记和权威股权穿透数据复核。"]},
                {"title": "关联企业与对外投资", "items": ["需关注对外投资、关联交易、股权质押和实际控制人风险传导。"]},
                {"title": "异常经营/行政处罚", "items": _gap_descriptions(business_gaps)[:4] or ["基于当前资料暂未见明确重大工商异常，建议授信前完成权威工商源核验。"]},
            ],
            risks=_gap_descriptions(business_gaps),
        ),
        _chapter(
            "financial",
            "四、财务状况与偿债能力",
            "近三年收入、利润、现金流、资产负债、盈利质量、营运效率、偿债能力与财务异常信号",
            financial_summary,
            financial_refs,
            financial_findings_rows,
            subsections=financial_structured_subsections or [
                {"title": "3.1 收入与利润分析", "items": financial_summary[:2]},
                {"title": "3.2 资产负债分析", "items": ["需结合资产负债表拆分资产沉淀位置和负债期限结构，重点关注货币资金、应收账款、存货、固定资产、短期借款、票据和或有负债。"]},
                {"title": "3.3 盈利质量与营运效率", "items": ["需交叉验证毛利率、净利率、应收周转、存货周转、经营现金流和客户账期，识别收入确认和资产真实性风险。"]},
                {"title": "3.4 偿债能力与财务信号异常", "items": _gap_descriptions(financial_gaps)[:4] or ["基于当前财务资料暂未识别重大阻断项，建议重点复核审计意见、现金流、应收账龄和短债到期安排。"]},
            ],
            risks=_gap_descriptions(financial_gaps),
            required_documents=_financial_required_documents(evidence),
        ),
        _chapter(
            "industry",
            "五、行业与经营环境",
            "行业定位、周期判断、竞争格局、政策环境、上下游议价能力与授信关注点",
            industry_summary,
            industry_refs,
            industry_findings_rows,
            subsections=[
                {"title": "行业定位", "items": industry_summary[:2]},
                {"title": "周期判断", "items": ["结合行业景气度、订单周期、资本开支和客户需求变化判断经营韧性。"]},
                {"title": "竞争格局", "items": ["关注标的在子赛道中的份额、技术壁垒、客户集中度和同业竞争压力。"]},
                {"title": "政策环境", "items": ["关注监管、产业政策、地缘贸易限制及行业准入变化。"]},
                {"title": "上下游议价能力", "items": ["关注供应商集中度、客户集中度、账期和成本转嫁能力。"]},
                {"title": "授信关注点", "items": _gap_descriptions(industry_gaps)[:4] or ["建议将行业周期、核心客户回款、订单持续性和价格波动纳入额度释放和贷后监控条件。"]},
            ],
            risks=_gap_descriptions(industry_gaps),
        ),
        _chapter(
            "legal",
            "六、司法与合规风险",
            "裁判文书、被执行/失信、行政处罚、监管问询/公告与重大舆情",
            legal_summary,
            legal_refs,
            legal_findings,
            subsections=[
                {"title": "裁判文书", "items": legal_summary[:2]},
                {"title": "被执行/失信", "items": ["需以执行信息公开网、失信被执行人名单等权威源复核。"]},
                {"title": "行政处罚", "items": ["需核验处罚机关、处罚金额、处罚事由和整改状态。"]},
                {"title": "监管问询/公告", "items": ["上市公司需重点核验交易所问询、监管函、诉讼公告和重大事项公告。"]},
                {"title": "重大舆情", "items": _gap_descriptions(legal_gaps)[:4] or ["基于当前公开线索暂未见重大阻断性司法风险，仍建议在提款前完成权威司法源复核。"]},
            ],
            risks=_gap_descriptions(legal_gaps),
        ),
        _chapter(
            "risks",
            "七、交叉验证与重大风险",
            "财务与经营范围、现金流与利润、司法风险与授信安全边界、行业周期与还款来源",
            [item["conclusion"] for item in cross_findings],
            all_core_refs,
            cross_findings,
            subsections=[
                {"title": "财务与经营范围是否匹配", "items": [cross_findings[0]["conclusion"]]},
                {"title": "现金流与利润是否匹配", "items": ["重点核验利润增长是否有经营现金流、银行流水和纳税申报支撑。"]},
                {"title": "司法风险是否影响授信安全边界", "items": [cross_findings[1]["conclusion"]]},
                {"title": "行业周期是否影响还款来源", "items": [cross_findings[2]["conclusion"]]},
            ],
        ),
        _chapter(
            "credit",
            "八、信贷方案建议",
            "准入/审慎/暂缓、额度建议、期限建议、担保建议、提款前置条件与贷后监控指标",
            credit_summary,
            credit_refs,
            credit_findings,
            subsections=[
                {"title": "准入/审慎/暂缓", "items": [suggestion]},
                {"title": "额度建议", "items": ["建议先控制首笔授信额度，待财务真实性、司法风险和回款闭环核实后再逐步释放额度。"]},
                {"title": "期限建议", "items": ["建议短期限、分阶段提款，并设置按月/季复核机制。"]},
                {"title": "担保建议", "items": ["优先落实实际控制人连带责任、核心资产抵质押、应收账款回款监管或项目回款闭环。"]},
                {"title": "提款前置条件", "items": ["补齐高优先级证据缺口，完成权威工商、司法、财报和客户原始材料复核。"]},
                {"title": "贷后监控指标", "items": ["工商变更、司法新增、行政处罚、销售回款、纳税申报、行业周期和核心客户信用变化。"]},
            ],
        ),
        _chapter(
            "evidence",
            "九、证据链与待补充材料",
            "Evidence 列表、证据缺口、待客户补充材料与人工复核事项",
            ["本章节用于审查追溯：列示支撑结论的资料、仍需补充的客户材料和人工复核事项。"],
            all_core_refs,
            subsections=[
                {"title": "Evidence 列表", "items": [f"当前已归集证据 {len(evidence)} 项。"]},
                {"title": "证据缺口", "items": _gap_descriptions(gaps)[:8] or ["暂无结构化证据缺口。"]},
                {"title": "待客户补充材料", "items": _financial_required_documents(evidence)},
                {"title": "人工复核事项", "items": ["公开搜索线索、低可信来源、无权威来源字段和高优先级证据缺口均需人工复核。"]},
            ],
            required_documents=_financial_required_documents(evidence),
            data_boundary="证据附录用于审查追溯，不替代权威数据源和客户原始材料。",
        ),
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
        "cross_findings": cross_findings,
        "report_chapters": report_chapters,
        "runtime_skills": state.get("runtime_skills", {}),
        "due_diligence_blueprint": (state.get("planner") or {}).get("metadata", {}).get("blueprint", {}),
        "research_plan": tasks,
        "research_rounds": state.get("research_rounds", []),
        "follow_up_tasks": state.get("follow_up_tasks", []),
        "claims": claims,
        "evidence": evidence,
        "tool_traces": public_tool_traces(state.get("tool_traces", [])),
        "gaps": gaps,
        "summary": summary,
        "source_reliability_summary": _source_summary(evidence),
        "data_boundary": "本报告由智能尽调 DeepResearch 引擎基于公开资料、知识库和本地工具生成。公开搜索结果仅作为线索，正式授信前需结合权威工商、司法、财报和客户原始材料人工复核。",
        "timeline": state.get("timeline", []),
    }
