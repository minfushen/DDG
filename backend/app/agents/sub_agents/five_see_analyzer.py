"""授信五看分析法（确定性框架）。

口径：看行业 / 看客户 / 看产品 / 看还款来源 / 看担保（银行授信五看）。
将分散的工商、行业、财务、流水、担保信息收敛为五张结构化「看」卡片，
作为信审/风控经理快速建立客户画像与风险判断的专业框架。

本模块为确定性骨架（不依赖 LLM）：从已抽取的结构化上下文组织事实、风险信号与数据缺口；
LLM 深度研判可在上层叠加，缺失时仍给出可复核的结构化输出。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe(v: Any, suffix: str = "") -> str:
    if v is None:
        return "[需补充]"
    return f"{v}{suffix}" if suffix else str(v)


def build_five_see_analysis(
    enterprise_name: str,
    industry_context: Optional[Dict[str, Any]] = None,
    business_segments: Optional[List[Dict[str, Any]]] = None,
    business_review: Optional[str] = None,
    financial_metrics: Optional[Dict[str, Any]] = None,
    repayment: Optional[Dict[str, Any]] = None,
    guarantee: Optional[Dict[str, Any]] = None,
    risk_section: Optional[str] = None,
) -> Dict[str, Any]:
    """构建授信五看结构化卡片。

    Args:
        enterprise_name: 企业名称
        industry_context: 行业报告上下文 {"industry_name","diagnosis_summary","triggered_rules"}
        business_segments: 主营构成列表（来自年报）
        business_review: 年报经营讨论文本
        financial_metrics: 关键财务指标字典（营收/净利/负债率/经营现金流等）
        repayment: 还款来源指标（经营现金流/回款率/流水净额等）
        guarantee: 担保抵质押信息（可缺）
        risk_section: 年报风险章节原文
    """
    industry_context = industry_context or {}
    financial_metrics = financial_metrics or {}
    repayment = repayment or {}
    business_segments = business_segments or []
    business_review = (business_review or "").strip()
    risk_section = (risk_section or "").strip()

    # 一、看行业
    industry_name = industry_context.get("industry_name") or "[需补充：行业分类]"
    ind_diag = industry_context.get("diagnosis_summary") or ""
    ind_rules = industry_context.get("triggered_rules") or []
    see_industry = {
        "facts": [
            f"所属行业：{industry_name}",
            f"行业研判：{ind_diag[:200]}" if ind_diag else "行业周期与景气度：[需补充]",
        ],
        "risk_signals": [f"触发行业规则：{r}" for r in ind_rules] or ["[需补充：行业政策/周期风险信号]"],
        "data_gap": [] if ind_diag else ["缺少行业深度研判与同业基准"],
    }

    # 二、看客户（主体与实控人）
    customer_facts = [f"企业名称：{enterprise_name}"]
    customer_risks: List[str] = []
    if risk_section:
        for kw in ["实际控制人", "股权", "治理", "关联"]:
            if kw in risk_section:
                customer_risks.append(f"风险章节提及「{kw}」相关事项，需穿透实控人及关联方。")
    if not customer_risks:
        customer_risks = ["[需补充：实控人背景、股权稳定性、征信与涉诉]"]
    see_customer = {
        "facts": customer_facts,
        "risk_signals": customer_risks,
        "data_gap": ["工商股权结构、实控人征信与涉诉信息未结构化接入"],
    }

    # 三、看产品（主营构成与竞争力）
    product_facts: List[str] = []
    if business_segments:
        for seg in business_segments[:5]:
            name = seg.get("产品") or seg.get("业务") or seg.get("板块") or seg.get("name") or "未命名"
            share = seg.get("占比") or seg.get("收入占比") or seg.get("比例") or ""
            product_facts.append(f"{name}（{share}）" if share else f"{name}")
    else:
        product_facts = ["[需补充：主营产品构成与收入占比]"]
    product_risk = "[需补充：产品竞争力、集中度与毛利率趋势]" if not business_segments else "需结合毛利率与价格周期判断产品竞争力。"
    see_product = {
        "facts": product_facts,
        "risk_signals": [product_risk],
        "data_gap": [] if business_segments else ["缺少主营业务分部收入与毛利数据"],
    }

    # 四、看还款来源（第一/第二）
    ocf = repayment.get("operating_cash_flow") or financial_metrics.get("operating_cash_flow")
    rev = financial_metrics.get("revenue")
    flow_net = repayment.get("flow_net")
    ocf_cover = repayment.get("ocf_cover")
    repayment_facts = [
        f"经营现金流净额：{_safe(ocf)}",
        f"营业收入：{_safe(rev)}",
        f"流水经营性净额：{_safe(flow_net)}",
        f"经营现金流/本息覆盖：{_safe(ocf_cover)}",
    ]
    repayment_risks: List[str] = []
    if ocf is not None and ocf < 0:
        repayment_risks.append("经营活动现金流为负，第一还款来源造血不足。")
    if ocf_cover is not None and ocf_cover < 1:
        repayment_risks.append("经营现金流对贷款本息覆盖倍数不足 1 倍。")
    if not repayment_risks:
        repayment_risks = ["第一还款来源需结合回款周期与流水进一步核实。"]
    see_repayment = {
        "facts": repayment_facts,
        "risk_signals": repayment_risks,
        "data_gap": ["缺少贷款本息金额与期限，无法精确测算覆盖倍数"] if ocf_cover is None else [],
    }

    # 五、看担保（第二还款来源）
    if guarantee:
        see_guarantee = {
            "facts": [f"担保方式：{guarantee.get('type', '[需补充]')}", guarantee.get("detail", "")],
            "risk_signals": guarantee.get("risk_signals", []) or ["需评估担保物变现能力与保证人代偿能力。"],
            "data_gap": [],
        }
    else:
        see_guarantee = {
            "facts": ["[需补充：抵质押物、保证人及代偿能力]"],
            "risk_signals": ["第二还款来源尚未提供，担保强度无法评估。"],
            "data_gap": ["缺少担保合同、抵押物评估值与保证人财报"],
        }

    summary = (
        f"授信五看（{enterprise_name}）：行业={industry_name}；"
        f"主营={('、'.join(product_facts[:3]) if product_facts else '缺')}；"
        f"第一还款来源经营现金流={_safe(ocf)}；"
        f"担保={'已提供' if guarantee else '缺'}。"
    )

    return {
        "success": True,
        "enterprise_name": enterprise_name,
        "five_see": {
            "see_industry": see_industry,
            "see_customer": see_customer,
            "see_product": see_product,
            "see_repayment": see_repayment,
            "see_guarantee": see_guarantee,
        },
        "summary": summary,
    }
