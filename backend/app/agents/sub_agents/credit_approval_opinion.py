"""信审审批意见生成器（确定性决策骨架）。

复用 knowledge_base/credit_guides/credit_decision_policy.md 与
bank_policy_references/credit_approval_wording_reference.md 的分层逻辑，
将工商/财务/流水核验/五看等结论收敛为信审经理可用的审批意见：

    decision（建议准入 / 谨慎准入 / 有条件初步准入 / 暂缓准入）
    + 授信条件（额度/期限/担保/用途监管）
    + 风险定价建议
    + 人工复核清单

本模块为确定性骨架（不依赖 LLM）：按规则触发分层结论与条件清单；
LLM 自然语言润色可在上层叠加，缺失时仍给出可复核的结构化审批意见。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# 决策分层（对应 credit_decision_policy.md）。
DECISION_ADMIT = "建议准入"
DECISION_CAUTIOUS = "谨慎准入"
DECISION_CONDITIONAL = "有条件初步准入"
DECISION_DEFER = "暂缓准入"


def _safe(v: Any, suffix: str = "") -> str:
    if v is None:
        return "[需补充]"
    return f"{v}{suffix}" if suffix else str(v)


def build_credit_approval_opinion(
    enterprise_name: str,
    financial_metrics: Optional[Dict[str, Any]] = None,
    flow_reconciliation: Optional[Dict[str, Any]] = None,
    five_see: Optional[Dict[str, Any]] = None,
    risk_signals: Optional[List[str]] = None,
    industry_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """生成确定性审批意见。

    Args:
        enterprise_name: 企业名称
        financial_metrics: 关键财务指标（资产负债率/经营现金流/ROE 等）
        flow_reconciliation: 流水×年报核验结果
        five_see: 五看分析结果
        risk_signals: 额外风险信号列表
        industry_context: 行业上下文
    """
    financial_metrics = financial_metrics or {}
    flow_reconciliation = flow_reconciliation or {}
    five_see = five_see or {}
    risk_signals = list(risk_signals or [])
    industry_context = industry_context or {}

    decision = DECISION_CAUTIOUS
    reasons: List[str] = []

    debt_ratio = financial_metrics.get("debt_ratio")
    ocf = financial_metrics.get("operating_cash_flow")
    roe = financial_metrics.get("roe")

    # 触发「暂缓准入」的硬信号
    defer_triggers: List[str] = []
    for flag in flow_reconciliation.get("red_flags", []):
        if flag.get("severity") == "high":
            defer_triggers.append(f"流水风险信号（{flag.get('type')}）：{flag.get('detail', '')}")
    if ocf is not None and ocf < 0:
        defer_triggers.append("经营活动现金流持续为负，第一还款来源造血不足。")
    if debt_ratio is not None and debt_ratio > 0.85:
        defer_triggers.append(f"资产负债率 {debt_ratio:.1%} 过高，偿债压力过大。")

    # 触发「谨慎准入」的中风险信号
    cautious_triggers: List[str] = []
    if flow_reconciliation.get("status") == "mismatch":
        cautious_triggers.append("银行流水与年报交叉核验存在未解释差异，财务真实性需穿透。")
    if debt_ratio is not None and debt_ratio > 0.70:
        cautious_triggers.append(f"资产负债率 {debt_ratio:.1%} 偏高（>70%）。")
    if roe is not None and roe < 0.03:
        cautious_triggers.append(f"ROE {roe:.1%} 偏低，主业盈利对风险覆盖不足。")
    if five_see:
        for dim in five_see.get("five_see", {}).values():
            cautious_triggers.extend(dim.get("risk_signals", [])[:1])

    if defer_triggers:
        decision = DECISION_DEFER
        reasons.extend(defer_triggers)
    elif cautious_triggers:
        decision = DECISION_CAUTIOUS
        reasons.extend(cautious_triggers[:4])
    else:
        decision = DECISION_ADMIT
        reasons.append("财务与流水核验未发现重大风险信号，基本面稳健。")

    # 数据缺口 → 倾向「有条件初步准入 / 审批前置条件」
    data_gaps: List[str] = []
    if not financial_metrics:
        data_gaps.append("未提供任何财务指标，无法测算偿债与盈利能力，需补充近三年财报。")
    if flow_reconciliation.get("status") == "skipped":
        data_gaps.append("未提供银行流水，营收与资金真实性无法交叉核验。")
    five_see_gaps = []
    for dim in five_see.get("five_see", {}).values():
        five_see_gaps.extend(dim.get("data_gap", []))
    data_gaps.extend(five_see_gaps)
    if data_gaps:
        # 关键信息缺口时，即便无硬风险也降级为有条件初步准入。
        if decision == DECISION_ADMIT:
            decision = DECISION_CONDITIONAL
            reasons.append("主体与财务基本正常，但存在数据缺口，建议转有条件初步准入。")

    # 授信条件（复用 credit_decision_policy 风控措施）
    conditions: List[str] = []
    if decision in (DECISION_CAUTIOUS, DECISION_CONDITIONAL):
        conditions = [
            "控制首笔额度，期限与经营周转周期匹配，分批提款、到期复核。",
            "落实实际控制人及配偶连带责任保证。",
            "土地/厂房/设备/应收账款抵质押，降低抵押率并补充评估与保险。",
            "回款账户监管 + 受托支付，资金用途闭环管理。",
            "核心客户回款监控，限制对外担保、分红与关联交易。",
        ]
    elif decision == DECISION_DEFER:
        conditions = ["暂缓新增授信，待财务真实性、司法执行状态、资金用途与风险缓释明确后重新审议。"]
    else:
        conditions = ["落实约定担保、资金用途监管与贷后监控要求后予以准入。"]

    # 风险定价建议（确定性经验映射）
    pricing_map = {
        DECISION_ADMIT: "可按基准及以下定价，信用溢价从低。",
        DECISION_CONDITIONAL: "按基准定价，视补充材料核减溢价。",
        DECISION_CAUTIOUS: "较基准上浮，体现风险溢价；强担保可适度下修。",
        DECISION_DEFER: "暂不适用（暂缓准入）。",
    }

    manual_review = list(data_gaps)
    manual_review.append("本行正式审批话术与授权格式需人工复核。")
    manual_review.append("审查意见是否覆盖客户、用途、还款、风险、缓释五要素。")
    manual_review.append("是否触碰行业、监管或内部政策红线。")

    return {
        "success": True,
        "enterprise_name": enterprise_name,
        "decision": decision,
        "reasons": reasons,
        "conditions": conditions,
        "risk_pricing": pricing_map.get(decision, pricing_map[DECISION_CAUTIOUS]),
        "data_gaps": data_gaps,
        "manual_review": manual_review,
        "summary": (
            f"审批意见（{enterprise_name}）：{decision}。"
            + ("主要依据：" + "；".join(reasons[:2]) if reasons else "")
        ),
    }
