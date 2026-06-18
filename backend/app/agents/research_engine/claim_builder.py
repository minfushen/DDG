"""Build auditable claims from research-task evidence."""

from __future__ import annotations

from typing import Any, Dict, List

from app.agents.evidence.source_intelligence import summarize_extracted_fields

from .state import ResearchClaim, ResearchTask, stable_id


def _avg_confidence(evidence: List[Dict[str, Any]]) -> float:
    values = [float(item.get("confidence", 0.55)) for item in evidence if isinstance(item.get("confidence"), (int, float))]
    if not values:
        return 0.45
    return round(sum(values) / len(values), 2)


def _risk_level(category: str, confidence: float, evidence: List[Dict[str, Any]]) -> str:
    if not evidence or confidence < 0.5:
        return "high"
    if any(item.get("requires_manual_review") for item in evidence):
        return "medium"
    if category in {"legal", "financial"} and confidence < 0.75:
        return "medium"
    return "low"


def _financial_claim_text(task: ResearchTask, evidence: List[Dict[str, Any]]) -> str | None:
    for item in evidence:
        report = ((item.get("metadata") or {}).get("financial_analysis_report") or {})
        if not report:
            continue
        metrics = report.get("key_metrics") or {}
        narrative = report.get("narrative_summary") or []
        latest_year = metrics.get("latest_year") or (report.get("years") or ["最新年度"])[-1]
        source = report.get("narrative_source") or "规则+结构化指标"
        head = (
            f"财务专项基于{report.get('generated_from', '公开财报')}形成{report.get('risk_rating', '风险待定')}判断"
            f"（{report.get('risk_score', '评分待定')}分）：{latest_year}年营业收入{metrics.get('revenue', '不可用')}，"
            f"净利润{metrics.get('net_profit', '不可用')}，毛利率{metrics.get('gross_margin', '不可用')}，"
            f"净利率{metrics.get('net_margin', '不可用')}，资产负债率{metrics.get('debt_ratio', '不可用')}，"
            f"经营活动现金流{metrics.get('operating_cash_flow', '不可用')}。"
        )
        if narrative:
            return f"{head}{narrative[0]}（财务叙述来源：{source}）"
        return head
    return None


def _industry_claim_text(task: ResearchTask, evidence: List[Dict[str, Any]]) -> str | None:
    for item in evidence:
        report = ((item.get("metadata") or {}).get("industry_analysis_report") or {})
        if not report:
            continue
        industry = report.get("industry") or {}
        summary = report.get("industry_diagnostic_summary") or report.get("risk_summary") or []
        source = report.get("industry_diagnostic_source") or "规则+知识库"
        head = (
            f"行业专项识别为{industry.get('semantic_industry_name') or industry.get('name') or '待确认行业'}，"
            f"标准路径为{' > '.join(industry.get('path') or []) or '待确认'}；"
            f"诊断来源：{source}。"
        )
        if summary:
            return f"{head}{summary[0]}"
        return head
    for item in evidence:
        public_info = ((item.get("metadata") or {}).get("public_info") or {})
        if not public_info:
            continue
        basic = public_info.get("basic_info") or {}
        main_business = public_info.get("main_business_composition") or []
        top_items = [
            f"{row.get('item_name')}收入占比{row.get('income_ratio')}、毛利率{row.get('gross_margin')}"
            for row in main_business[:3]
            if row.get("item_name")
        ]
        business_review = public_info.get("annual_business_review") or {}
        review = business_review.get("business_review") or ""
        text = (
            f"行业与经营专项已获取上市公司公开资料包：公司主营为{basic.get('main_business') or '待复核'}；"
            f"主营构成{('；'.join(top_items)) if top_items else '尚需进一步拆分'}。"
        )
        if review:
            text += f"年报经营讨论提示：{review[:180]}。"
        return text
    return None


def _business_claim_text(task: ResearchTask, evidence: List[Dict[str, Any]]) -> str | None:
    field_evidence = [
        item for item in evidence
        if item.get("trust_level") in {"high", "medium"}
        or item.get("source_type") in {"official_business_registry", "official_credit_publicity", "commercial_business_data", "official_named_source"}
    ]
    extracted = summarize_extracted_fields(field_evidence, "business_fields")
    fields = extracted.get("fields") or {}
    if fields:
        parts = []
        for field in ["统一社会信用代码", "法定代表人", "注册资本", "经营状态", "成立日期", "经营范围"]:
            if fields.get(field):
                parts.append(f"{field}：{fields[field]}")
        high_count = len([item for item in field_evidence if item.get("trust_level") == "high"])
        prefix = "工商专项已从工商/信用类公开来源抽取" if high_count else "工商专项仅从中可信工商类来源抽取"
        return f"{prefix}{len(fields)}个主体字段，其中高可信来源{high_count}项；" + "；".join(parts[:6]) + "。"
    high = [item for item in evidence if item.get("trust_level") == "high"]
    if high:
        top = high[0]
        return f"工商专项命中高可信公开来源：{top.get('claim') or top.get('value') or top.get('source_name')}，但结构化字段仍需进一步核验。"
    return None


def _legal_claim_text(task: ResearchTask, evidence: List[Dict[str, Any]]) -> str | None:
    signal_counts: Dict[str, int] = {}
    case_numbers: List[str] = []
    amounts: List[str] = []
    high_count = 0
    for item in evidence:
        if item.get("trust_level") == "high":
            high_count += 1
        signals = (((item.get("metadata") or {}).get("extracted_fields") or {}).get("legal_signals") or {})
        for signal in signals.get("signal_types") or []:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        case_numbers.extend(signals.get("case_numbers") or [])
        amounts.extend(signals.get("amounts") or [])
    case_numbers = list(dict.fromkeys(case_numbers))[:3]
    amounts = list(dict.fromkeys(amounts))[:3]
    if signal_counts or case_numbers:
        signal_text = "、".join(f"{key}{value}条" for key, value in signal_counts.items()) or "司法线索待分类"
        extras = []
        if case_numbers:
            extras.append(f"案号示例：{'、'.join(case_numbers)}")
        if amounts:
            extras.append(f"金额线索：{'、'.join(amounts)}")
        return f"司法专项检索形成{len(evidence)}项证据，其中高可信来源{high_count}项，识别到{signal_text}。{'；'.join(extras)}"
    return None


def _evidence_based_claim_text(task: ResearchTask, evidence: List[Dict[str, Any]]) -> str | None:
    category = task.get("category", "general")
    if category == "financial":
        return _financial_claim_text(task, evidence)
    if category == "industry":
        return _industry_claim_text(task, evidence)
    if category == "business":
        return _business_claim_text(task, evidence)
    if category == "legal":
        return _legal_claim_text(task, evidence)
    authoritative = [item for item in evidence if item.get("trust_level") == "high" or item.get("reliability") == "high"]
    top = authoritative[0] if authoritative else (evidence[0] if evidence else None)
    if not top:
        return None
    claim = top.get("claim") or top.get("value") or top.get("label")
    if claim:
        return f"关于“{task.get('question')}”，当前关键证据显示：{claim}"
    return None


def build_claim_for_task(enterprise_name: str, task: ResearchTask, evidence: List[Dict[str, Any]]) -> ResearchClaim:
    evidence_ids = [item.get("id") for item in evidence if item.get("id")]
    confidence = _avg_confidence(evidence)
    category = task.get("category", "general")
    if evidence_ids:
        text = _evidence_based_claim_text(task, evidence) or f"关于“{task.get('question')}”已获得{len(evidence_ids)}项证据，当前可形成初步判断；正式结论仍需结合证据可信度和人工复核。"
    else:
        text = f"关于“{task.get('question')}”尚未获得可用证据，无法形成稳定结论。"
    missing = [] if evidence_ids else list(task.get("required_evidence", []))
    requires_review = not evidence_ids or any(item.get("requires_manual_review") for item in evidence)
    return {
        "id": stable_id("cl", task.get("id"), text, evidence_ids),
        "task_id": task.get("id", ""),
        "text": text,
        "evidence_ids": evidence_ids,
        "confidence": confidence,
        "risk_level": _risk_level(category, confidence, evidence),
        "missing_evidence": missing,
        "requires_manual_review": requires_review,
    }
