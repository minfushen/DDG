"""Synthesize a DeepResearch-style due-diligence report."""

from __future__ import annotations

from typing import Any, Dict, List

from .report_assembler import claim_findings, financial_findings, industry_findings, relationship_findings, sentiment_findings, refs_for_category, sanitize_chapter_refs
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
    """Expose financial agent report as customer-facing chapter blocks.

    Priority: LLM narrative diagnostics (attribution) > narrative summary > legacy sections.
    """
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        if not report:
            continue

        diagnostics = (report.get("narrative_diagnostics") or {}).get("diagnostics") or []
        if diagnostics:
            output: List[Dict[str, Any]] = []
            title_map = {
                "3.1 收入与利润分析": "盈利质量与成长性风险",
                "3.2 资产负债分析": "资本结构与偿债能力风险",
                "3.3 盈利质量与营运效率": "资产真实性与营运效率风险",
                "3.4 偿债能力与财务信号异常": "资本结构与偿债能力风险",
            }
            diagnostic_by_title = {d.get("title"): d for d in diagnostics if d.get("title")}
            for section_title, diag_title in title_map.items():
                diag = diagnostic_by_title.get(diag_title)
                if not diag:
                    continue
                items: List[str] = []
                if diag.get("phenomenon"):
                    items.append(str(diag["phenomenon"]))
                if diag.get("driver"):
                    items.append(f"风险实质：{diag['driver']}")
                if diag.get("verification_action"):
                    actions = diag["verification_action"]
                    if isinstance(actions, list) and actions:
                        items.append(f"核查动作：{'；'.join(str(a) for a in actions)}")
                if diag.get("missing_items"):
                    missing = diag["missing_items"]
                    if isinstance(missing, list) and missing:
                        items.append(f"待补充：{'、'.join(str(m) for m in missing)}")
                if items:
                    output.append({
                        "title": section_title,
                        "items": items[:6],
                        "evidence_refs": report.get("codeact_evidence_refs") or [],
                    })
            if output:
                return output

        # Fallback 1: narrative_summary if diagnostics unavailable.
        summary = report.get("narrative_summary") or []
        if summary:
            title_map = {
                "3.1 收入与利润分析": ["3.1 收入与利润分析"],
                "3.2 资产负债分析": ["3.2 资产负债分析"],
                "3.3 盈利质量与营运效率": ["3.3 盈利质量与营运效率"],
                "3.4 偿债能力与财务信号异常": ["3.4 偿债能力与财务信号异常"],
            }
            output = []
            for section_title, prefixes in title_map.items():
                items = [s for s in summary if any(str(s).startswith(p) for p in prefixes)]
                if items:
                    output.append({
                        "title": section_title,
                        "items": [str(i) for i in items[:3]],
                        "evidence_refs": report.get("codeact_evidence_refs") or [],
                    })
            if output:
                return output

        # Fallback 2: legacy hard-coded sections (original behavior).
        flattened = [sub for section in report.get("sections") or [] for sub in section.get("subsections") or []]
        title_map = {
            "3.1 收入与利润分析": ["利润表分析", "盈利能力分析"],
            "3.2 资产负债分析": ["资产分析", "负债分析", "所有者权益分析"],
            "3.3 盈利质量与营运效率": ["现金流量表分析", "营运能力分析"],
            "3.4 偿债能力与财务信号异常": ["偿债能力分析", "主要潜在风险提示"],
        }
        output = []
        for title, names in title_map.items():
            items: List[str] = []
            for sub in flattened:
                if sub.get("title") not in names:
                    continue
                items.extend(str(text) for text in (sub.get("analysis") or []) if text)
                items.extend(str(risk) for risk in (sub.get("risks") or []) if text)
                if sub.get("risk提示"):
                    items.append(str(sub.get("risk提示")))
            if items:
                output.append({"title": title, "items": items[:5], "evidence_refs": report.get("codeact_evidence_refs") or []})
        if output:
            return output
    return []


def _industry_subsections(evidence: List[Dict[str, Any]], industry_summary: List[str], industry_gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build industry section subsections from the full industry_analysis_report.

    Falls back to public-info snippets and finally to template placeholders.
    """
    report: Dict[str, Any] | None = None
    for item in evidence:
        report = ((item.get("metadata") or {}).get("industry_analysis_report") or {})
        if report:
            break

    sections = report.get("sections") or [] if report else []
    public_info = report.get("listed_company_public_info") or {} if report else {}
    if not public_info:
        for item in evidence:
            if item.get("source_type") == "listed_company_public_info":
                public_info = item.get("metadata", {}).get("public_info") or {}
                if public_info:
                    break

    # Try to map report sections to chapter subsections.
    title_map = {
        "行业定位与周期判断": "行业定位",
        "行业识别结论": None,  # used as metadata, not a chapter subsection
        "年报经营讨论与主营构成": "行业定位",
        "行业地位与研报摘要": "竞争格局",
        "诉讼公告、担保质押与资本市场风险线索": "政策环境",
        "行业尽调重点": "授信关注点",
        "行业动态规则与关键假设": "授信关注点",
        "关键财务指标阈值": None,
        "行业风险": "周期判断",
        "建议来源与核验路径": None,
        "知识库来源": None,
    }
    mapped: Dict[str, List[str]] = {
        "行业定位": [],
        "周期判断": [],
        "竞争格局": [],
        "政策环境": [],
        "上下游议价能力": [],
        "授信关注点": [],
    }

    for sec in sections:
        sec_title = sec.get("title", "")
        target = title_map.get(sec_title)
        if target is None:
            continue
        analysis = sec.get("analysis") or []
        risks = sec.get("risks") or []
        rows = sec.get("rows") or []
        mapped[target].extend(str(a) for a in analysis if a)
        if sec_title == "年报经营讨论与主营构成" and rows:
            mapped[target].append("主营构成：" + "；".join(
                f"{row.get('item_name')} {row.get('income_ratio')}"
                for row in rows[:6] if isinstance(row, dict)
            ))
        if sec_title == "行业风险" and risks:
            mapped["周期判断"].extend(str(r) for r in risks[:4])

    # Public info fallback for missing dimensions.
    if public_info:
        basic = public_info.get("basic_info") or {}
        review = public_info.get("annual_business_review") or {}
        clues = public_info.get("search_clues") or {}
        if not mapped["行业定位"]:
            mapped["行业定位"].extend(filter(None, [
                f"公开行业标签：{basic.get('industry')}" if basic.get("industry") else None,
                f"主营业务：{basic.get('main_business')}" if basic.get("main_business") else None,
                review.get("business_review") if review.get("business_review") else None,
            ]))
        if not mapped["竞争格局"]:
            mapped["竞争格局"].extend(
                str(item.get("content", ""))[:240]
                for item in (clues.get("industry_position") or [])[:3]
                if item.get("content")
            )
        if not mapped["政策环境"]:
            mapped["政策环境"].extend(
                str(item.get("content", ""))[:240]
                for item in (clues.get("research_summaries") or [])[:3]
                if item.get("content")
            )

    # Final template fallback for any still-empty dimension.
    fallbacks = {
        "行业定位": ["结合标准行业分类、主营构成和年报经营讨论判断企业在产业链中的位置。"],
        "周期判断": ["结合行业景气度、订单周期、资本开支和客户需求变化判断经营韧性。"],
        "竞争格局": ["关注标的在子赛道中的份额、技术壁垒、客户集中度和同业竞争压力。"],
        "政策环境": ["关注监管、产业政策、地缘贸易限制及行业准入变化。"],
        "上下游议价能力": ["关注供应商集中度、客户集中度、账期和成本转嫁能力。"],
        "授信关注点": ["建议将行业周期、核心客户回款、订单持续性和价格波动纳入额度释放和贷后监控条件。"],
    }

    output: List[Dict[str, Any]] = []
    for title, fallback in fallbacks.items():
        items = mapped.get(title) or []
        if not items:
            items = fallback
        output.append({"title": title, "items": items[:5]})

    # ── 2D table: key financial metric thresholds from industry guides ──
    metric_table: Dict[str, Any] | None = None
    for sec in sections:
        if sec.get("title") == "八、关键财务指标阈值":
            rows = sec.get("rows") or []
            if rows and isinstance(rows[0], dict) and "headers" in rows[0] and "rows" in rows[0]:
                metric_table = {
                    "columns": rows[0]["headers"],
                    "rows": rows[0]["rows"],
                    "source": "行业指南知识库",
                }
            elif rows:
                # Fallback for list-of-dict rows.
                metric_table = {
                    "columns": list(rows[0].keys()) if rows else [],
                    "rows": rows,
                    "source": "行业指南知识库",
                }
            break
    if metric_table:
        output.append({
            "title": "行业关键指标阈值",
            "items": ["以下为行业指南中给出的关键财务指标阈值参考，可用于与标的财务数据进行横向对比。"],
            "table": metric_table,
        })

    # ── Deep narrative: industry diagnostics ──
    diagnostics_raw = report.get("industry_diagnostics") or {} if report else {}
    if isinstance(diagnostics_raw, dict):
        diagnostics = diagnostics_raw.get("diagnostics") or []
    else:
        diagnostics = diagnostics_raw
    if diagnostics:
        diagnostic_items: List[str] = []
        for d in diagnostics[:5]:
            title = d.get("title") or "行业诊断"
            current = d.get("current_anchor") or ""
            risk = d.get("risk_substance") or ""
            actions = d.get("verification_actions") or []
            missing = d.get("missing_items") or []
            parts = [f"【{title}】"]
            if current:
                parts.append(f"现状锚定：{current}")
            if risk:
                parts.append(f"风险实质：{risk}")
            if actions:
                parts.append(f"核查要点：{'；'.join(str(a) for a in actions if a)}")
            if missing:
                parts.append(f"待补充：{'；'.join(str(m) for m in missing if m)}")
            diagnostic_items.append("\n".join(parts))
        if diagnostic_items:
            output.append({
                "title": "行业深度诊断",
                "items": diagnostic_items,
            })

    return output


def _legal_subsections(evidence: List[Dict[str, Any]], legal_summary: List[str], legal_gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build legal section subsections from cninfo, yuandian, legal_agent and public clues."""
    cninfo_risk: Dict[str, Any] | None = None
    yuandian_risk: Dict[str, Any] | None = None
    legal_report: Dict[str, Any] | None = None
    public_clues: List[Dict[str, Any]] = []
    for item in evidence:
        source_type = item.get("source_type")
        metadata = item.get("metadata") or {}
        if source_type == "cninfo_webapi_risk":
            cninfo_risk = metadata
        elif source_type == "yuandian_legal_risk":
            yuandian_risk = metadata
        elif source_type == "legal_analysis_report" or (metadata.get("legal_analysis_report") and not legal_report):
            legal_report = metadata.get("legal_analysis_report") or metadata
        elif source_type in {"public_web_search_clue", "official_or_authoritative_public_source"}:
            if isinstance(metadata, dict) and metadata.get("title"):
                public_clues.append(metadata)

    risk_counts: Dict[str, int] = {}
    risk_records: Dict[str, List[Dict[str, Any]]] = {}
    if cninfo_risk:
        for key, label in [("litigation", "诉讼"), ("guarantees", "对外担保"), ("penalties", "处罚"), ("asset_freezes", "资产冻结"), ("arbitration", "仲裁")]:
            section = cninfo_risk.get(key) or {}
            risk_counts[label] = section.get("count", 0)
            risk_records[label] = section.get("records", []) or []

    # ── Build unified case summary table ────────────────────────────
    case_rows: List[Dict[str, Any]] = []

    # 1. Yuandian case summaries (structured)
    yuandian_summaries = (yuandian_risk or {}).get("case_summaries") or []
    for s in yuandian_summaries[:8]:
        if not isinstance(s, dict):
            continue
        parties = s.get("plaintiffs") or s.get("defendants") or s.get("parties") or []
        case_rows.append({
            "类型": "裁判文书",
            "案号": s.get("case_number") or "",
            "案由": s.get("case_cause") or "",
            "法院/来源": s.get("court") or "元典案例库",
            "当事人": "、".join(str(p) for p in parties) or "",
            "日期": s.get("judgment_date") or "",
            "摘要": (s.get("title") or "")[:80],
        })

    # 2. Legal agent legal_items
    legal_items = (legal_report or {}).get("legal_items") or []
    for item in legal_items[:8]:
        if not isinstance(item, dict):
            continue
        case_rows.append({
            "类型": "、".join(str(t) for t in item.get("types") or []) or "司法线索",
            "案号": "、".join(str(n) for n in item.get("case_numbers") or []) or "",
            "案由": "、".join(str(c) for c in item.get("causes") or []) or "",
            "法院/来源": item.get("source") or "公开搜索",
            "当事人": "",
            "日期": "",
            "摘要": (item.get("excerpt") or item.get("title") or "")[:80],
        })

    # 3. Cninfo material records (heuristic)
    for label in ["诉讼", "处罚", "对外担保"]:
        for rec in risk_records.get(label, [])[:5]:
            if not isinstance(rec, dict):
                continue
            summary_text = next((str(v) for v in rec.values() if isinstance(v, str) and v.strip()), "")
            case_rows.append({
                "类型": label,
                "案号": "",
                "案由": "",
                "法院/来源": "巨潮资讯WebAPI",
                "当事人": "",
                "日期": "",
                "摘要": summary_text[:80],
            })

    # ── Build deep narrative paragraphs ─────────────────────────────
    narrative_items: List[str] = []
    total_yuandian = (yuandian_risk or {}).get("total", len(yuandian_summaries))
    if total_yuandian:
        summary = (yuandian_risk or {}).get("summary") or {}
        causes = summary.get("case_cause_distribution") or {}
        levels = summary.get("court_level_distribution") or {}
        cause_part = ""
        if causes:
            cause_part = "主要案由包括" + "、".join(f"{k}（{v}条）" for k, v in sorted(causes.items(), key=lambda x: -x[1])[:3]) + "。"
        level_part = ""
        if levels:
            level_part = "审理法院层级分布：" + "、".join(f"{k}{v}条" for k, v in levels.items()) + "。"
        narrative_items.append(
            f"元典案例库返回{total_yuandian}条司法线索。{cause_part}{level_part}"
        )
        for s in yuandian_summaries[:2]:
            title = s.get("title") or ""
            court = s.get("court") or ""
            cause = s.get("case_cause") or ""
            date = s.get("judgment_date") or ""
            parties = s.get("plaintiffs") or s.get("defendants") or s.get("parties") or []
            narrative_items.append(
                f"典型案件：{title}（{court}，{date}）。案由：{cause}；当事人：{'、'.join(str(p) for p in parties)}。"
            )

    cninfo_total = sum(risk_counts.values())
    if cninfo_total:
        narrative_items.append(
            f"巨潮官方API返回结构化司法风险：诉讼{risk_counts.get('诉讼', 0)}条、对外担保{risk_counts.get('对外担保', 0)}条、处罚{risk_counts.get('处罚', 0)}条、资产冻结{risk_counts.get('资产冻结', 0)}条、仲裁{risk_counts.get('仲裁', 0)}条。"
        )

    if not narrative_items:
        narrative_items.append(
            "基于当前资料暂未识别到结构化司法风险记录，但仍建议以裁判文书网、执行信息公开网、国家企业信用信息公示系统和交易所公告复核。"
        )

    subsections = [
        {
            "title": "司法风险概览",
            "items": narrative_items[:4],
        },
        {
            "title": "被执行/失信",
            "items": [
                f"巨潮官方API返回被执行/资产冻结线索：{risk_counts.get('资产冻结', 0)}条"
                if risk_counts.get("资产冻结", 0) > 0
                else "巨潮官方API暂未返回被执行、失信或资产冻结记录，仍需以执行信息公开网、失信被执行人名单复核。"
            ],
        },
        {
            "title": "行政处罚",
            "items": [
                f"巨潮官方API返回处罚线索：{risk_counts.get('处罚', 0)}条，需核验处罚机关、金额、事由和整改状态。"
                if risk_counts.get("处罚", 0) > 0
                else "巨潮官方API暂未返回行政处罚记录，仍需以国家企业信用信息公示系统、行业主管部门复核。"
            ],
        },
        {
            "title": "监管问询/公告",
            "items": [
                f"巨潮官方API返回对外担保线索：{risk_counts.get('对外担保', 0)}条，需关注担保对象、金额和代偿风险。"
                if risk_counts.get("对外担保", 0) > 0
                else "巨潮官方API暂未返回对外担保记录；上市公司仍需重点核验交易所问询、监管函、诉讼公告和重大事项公告。"
            ],
        },
        {
            "title": "重大舆情",
            "items": _gap_descriptions(legal_gaps)[:4]
                or ["基于当前公开线索暂未见重大阻断性司法风险，仍建议在提款前完成权威司法源复核。"],
        },
    ]

    if case_rows:
        subsections.insert(1, {
            "title": "司法线索明细表",
            "items": ["以下为元典/巨潮/legal_agent 返回的司法线索结构化摘要，可作为贷前复核清单。"],
            "table": {
                "columns": ["类型", "案号", "案由", "法院/来源", "当事人", "日期", "摘要"],
                "rows": case_rows[:15],
                "source": "元典开放平台 / 巨潮资讯WebAPI / 公开搜索",
            },
        })

    return subsections


def _cross_validation_subsections(
    evidence: List[Dict[str, Any]],
    cross_findings: List[Dict[str, Any]],
    financial_score: int,
    legal_score: int,
    industry_score: int,
) -> List[Dict[str, Any]]:
    """Build cross-validation subsections from real evidence instead of hard-coded templates."""
    # Load financial narrative diagnostics and codeact results.
    financial_diagnostics: List[Dict[str, Any]] = []
    codeact_analysis: Dict[str, Any] | None = None
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        if report:
            nd = report.get("narrative_diagnostics") or {}
            financial_diagnostics = nd.get("diagnostics") or []
            codeact_analysis = report.get("codeact_analysis") or codeact_analysis
            break

    # Load cninfo risk counts.
    cninfo_risk: Dict[str, Any] | None = None
    for item in evidence:
        if item.get("source_type") == "cninfo_webapi_risk":
            cninfo_risk = item.get("metadata") or {}
            break
    risk_total = 0
    if cninfo_risk:
        risk_total = sum(
            (cninfo_risk.get(k) or {}).get("count", 0)
            for k in ["litigation", "guarantees", "penalties", "asset_freezes", "arbitration"]
        )

    # Load industry diagnostic summary.
    industry_summary: List[str] = []
    for item in evidence:
        report = ((item.get("metadata") or {}).get("industry_analysis_report") or {})
        if report:
            industry_summary = (report.get("industry_diagnostic_summary") or report.get("risk_summary") or [])[:4]
            break

    # 1. 财务真实性与经营匹配
    business_match_items = [cross_findings[0]["conclusion"]]
    for diag in financial_diagnostics:
        if "成长性" in str(diag.get("title", "")) and diag.get("driver"):
            business_match_items.append(f"经营匹配：{diag['driver']}")
            break

    # 2. 现金流与利润是否匹配
    cash_profit_items = [
        "重点核验利润增长是否有经营现金流、银行流水和纳税申报支撑；经营现金流/净利润长期低于1或背离扩大需警惕收入确认质量。"
    ]
    for diag in financial_diagnostics:
        title = str(diag.get("title", ""))
        if ("营运" in title or "资产" in title) and diag.get("phenomenon"):
            cash_profit_items.append(f"现金流勾稽：{diag['phenomenon']}")
            break
    if codeact_analysis and codeact_analysis.get("validation_passed") is False:
        issues = codeact_analysis.get("validation_issues") or []
        if issues:
            cash_profit_items.append(f"CodeAct 三大表勾稽异常：{issues[0]}")

    # 3. 司法风险是否影响授信安全边界
    if risk_total > 0:
        legal_items = [
            f"巨潮官方API返回{risk_total}条司法/合规风险线索，直接影响授信准入、额度释放和担保条件。",
            "需重点核验诉讼主体、标的金额、担保对象、处罚事由及整改进度。",
        ]
    else:
        legal_items = [
            "巨潮官方API暂未返回司法/合规风险线索，但公开搜索线索需以权威司法及交易所公告复核。",
        ]

    # 4. 行业周期是否影响还款来源
    industry_items = [cross_findings[2]["conclusion"]]
    if industry_summary:
        industry_items.extend(str(s) for s in industry_summary[:2])

    return [
        {"title": "财务与经营范围是否匹配", "items": business_match_items[:3]},
        {"title": "现金流与利润是否匹配", "items": cash_profit_items[:3]},
        {"title": "司法风险是否影响授信安全边界", "items": legal_items[:3]},
        {"title": "行业周期是否影响还款来源", "items": industry_items[:3]},
    ]


def _gap_descriptions(gaps: List[Dict[str, Any]]) -> List[str]:
    return [str(gap.get("description")) for gap in gaps if gap.get("description")]


def _business_subsections(all_evidence: List[Dict[str, Any]], business_summary: List[str], business_gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build business section subsections dynamically from evidence (all categories)."""
    shareholder_items: List[str] = []
    shareholder_table: Dict[str, Any] | None = None
    penalty_items: List[str] = []
    related_items: List[str] = []
    registry_rows: List[Dict[str, str]] = []

    for item in all_evidence:
        source_type = item.get("source_type", "")
        metadata = item.get("metadata") or {}

        if source_type == "official_business_registry":
            biz_fields = (metadata.get("extracted_fields") or {}).get("business_fields") or {}
            shareholders = metadata.get("shareholders") or {}
            ctrl = (shareholders.get("actual_controller") or {}).get("records", [])
            top = shareholders.get("top_shareholders") or {}
            capital_changes = shareholders.get("share_capital_changes") or {}
            latest_ctrl = ctrl[-1].get("F004V") if ctrl else None
            ctrl_type = biz_fields.get("控制方式")

            # Structured registry table: prefer CNINFO fields, fallback to Tavily search clues.
            if biz_fields:
                registry_rows = [
                    {"项目": k, "登记信息": str(v)}
                    for k, v in biz_fields.items()
                    if v and str(v).strip()
                ]

            if metadata.get("shareholder_table", {}).get("success"):
                shareholder_table = metadata["shareholder_table"]

            if latest_ctrl:
                shareholder_items.append(f"实际控制人：{latest_ctrl}" + (f"（{ctrl_type}）" if ctrl_type else ""))
            if top.get("count", 0) > 0:
                shareholder_items.append(f"十大股东共{top['count']}条记录（来源：巨潮官方数据）")
            if capital_changes.get("count", 0) > 0:
                related_items.append(f"股本变动记录：{capital_changes['count']}条")

        # Risk data from legal category evidence
        if source_type == "cninfo_webapi_risk":
            for key, label in [("litigation", "诉讼"), ("penalties", "处罚"), ("guarantees", "对外担保"), ("asset_freezes", "资产冻结"), ("arbitration", "仲裁")]:
                section = metadata.get(key) or {}
                count = section.get("count", 0)
                if count > 0:
                    penalty_items.append(f"{label}：{count}条")

    # Fallback textual summaries when structured data is missing.
    if not registry_rows:
        registry_rows = [{"项目": "工商登记", "登记信息": business_summary[0] if business_summary else "暂无结构化工商登记信息"}]

    # If only code is present (no company name/controller), keep a human-readable note in items.
    registry_items = business_summary[:2] if len(business_summary) >= 2 else ["以下工商登记信息来自巨潮官方API或公开工商数据源。"]
    if not shareholder_items:
        shareholder_items = ["需结合年报、工商登记和权威股权穿透数据复核。"]
    if not related_items:
        related_items = ["需关注对外投资、关联交易、股权质押和实际控制人风险传导。"]
    if not penalty_items:
        penalty_items = ["基于当前资料暂未见明确重大工商异常，建议授信前完成权威工商源核验。"]

    shareholder_sub: Dict[str, Any] = {"title": "股权结构与实控人", "items": shareholder_items[:5]}
    if shareholder_table and shareholder_table.get("rows"):
        shareholder_sub["table"] = {
            "columns": shareholder_table.get("columns", []),
            "rows": shareholder_table["rows"],
            "source": f"巨潮资讯WebAPI（报告期：{shareholder_table.get('report_date', '')}）",
        }

    # ── Deep narrative from business_analysis_report ─────────────────
    narrative_items: List[str] = []
    for item in all_evidence:
        report = ((item.get("metadata") or {}).get("business_analysis_report") or {})
        if report and report.get("narrative_summary"):
            narrative_items = report["narrative_summary"][:6]
            break

    subsections: List[Dict[str, Any]] = []
    if narrative_items:
        subsections.append({
            "title": "工商深度分析",
            "items": narrative_items,
        })

    subsections.extend([
        {
            "title": "工商登记信息",
            "items": registry_items,
            "table": {
                "columns": ["项目", "登记信息"],
                "rows": registry_rows,
                "source": "巨潮资讯WebAPI / 公开工商数据",
            },
        },
        shareholder_sub,
        {"title": "关联企业与对外投资", "items": related_items[:4]},
        {"title": "异常经营/行政处罚", "items": penalty_items[:4]},
    ])
    return subsections


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


def _deepresearch_sub_reports(report_chapters: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """把 DeepResearch 报告的 ``report_chapters`` 转成渲染器可消费的 sub_reports。

    渲染器（render_report_from_template）按维度取：
    - ``report_chapters`` 用于「子报告嵌入」块（整章嵌入）；
    - ``recommendation`` / ``risk_summary`` 用于「解读位置」块。
    """

    def _as_list(value: Any) -> List[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value]
        return []

    out: Dict[str, Dict[str, Any]] = {}
    for ch in report_chapters or []:
        cid = ch.get("id")
        if not cid:
            continue
        summary = _as_list(ch.get("summary"))
        out[cid] = {
            "report_chapters": [ch],
            "recommendation": "\n".join(summary[:2]) if summary else None,
            "risk_summary": _as_list(ch.get("risks")),
        }
    return out


def _deepresearch_financial_indicators(fin_sub_report: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """从 DeepResearch 财务章节文本中抽可绑定指标值，供模板指标位使用。"""
    if not fin_sub_report:
        return {}
    from app.template.renderer import _find_indicator_in_text

    texts: List[str] = []
    for ch in fin_sub_report.get("report_chapters", []) or []:
        texts.append(" ".join(str(s) for s in (ch.get("summary") or [])))
        for sub in ch.get("subsections", []) or []:
            items = sub.get("items") if isinstance(sub, dict) else None
            if isinstance(items, list):
                texts.append(" ".join(str(i) for i in items))
    text = " ".join(texts)
    labels = ["营业收入", "净利润", "资产负债率", "毛利率", "净利率", "经营活动现金流净额", "流动比率", "营收增速"]
    out: Dict[str, str] = {}
    for label in labels:
        val = _find_indicator_in_text(label, text)
        if val:
            out[label] = val
    return out


def synthesize_research_report(state: ResearchState, template: Any = None) -> Dict[str, Any]:
    tasks = state.get("tasks", [])
    claims = state.get("claims", [])
    gaps = state.get("gaps", [])
    evidence = state.get("evidence", [])
    # 风险评分仅依据规则反射的确定性 gaps；排除 Sequential Thinking MCP 注入的
    # advisory gaps（source=sequential_thinking_mcp），其非确定性会导致 risk_rating 漂移
    rule_gaps = [gap for gap in gaps if gap.get("source") != "sequential_thinking_mcp"]
    high_gaps = [gap for gap in rule_gaps if gap.get("severity") == "high"]
    enterprise_name = state.get("enterprise_name")
    blueprint = (state.get("planner") or {}).get("metadata", {}).get("blueprint", {})
    financial_gaps = [gap for gap in rule_gaps if gap.get("task_id") and "financial" in gap.get("task_id", "")]
    legal_gaps = [gap for gap in rule_gaps if gap.get("task_id") and "legal" in gap.get("task_id", "")]
    business_gaps = [gap for gap in rule_gaps if gap.get("task_id") and ("business" in gap.get("task_id", "") or "identity" in gap.get("task_id", ""))]
    industry_gaps = [gap for gap in rule_gaps if gap.get("task_id") and "industry" in gap.get("task_id", "")]

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

    relationship_findings_rows = relationship_findings(evidence) or claim_findings(
        claims, tasks, "relationship", "未获取到股权、担保与关联网络数据，需人工核验关联关系。"
    )
    relationship_report: Dict[str, Any] = {}
    for item in evidence:
        r = ((item.get("metadata") or {}).get("relationship_analysis_report") or {})
        if r:
            relationship_report = r
            break
    if relationship_report:
        rsum = relationship_report.get("summary") or {}
        relationship_summary = [
            f"实际控制人：{rsum.get('实际控制人')}",
            f"对外担保 {rsum.get('对外担保笔数')} 笔、股权冻结 {rsum.get('股权冻结项')} 项、关联方 {rsum.get('关联方数量')} 个",
            f"关联风险评级：{relationship_report.get('risk_rating')}",
        ]
    else:
        relationship_summary = ["未获取到关联网络数据，需人工核验股权、担保与关联关系。"]
    relationship_refs = refs_for_category(evidence, "relationship")

    sentiment_findings_rows = sentiment_findings(evidence) or claim_findings(
        claims, tasks, "sentiment", "未获取到企业舆情数据，需人工监测公开信息与权威源。"
    )
    sentiment_report: Dict[str, Any] = {}
    for item in evidence:
        r = ((item.get("metadata") or {}).get("sentiment_analysis_report") or {})
        if r:
            sentiment_report = r
            break
    if sentiment_report:
        ssum = sentiment_report.get("summary") or {}
        sentiment_summary = [
            f"检索舆情 {ssum.get('检索结果')} 条，负面 {ssum.get('负面')} 条（权威源 {ssum.get('权威源负面')} 条）",
            f"声誉风险评级：{sentiment_report.get('risk_rating')}",
        ]
    else:
        sentiment_summary = ["未获取到企业舆情数据，需人工监测公开信息与权威源。"]
    sentiment_refs = refs_for_category(evidence, "sentiment")

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
            subsections=_business_subsections(evidence, business_summary, business_gaps),
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
            subsections=_industry_subsections(evidence, industry_summary, industry_gaps),
            risks=_gap_descriptions(industry_gaps),
        ),
        _chapter(
            "legal",
            "六、司法与合规风险",
            "裁判文书、被执行/失信、行政处罚、监管问询/公告与重大舆情",
            legal_summary,
            legal_refs,
            legal_findings,
            subsections=_legal_subsections(evidence, legal_summary, legal_gaps),
            risks=_gap_descriptions(legal_gaps),
        ),
        _chapter(
            "relationship",
            "七、关联网络与关联交易",
            "股权结构、实际控制人、对外担保/质押、股权冻结与上下游供应链位置",
            relationship_summary,
            relationship_refs,
            relationship_findings_rows,
        ),
        _chapter(
            "sentiment",
            "八、舆情与声誉风险",
            "公开舆情、监管处罚、声誉风险信号与权威源负面线索",
            sentiment_summary,
            sentiment_refs,
            sentiment_findings_rows,
        ),
        _chapter(
            "risks",
            "九、交叉验证与重大风险",
            "财务与经营范围、现金流与利润、司法风险与授信安全边界、行业周期与还款来源",
            [item["conclusion"] for item in cross_findings],
            all_core_refs,
            cross_findings,
            subsections=_cross_validation_subsections(
                evidence, cross_findings, financial_score, legal_score, industry_score
            ),
        ),
        _chapter(
            "credit",
            "十、信贷方案建议",
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
            "十一、证据链与待补充材料",
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

    # P1 修复：剔除章节内引用了不存在 evidence ID 的 evidence_refs
    report_chapters = sanitize_chapter_refs(report_chapters, evidence)

    # 多意图槽位：把用户输入的配置（时间窗口/深度/对比/细分/授信假设/材料/格式）
    # 落为报告级 research_config，供前端渲染与下游消费（brief/slides 等）。
    _slots = state.get("slots") or (state.get("parsed_intent") or {}).get("slots") or {}
    research_config = {
        "depth": _slots.get("depth"),
        "time_window": _slots.get("time_window"),
        "comparison": _slots.get("comparison"),
        "industry_segment": _slots.get("industry_segment"),
        "credit_assumptions": _slots.get("credit_assumptions"),
        "has_on_site_materials": _slots.get("has_on_site_materials"),
        "output_format": _slots.get("output_format"),
    }

    report = {
        "report_type": "deepresearch_due_diligence",
        "enterprise_name": enterprise_name,
        "objective": state.get("objective"),
        "risk_rating": risk_rating,
        "risk_score": weighted_score,
        "recommendation": f"建议{suggestion}。正式授信前需补齐高优先级证据缺口，并以权威工商、司法、财报和客户原始材料复核。",
        "executive_summary": summary,
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
        "research_config": research_config,
        "data_boundary": "本报告由智能尽调 DeepResearch 引擎基于公开资料、知识库和本地工具生成。公开搜索结果仅作为线索，正式授信前需结合权威工商、司法、财报和客户原始材料人工复核。",
        "timeline": state.get("timeline", []),
    }

    # 非功能需求①：把用户上传模板也用于 DeepResearch 综合报告（与财务增强 DD 报告一致）。
    # 模板章节按用户上传结构组织，并嵌入对应维度的专项结论、指标与解读位置。
    if template is not None:
        from app.template.models import ReportTemplate
        from app.template.renderer import render_report_from_template

        tpl = template if isinstance(template, ReportTemplate) else ReportTemplate.model_validate(template)
        dr_sub_reports = _deepresearch_sub_reports(report_chapters)
        dr_indicators = _deepresearch_financial_indicators(dr_sub_reports.get("financial"))
        report["template_sections"] = render_report_from_template(
            tpl, dr_sub_reports, indicators=dr_indicators, overall_summary=summary,
        )
        report["template"] = {"id": tpl.id, "name": tpl.name, "is_active": tpl.is_active}

    return report
