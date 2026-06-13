"""Rule-based evidence-gap detection."""

from __future__ import annotations

from typing import Any, Dict, List

from .state import ResearchGap, ResearchTask, stable_id


def reflect_task_gaps(task: ResearchTask, evidence: List[Dict[str, Any]]) -> List[ResearchGap]:
    gaps: List[ResearchGap] = []
    task_id = task.get("id", "")
    category = task.get("category", "general")
    if not evidence:
        gaps.append({
            "id": stable_id("gap", task_id, "no_evidence"),
            "task_id": task_id,
            "description": f"未获得“{task.get('question')}”所需证据。",
            "why_it_matters": "缺少证据会导致尽调结论无法被审查人员复核。",
            "suggested_next_actions": [f"补充：{item}" for item in task.get("required_evidence", [])[:5]],
            "severity": "high",
        })
        return gaps

    high_trust = [item for item in evidence if item.get("trust_level") == "high" or item.get("reliability") == "high"]
    if not high_trust:
        gaps.append({
            "id": stable_id("gap", task_id, "no_high_trust"),
            "task_id": task_id,
            "description": "当前证据主要来自公开搜索或中低可信来源，缺少权威来源。",
            "why_it_matters": "公开搜索只能作为线索，正式授信前需权威数据源复核。",
            "suggested_next_actions": ["接入权威数据源", "人工核验公开来源", "补充客户原始材料"],
            "severity": "medium",
        })

    if category == "financial" and not any(item.get("source_type") in {"financial_statement", "uploaded_private_file"} for item in evidence):
        gaps.append({
            "id": stable_id("gap", task_id, "missing_financial_statement"),
            "task_id": task_id,
            "description": "未取得近三年三大表或正式财报结构化数据。",
            "why_it_matters": "财务真实性、偿债能力和还款来源无法仅凭公开网页线索确认。",
            "suggested_next_actions": ["上传近三年审计报告或三大表", "接入巨潮/交易所/财报结构化数据源"],
            "severity": "high",
        })

    if category == "legal" and not any(item.get("source_type") == "official_or_authoritative_public_source" for item in evidence):
        gaps.append({
            "id": stable_id("gap", task_id, "missing_legal_authority"),
            "task_id": task_id,
            "description": "司法合规线索未命中法院、执行、信用中国或交易所公告等高可信来源。",
            "why_it_matters": "司法风险会直接影响授信安全边界，需权威渠道复核。",
            "suggested_next_actions": ["查询裁判文书/执行公开源", "查询信用中国", "核验上市公司公告"],
            "severity": "medium",
        })
    return gaps

