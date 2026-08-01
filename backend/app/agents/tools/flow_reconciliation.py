"""银行流水 × 年报三大表 多源交叉核验引擎。

复用 ``financial_provider_reconciliation`` 的「确定性差异校验」风格，但核验对象从
「多数据源同口径报表」升级为「资金流水 vs 会计报表」，是贷前/贷后穿透式尽调的关键证据。

核验维度（详见 knowledge_base/credit_guides/bank_flow_reconciliation_rules.md）：
1. 货币资金 vs 银行账户日终余额之和（确定性最强）
2. 营业收入 vs 销售回款流水（贷方累计）
3. 经营活动现金流净额 vs 经营性收支净额
4. 其他应收款/预付 vs 关联方流水往来
5. 隐性负债与异常往来信号（红黄灯）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.tools.bank_flow_tool import (
    BankFlowData,
    classify_flow_roles,
)


# 阈值（经验值，正式授信以本行风险偏好为准）。
CASH_BALANCE_DIFF_RATE = 0.05        # 货币资金 vs 余额 差异率阈值
REVENUE_FLOW_LOW = 0.85              # 销售回款/营收 下限
REVENUE_FLOW_HIGH = 1.15             # 销售回款/营收 上限
OCF_DIFF_RATE = 0.15                 # 经营现金流 vs 流水净额 差异率阈值
RELATED_PARTY_RED_FLAG_RATE = 0.05   # 关联方往来占净资产 阈值


def _value_by_item(df, item_keywords: List[str], year: str) -> Optional[float]:
    if df is None or getattr(df, "empty", True):
        return None
    year_col = None
    for col in df.columns:
        if str(col) == str(year):
            year_col = col
            break
    if year_col is None:
        return None
    label_col = None
    for col in df.columns:
        if any(k in str(col) for k in ["项目", "科目", "指标", "名称"]):
            label_col = col
            break
    if label_col is None:
        label_col = df.columns[0]
    for _, row in df.iterrows():
        label = str(row.get(label_col, "")).replace("\n", "").replace(" ", "")
        if any(k in label for k in item_keywords):
            try:
                val = row.get(year_col)
                return float(val) if val not in (None, "") else None
            except (TypeError, ValueError):
                return None
    return None


def _latest_year(df) -> Optional[str]:
    if df is None or getattr(df, "empty", True):
        return None
    years = [str(c) for c in df.columns if str(c).isdigit() and len(str(c)) == 4]
    return sorted(years, reverse=True)[0] if years else None


def _status_for_diff(report_val: Optional[float], flow_val: float, rate: float) -> str:
    if report_val is None:
        return "missing"
    if report_val == 0:
        return "mismatch" if abs(flow_val) > 1e-6 else "consistent"
    diff_rate = abs(flow_val - report_val) / abs(report_val)
    return "consistent" if diff_rate <= rate else "mismatch"


def reconcile_flow_with_annual_report(
    bank_flow: BankFlowData,
    rebecca_data: Dict[str, Any],
    annual_report_notes: Optional[Dict[str, Any]] = None,
    net_assets: Optional[float] = None,
) -> Dict[str, Any]:
    """银行流水与年报三大表交叉核验。

    Args:
        bank_flow: 解析后的流水数据。
        rebecca_data: {"income_statement": DataFrame, "balance_sheet": DataFrame,
                        "cash_flow": DataFrame}。
        annual_report_notes: 可选，年报抽取附注（用于补充上下文）。
        net_assets: 可选，净资产（所有者权益），用于关联方往来红黄灯阈值。

    Returns:
        结构化核验结果：{check_items, red_flags, summary, status, coverage}。
    """
    if bank_flow is None or bank_flow.is_empty():
        return {
            "success": False,
            "status": "skipped",
            "reason": "未提供银行流水",
            "check_items": [],
            "red_flags": [],
            "summary": "未提供银行流水，相关核验项转为审批前置条件。",
        }

    income = rebecca_data.get("income_statement")
    balance = rebecca_data.get("balance_sheet")
    cash_flow = rebecca_data.get("cash_flow")

    year = _latest_year(balance) or _latest_year(income) or _latest_year(cash_flow)
    roles = classify_flow_roles(bank_flow)

    check_items: List[Dict[str, Any]] = []

    # 1. 货币资金 vs 账户日终余额之和
    cash_report = _value_by_item(balance, ["货币资金"], year) if year else None
    closing_sum = bank_flow.total_closing_balance()
    cash_status = _status_for_diff(cash_report, closing_sum, CASH_BALANCE_DIFF_RATE)
    check_items.append({
        "key": "cash_vs_balance",
        "label": "货币资金 vs 银行账户日终余额",
        "annual_report_value": cash_report,
        "flow_value": round(closing_sum, 2),
        "diff_rate": round(abs(closing_sum - (cash_report or 0)) / abs(cash_report), 4) if cash_report else None,
        "status": cash_status,
        "evidence": (
            f"年报货币资金={cash_report}; 主要结算账户期末余额之和={closing_sum:.0f}; "
            f"差异率阈值={CASH_BALANCE_DIFF_RATE:.0%}"
        ),
    })

    # 2. 营业收入 vs 销售回款流水
    revenue = _value_by_item(income, ["营业收入", "主营业务收入"], year) if year else None
    operating_credit = roles["operating_credit"]
    rev_ratio = (operating_credit / revenue) if revenue else None
    if revenue:
        if rev_ratio is not None and REVENUE_FLOW_LOW <= rev_ratio <= REVENUE_FLOW_HIGH:
            rev_status = "consistent"
        else:
            rev_status = "mismatch"
    else:
        rev_status = "missing"
    check_items.append({
        "key": "revenue_vs_flow",
        "label": "营业收入 vs 销售回款流水",
        "annual_report_value": revenue,
        "flow_value": round(operating_credit, 2),
        "ratio": round(rev_ratio, 4) if rev_ratio is not None else None,
        "status": rev_status,
        "evidence": (
            f"年报营业收入={revenue}; 流水销售回款贷方累计={operating_credit:.0f}; "
            f"回款/营收={rev_ratio:.2%}" if rev_ratio is not None else "年报无营业收入数据"
        ),
    })

    # 3. 经营活动现金流净额 vs 经营性收支净额
    ocf = _value_by_item(cash_flow, ["经营活动产生的现金流量净额", "经营活动现金流"], year) if year else None
    flow_ocf_net = roles["operating_credit"] - roles["operating_debit"]
    ocf_status = _status_for_diff(ocf, flow_ocf_net, OCF_DIFF_RATE)
    check_items.append({
        "key": "ocf_vs_flow_net",
        "label": "经营现金流净额 vs 经营性收支净额",
        "annual_report_value": ocf,
        "flow_value": round(flow_ocf_net, 2),
        "diff_rate": round(abs(flow_ocf_net - (ocf or 0)) / abs(ocf), 4) if ocf else None,
        "status": ocf_status,
        "evidence": (
            f"年报经营现金流净额={ocf}; 流水经营性净额(贷方-借方)={flow_ocf_net:.0f}"
        ),
    })

    # 4. 其他应收款/预付 vs 关联方流水往来
    other_receivable = _value_by_item(balance, ["其他应收款"], year) if year else None
    prepay = _value_by_item(balance, ["预付款项", "预付账款"], year) if year else None
    related_party_flow = roles["related_party_flow"]
    rp_status = "missing"
    rp_evidence = "年报无可比科目"
    if other_receivable is not None or prepay is not None:
        report_side = (other_receivable or 0) + (prepay or 0)
        # 关联方流水净额与报表其他应收/预付规模背离即预警。
        if report_side > 0:
            rp_diff = abs(related_party_flow - report_side) / report_side
            rp_status = "consistent" if rp_diff <= 0.5 else "mismatch"
        else:
            rp_status = "mismatch" if abs(related_party_flow) > 1e-6 else "consistent"
        rp_evidence = (
            f"年报其他应收+预付={report_side:.0f}; 流水关联方往来净额={related_party_flow:.0f}"
        )
    check_items.append({
        "key": "related_party_flow",
        "label": "其他应收/预付 vs 关联方流水往来",
        "annual_report_value": (other_receivable or 0) + (prepay or 0),
        "flow_value": round(related_party_flow, 2),
        "status": rp_status,
        "evidence": rp_evidence,
    })

    # 5. 隐性负债与异常往来信号（红黄灯）
    red_flags = _detect_red_flags(bank_flow, net_assets)

    # 汇总
    statuses = [c["status"] for c in check_items]
    if "mismatch" in statuses:
        overall = "mismatch"
    elif "missing" in statuses:
        overall = "partial"
    else:
        overall = "consistent"

    mismatch_count = sum(1 for c in check_items if c["status"] == "mismatch")
    consistent_count = sum(1 for c in check_items if c["status"] == "consistent")

    summary = (
        f"流水×年报交叉核验完成 {len(check_items)} 项，一致 {consistent_count} 项、"
        f"差异 {mismatch_count} 项、缺失 {sum(1 for c in check_items if c['status']=='missing')} 项；"
        f"触发风险信号 {len(red_flags)} 条。"
    )

    return {
        "success": True,
        "status": overall,
        "year": year,
        "check_items": check_items,
        "red_flags": red_flags,
        "summary": summary,
        "coverage": {
            "accounts": len(bank_flow.accounts),
            "transactions": len(bank_flow.all_transactions()),
            "total_credit": round(bank_flow.total_credit(), 2),
            "total_debit": round(bank_flow.total_debit(), 2),
            "closing_balance_sum": round(closing_sum, 2),
        },
    }


def _detect_red_flags(bank_flow: BankFlowData, net_assets: Optional[float]) -> List[Dict[str, Any]]:
    """识别隐性负债与异常往来信号。"""
    flags: List[Dict[str, Any]] = []
    txns = bank_flow.all_transactions()

    # (a) 大额、无业务背景、关联方拆借
    related_large = [
        t for t in txns
        if t.is_related_party and (t.credit >= 1e7 or t.debit >= 1e7)
        and any(k in t.summary for k in ["借款", "拆借", "往来", "代付", "垫资"])
    ]
    for t in related_large:
        sev = "high"
        if net_assets and (t.credit - t.debit) > RELATED_PARTY_RED_FLAG_RATE * net_assets:
            sev = "high"
        flags.append({
            "type": "related_party_large_flow",
            "severity": sev,
            "date": t.date,
            "counterparty": t.counterparty,
            "summary": t.summary,
            "amount": round(t.credit - t.debit, 2),
            "detail": "大额关联方资金往来，疑似资金占用或隐性负债，需穿透实控人及关联企业。",
        })

    # (b) 摘要含禁止/敏感用途关键词
    sensitive_keywords = ["房地产", "股市", "理财", "过桥", "个人卡", "备用金"]
    for t in txns:
        if any(k in t.summary for k in sensitive_keywords):
            flags.append({
                "type": "sensitive_usage",
                "severity": "medium",
                "date": t.date,
                "counterparty": t.counterparty,
                "summary": t.summary,
                "amount": round(t.credit - t.debit, 2),
                "detail": "流水摘要命中敏感用途关键词，需核实资金是否违规流入禁止领域。",
            })

    # (c) 月末规律性大额进出（冲时点粉饰余额）—— 粗略：同日多笔大额对冲
    from collections import defaultdict
    daily_net: Dict[str, float] = defaultdict(float)
    for t in txns:
        daily_net[t.date] += (t.credit - t.debit)
    for date, net in daily_net.items():
        # 同日借贷净额接近 0 但单边发生额巨大，疑似过账
        day_txns = [t for t in txns if t.date == date]
        gross = sum(max(t.credit, t.debit) for t in day_txns)
        if abs(net) < 0.1 * gross and gross >= 5e7:
            flags.append({
                "type": "window_dressing",
                "severity": "medium",
                "date": date,
                "counterparty": "",
                "summary": "同日大额借贷净额接近零",
                "amount": round(gross, 2),
                "detail": "疑似月末冲时点、粉饰账户余额，需核查资金真实用途与停留时长。",
            })

    return flags
