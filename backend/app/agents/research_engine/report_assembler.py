"""Assemble specialist agent outputs into loan due-diligence chapters."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def evidence_map(evidence: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(item.get("id")): item for item in evidence if item.get("id")}


def refs_for_category(evidence: List[Dict[str, Any]], category: str, limit: int = 5) -> List[str]:
    refs: List[str] = []
    for item in evidence:
        if item.get("domain") == category or item.get("agent") == category or item.get("category") == category:
            if item.get("id"):
                refs.append(str(item["id"]))
    return refs[:limit]


def financial_findings(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        if not report:
            continue
        report_refs = [item.get("id")] if item.get("id") else []
        codeact_refs = [ref for ref in report.get("codeact_evidence_refs") or [] if ref]
        refs = list(dict.fromkeys(codeact_refs[:8] + report_refs))
        diagnostics = (report.get("narrative_diagnostics") or {}).get("diagnostics") or []
        for row in diagnostics[:4]:
            title = row.get("title") or row.get("dimension") or "财务诊断"
            phenomenon = row.get("phenomenon") or row.get("current_anchor") or row.get("现象与归因") or ""
            driver = row.get("driver") or row.get("risk_substance") or row.get("风险实质") or ""
            actions = row.get("verification_actions") or row.get("verification_action") or row.get("核查要点") or []
            if isinstance(actions, str):
                actions = [actions]
            findings.append({
                "title": title,
                "risk_level": row.get("risk_level") or row.get("risk_label") or report.get("risk_rating") or "medium",
                "conclusion": " ".join(part for part in [phenomenon, driver] if part).strip() or title,
                "verification_actions": actions[:4],
                "missing_items": row.get("missing_items") or [],
                "evidence_refs": refs[:6],
            })
        if findings:
            return findings
        for text in (report.get("narrative_summary") or [])[:4]:
            findings.append({"title": "财务专项判断", "risk_level": report.get("risk_rating") or "medium", "conclusion": text, "evidence_refs": refs[:6]})
    return findings


def industry_findings(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for item in evidence:
        report = ((item.get("metadata") or {}).get("industry_analysis_report") or {})
        if not report:
            continue
        refs = [item.get("id")] if item.get("id") else []
        diagnostics = (report.get("industry_diagnostics") or {}).get("diagnostics") or []
        overall = (report.get("industry_diagnostics") or {}).get("overall_position") or {}
        if overall:
            findings.append({
                "title": "行业定位与周期判断",
                "risk_level": overall.get("risk_level") or "medium",
                "conclusion": overall.get("conclusion") or overall.get("position") or overall.get("summary") or "已形成行业定位判断。",
                "verification_actions": overall.get("verification_actions") or [],
                "evidence_refs": refs,
            })
        for index, row in enumerate(diagnostics[:4], 1):
            actions = row.get("verification_actions") or row.get("核查要点") or []
            if isinstance(actions, str):
                actions = [actions]
            findings.append({
                "title": row.get("title") or ["竞争格局与行业周期", "产业链与议价能力", "授信审查关注点", "政策与合规环境"][min(index - 1, 3)],
                "risk_level": row.get("risk_level") or "medium",
                "conclusion": " ".join(str(row.get(key) or "") for key in ["current_anchor", "risk_substance", "现状锚定", "风险实质"]).strip() or row.get("title") or "行业专项判断",
                "verification_actions": actions[:4],
                "missing_items": row.get("missing_items") or [],
                "evidence_refs": refs + [ref for ref in row.get("evidence_ids") or [] if ref][:3],
            })
        if findings:
            return findings
        for text in (report.get("industry_diagnostic_summary") or report.get("risk_summary") or [])[:4]:
            findings.append({"title": "行业专项判断", "risk_level": "medium", "conclusion": text, "evidence_refs": refs})
    return findings


def relationship_findings(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for item in evidence:
        report = ((item.get("metadata") or {}).get("relationship_analysis_report") or {})
        if not report:
            continue
        refs = [item.get("id")] if item.get("id") else []
        summary = report.get("summary") or {}
        findings.append({
            "title": "股权结构与实际控制人",
            "risk_level": report.get("risk_rating") or "medium",
            "conclusion": (
                f"实际控制人：{summary.get('实际控制人')}；"
                f"股东 {summary.get('股东数量')} 个；"
                f"对外担保 {summary.get('对外担保笔数')} 笔、股权冻结 {summary.get('股权冻结项')} 项。"
            ),
            "evidence_refs": refs,
        })
        for tag in report.get("risk_tags", []):
            findings.append({
                "title": tag.get("tag", "关联风险"),
                "risk_level": tag.get("level", "medium"),
                "conclusion": tag.get("detail", ""),
                "evidence_refs": refs,
            })
        if findings:
            return findings[:5]
    return []


def sentiment_findings(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for item in evidence:
        report = ((item.get("metadata") or {}).get("sentiment_analysis_report") or {})
        if not report:
            continue
        refs = [item.get("id")] if item.get("id") else []
        summary = report.get("summary") or {}
        findings.append({
            "title": "舆情概览与声誉风险",
            "risk_level": report.get("risk_rating") or "medium",
            "conclusion": (
                f"检索舆情 {summary.get('检索结果')} 条；"
                f"负面 {summary.get('负面')} 条（权威源 {summary.get('权威源负面')} 条）；"
                f"声誉风险评级 {report.get('risk_rating')}。"
            ),
            "evidence_refs": refs,
        })
        for tag in report.get("risk_tags", []):
            findings.append({
                "title": tag.get("tag", "声誉风险"),
                "risk_level": tag.get("level", "medium"),
                "conclusion": tag.get("detail", ""),
                "evidence_refs": refs,
            })
        if findings:
            return findings[:5]
    return []


def claim_findings(claims: List[Dict[str, Any]], tasks: List[Dict[str, Any]], category: str, fallback: str) -> List[Dict[str, Any]]:
    task_ids = {task.get("id") for task in tasks if task.get("category") == category}
    rows = []
    for claim in claims:
        if claim.get("task_id") in task_ids and claim.get("text"):
            rows.append({
                "title": claim.get("text", "")[:28],
                "risk_level": claim.get("risk_level") or "medium",
                "conclusion": claim.get("text"),
                "evidence_refs": claim.get("evidence_ids") or [],
                "requires_manual_review": claim.get("requires_manual_review"),
            })
    return rows[:4] or [{"title": "证据边界", "risk_level": "medium", "conclusion": fallback, "evidence_refs": []}]


def sanitize_chapter_refs(chapters: List[Dict[str, Any]], evidence: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """剔除章节内引用了不存在 evidence ID 的 evidence_refs。

    报告合成层会从财务/行业专项分析报告的嵌套元数据（codeact_evidence_refs、
    diagnostics.evidence_ids 等）回填引用，这些 ID 可能不在顶层 evidence 列表中，
    导致质量门检出“无效 evidence_refs”。本函数在报告返回前做一次统一清洗。
    """
    valid_ids = {str(item.get("id")) for item in evidence if item.get("id")}
    if not valid_ids:
        return chapters

    def _filter(refs: Any) -> List[str]:
        return [str(r) for r in (refs or []) if str(r) in valid_ids]

    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        if chapter.get("evidence_refs"):
            chapter["evidence_refs"] = _filter(chapter.get("evidence_refs"))
        for citation in chapter.get("summary_citations") or []:
            if isinstance(citation, dict):
                citation["evidence_refs"] = _filter(citation.get("evidence_refs"))
        for finding in chapter.get("findings") or []:
            if isinstance(finding, dict):
                finding["evidence_refs"] = _filter(finding.get("evidence_refs"))
        for sub in chapter.get("subsections") or []:
            if isinstance(sub, dict):
                sub["evidence_refs"] = _filter(sub.get("evidence_refs"))
    return chapters
