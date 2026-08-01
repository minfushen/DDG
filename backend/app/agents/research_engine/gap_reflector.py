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

    if category == "financial" and not any(
        item.get("source_type") in {"financial_statement", "uploaded_private_file"}
        or (item.get("source_type") == "exchange_announcement"
            and str(item.get("label", "")).startswith("年报PDF-三大表覆盖度")
            and str(item.get("value", "")) != "0/3")
        or (item.get("source_type") == "internal_knowledge_base"
            and any(kw in str(item.get("label", "") or "") + str(item.get("value", "") or "")
            for kw in ["年报", "年度报告", "三大表", "审计报告", "财务报表"]))
        for item in evidence
    ):
        gaps.append({
            "id": stable_id("gap", task_id, "missing_financial_statement"),
            "task_id": task_id,
            "description": "未取得近三年三大表或正式财报结构化数据。",
            "why_it_matters": "财务真实性、偿债能力和还款来源无法仅凭公开网页线索确认。",
            "suggested_next_actions": ["上传近三年审计报告或三大表", "接入巨潮/交易所/财报结构化数据源"],
            "severity": "high",
        })

    provider_diff_evidence = [item for item in evidence if item.get("source_type") == "financial_provider_reconciliation"]
    if category == "financial" and provider_diff_evidence:
        gaps.append({
            "id": stable_id("gap", task_id, "financial_provider_reconciliation_mismatch"),
            "task_id": task_id,
            "description": f"公开结构化财报数据源之间存在{len(provider_diff_evidence)}项超阈值差异。",
            "why_it_matters": "跨源财务数据不一致会影响偿债指标、利润质量和授信额度测算，需以巨潮/交易所原始公告或审计报告复核。",
            "suggested_next_actions": ["回查巨潮/交易所原始年报PDF", "核对审计报告附注和财务报表项目口径", "必要时要求客户提供盖章版三大表"],
            "severity": "medium",
            "evidence_refs": [item.get("id") for item in provider_diff_evidence if item.get("id")][:8],
        })

    # 财务专项：缺同业财务对标（影响指标横比和行业定位判断）
    if category == "financial":
        _financial_text = " ".join(
            str(item.get("label", "")) + str(item.get("value", "")) + str(item.get("claim", ""))
            for item in evidence
        )
        if not any(kw in _financial_text for kw in ["同业", "对标", "行业均值", "行业平均", "横比", "可比公司"]):
            gaps.append({
                "id": stable_id("gap", task_id, "missing_financial_peer_benchmark"),
                "task_id": task_id,
                "description": "未取得同业财务对标数据，无法判断指标在行业中的相对水平。",
                "why_it_matters": "毛利率、资产负债率、周转率等指标缺乏行业横比时，难以判断是否偏离行业常态。",
                "suggested_next_actions": ["检索同行业可比公司财报摘要", "获取行业均值或分位数数据"],
                "severity": "medium",
            })

    # 财务专项：缺审计意见（影响财报可信度判断）
    if category == "financial":
        _audit_text = " ".join(
            str(item.get("label", "")) + str(item.get("value", "")) + str(item.get("claim", ""))
            for item in evidence
        )
        if not any(kw in _audit_text for kw in ["审计意见", "审计报告", "标准无保留", "非标", "保留意见", "强调事项"]):
            gaps.append({
                "id": stable_id("gap", task_id, "missing_audit_opinion"),
                "task_id": task_id,
                "description": "未取得审计意见类型，无法确认财报审计结论。",
                "why_it_matters": "非标审计意见（保留、无法表示、否定）会直接影响授信准入判断。",
                "suggested_next_actions": ["回查年报审计意见段落", "核实是否为标准无保留意见"],
                "severity": "medium",
            })

    # 行业专项：缺主营构成/产品收入占比（影响细分赛道锚定）
    if category == "industry":
        _has_main_business = any(
            item.get("source_type") == "listed_company_public_info"
            and any(kw in str(item.get("label", "")) + str(item.get("value", ""))
                    for kw in ["主营构成", "主营业务", "产品收入", "收入占比", "产品结构"])
            for item in evidence
        )
        if not _has_main_business:
            gaps.append({
                "id": stable_id("gap", task_id, "missing_industry_main_business"),
                "task_id": task_id,
                "description": "未取得主营构成或产品收入占比，无法精确锚定细分赛道。",
                "why_it_matters": "主营构成决定行业归类和风险传导路径，缺失会导致行业诊断泛化。",
                "suggested_next_actions": ["检索年报主营构成章节", "获取产品收入占比明细"],
                "severity": "high",
            })

    # 行业专项：缺同业对标/竞争格局数据（影响行业地位判断）
    if category == "industry":
        _peer_text = " ".join(
            str(item.get("label", "")) + str(item.get("value", "")) + str(item.get("claim", ""))
            for item in evidence
        )
        if not any(kw in _peer_text for kw in ["同业", "对标", "竞争格局", "市场份额", "市占率", "可比公司", "行业地位", "龙头", "排名"]):
            gaps.append({
                "id": stable_id("gap", task_id, "missing_industry_peer_benchmark"),
                "task_id": task_id,
                "description": "未取得同业对标或竞争格局数据，无法判断公司在行业中的相对地位。",
                "why_it_matters": "行业地位直接影响议价能力、经营韧性和授信安全边界。",
                "suggested_next_actions": ["检索行业研报竞争格局章节", "获取同业上市公司对比数据"],
                "severity": "medium",
            })

    # 行业专项：缺行业 KPI（影响景气度和经营效率量化判断）
    if category == "industry":
        _kpi_text = " ".join(
            str(item.get("label", "")) + str(item.get("value", "")) + str(item.get("claim", ""))
            for item in evidence
        )
        if not any(kw in _kpi_text for kw in ["产能", "利用率", "良率", "市占率", "市场份额", "渗透率", "复合增速", "行业增速", "行业KPI", "行业指标"]):
            gaps.append({
                "id": stable_id("gap", task_id, "missing_industry_kpi"),
                "task_id": task_id,
                "description": "未取得行业关键指标（KPI），无法量化行业景气度和经营效率。",
                "why_it_matters": "产能利用率、良率、市占率等行业 KPI 是判断经营韧性和周期位置的核心依据。",
                "suggested_next_actions": ["检索行业研报关键指标", "获取产能利用率或良率或市占率数据"],
                "severity": "medium",
            })

    # 行业专项：缺行业诊断报告（说明行业 Agent 未产出结构化诊断）
    if category == "industry" and not any(item.get("source_type") == "industry_diagnostic_report" for item in evidence):
        gaps.append({
            "id": stable_id("gap", task_id, "missing_industry_diagnostic"),
            "task_id": task_id,
            "description": "未生成行业专项诊断报告，行业分析结论不完整。",
            "why_it_matters": "缺少结构化行业诊断会导致授信审查缺少行业风险维度的专业判断。",
            "suggested_next_actions": ["确认行业 Agent 是否正常执行", "补充行业分类和研报数据后重试"],
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
