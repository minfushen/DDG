"""Structured financial data package for stable diagnosis and rendering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import math


NumberSeries = Dict[str, Optional[float]]


METRIC_LABELS = {
    "revenue": "营业收入",
    "cost": "营业成本",
    "gross_profit": "营业毛利润",
    "net_profit": "净利润",
    "deducted_net_profit": "扣非净利润",
    "operating_cashflow": "经营活动现金流量净额",
    "investing_cashflow": "投资活动现金流量净额",
    "financing_cashflow": "筹资活动现金流量净额",
    "total_assets": "总资产",
    "total_liabilities": "总负债",
    "cash": "货币资金",
    "short_loan": "短期借款",
    "short_debt": "短期有息债务",
    "receivable": "应收账款",
    "inventory": "存货",
    "gross_margin": "毛利率",
    "net_margin": "销售净利率",
    "debt_ratio": "资产负债率",
    "current_ratio": "流动比率",
    "quick_ratio": "速动比率",
    "cash_to_short_debt": "现金短债比",
    "ebitda_interest_coverage": "EBITDA利息保障倍数",
    "receivable_turnover_days": "应收账款周转天数",
    "inventory_turnover_days": "存货周转天数",
    "roe": "ROE",
    "roa": "ROA",
}

AMOUNT_METRICS = {
    "revenue",
    "cost",
    "gross_profit",
    "net_profit",
    "deducted_net_profit",
    "operating_cashflow",
    "investing_cashflow",
    "financing_cashflow",
    "total_assets",
    "total_liabilities",
    "cash",
    "short_loan",
    "short_debt",
    "receivable",
    "inventory",
}

PERCENT_METRICS = {"gross_margin", "net_margin", "debt_ratio", "roe", "roa"}
RATIO_METRICS = {"current_ratio", "quick_ratio", "cash_to_short_debt", "ebitda_interest_coverage"}
DAY_METRICS = {"receivable_turnover_days", "inventory_turnover_days"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _fmt_amount(value: Optional[float]) -> str:
    if not _is_number(value):
        return "数据不可用"
    value = float(value)  # type: ignore[arg-type]
    abs_value = abs(value)
    if abs_value >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿元"
    if abs_value >= 10_000:
        return f"{value / 10_000:.2f}万元"
    return f"{value:.2f}元"


def _fmt_percent(value: Optional[float]) -> str:
    if not _is_number(value):
        return "数据不可用"
    return f"{float(value) * 100:.2f}%"


def _fmt_ratio(value: Optional[float]) -> str:
    if not _is_number(value):
        return "数据不可用"
    return f"{float(value):.2f}"


def _fmt_days(value: Optional[float]) -> str:
    if not _is_number(value):
        return "数据不可用"
    return f"{float(value):.1f}天"


def _display_value(metric_key: str, value: Optional[float]) -> str:
    if metric_key in AMOUNT_METRICS:
        return _fmt_amount(value)
    if metric_key in PERCENT_METRICS:
        return _fmt_percent(value)
    if metric_key in DAY_METRICS:
        return _fmt_days(value)
    if metric_key in RATIO_METRICS:
        return _fmt_ratio(value)
    return _fmt_ratio(value)


def _series_from_metrics(metrics_by_year: Dict[str, Any], metric_key: str, years: List[str]) -> NumberSeries:
    return {
        year: (metrics_by_year.get(year) or {}).get(metric_key)
        for year in years
    }


def _growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if not _is_number(current) or not _is_number(previous) or float(previous) == 0:
        return None
    return (float(current) - float(previous)) / abs(float(previous))


def _trend(values: NumberSeries, years: List[str]) -> str:
    present = [values.get(year) for year in years if _is_number(values.get(year))]
    if len(present) < 2:
        return "数据不足"
    deltas = [float(present[index]) - float(present[index - 1]) for index in range(1, len(present))]
    if all(delta > 0 for delta in deltas):
        return "持续增长"
    if all(delta < 0 for delta in deltas):
        return "持续下降"
    if all(abs(delta) < 1e-9 for delta in deltas):
        return "基本稳定"
    if len(present) >= 3 and present[1] < present[0] and present[-1] > present[1]:
        return "先降后升"
    if len(present) >= 3 and present[1] > present[0] and present[-1] < present[1]:
        return "先升后降"
    return "波动上升" if present[-1] > present[0] else "波动下降"


def _coverage(metric_series: Dict[str, NumberSeries], years: List[str]) -> Dict[str, Any]:
    total = len(metric_series) * max(len(years), 1)
    present = 0
    missing: List[str] = []
    for key, series in metric_series.items():
        has_any = False
        for year in years:
            if _is_number(series.get(year)):
                present += 1
                has_any = True
        if not has_any:
            missing.append(METRIC_LABELS.get(key, key))
    return {
        "field_count": len(metric_series),
        "cell_count": total,
        "present_count": present,
        "coverage_ratio": round(present / total, 4) if total else 0,
        "missing_metrics": missing,
    }


def _red_flags(metric_series: Dict[str, NumberSeries], years: List[str]) -> List[Dict[str, Any]]:
    if not years:
        return []
    latest = years[-1]
    previous = years[-2] if len(years) >= 2 else None
    flags: List[Dict[str, Any]] = []

    debt_ratio = metric_series.get("debt_ratio", {}).get(latest)
    current_ratio = metric_series.get("current_ratio", {}).get(latest)
    cash_to_short_debt = metric_series.get("cash_to_short_debt", {}).get(latest)
    receivable_days = metric_series.get("receivable_turnover_days", {}).get(latest)
    inventory_days = metric_series.get("inventory_turnover_days", {}).get(latest)
    net_profit = metric_series.get("net_profit", {}).get(latest)
    operating_cf = metric_series.get("operating_cashflow", {}).get(latest)
    deducted_values = [metric_series.get("deducted_net_profit", {}).get(year) for year in years]
    receivable_growth = _growth(metric_series.get("receivable", {}).get(latest), metric_series.get("receivable", {}).get(previous) if previous else None)
    revenue_growth = _growth(metric_series.get("revenue", {}).get(latest), metric_series.get("revenue", {}).get(previous) if previous else None)

    def add(code: str, label: str, severity: str, detail: str) -> None:
        flags.append({"code": code, "label": label, "severity": severity, "detail": detail})

    if _is_number(debt_ratio) and float(debt_ratio) > 0.7:
        add("high_debt_ratio", "资产负债率高", "high", f"{latest}年资产负债率为{_fmt_percent(debt_ratio)}")
    if _is_number(current_ratio) and float(current_ratio) < 1:
        add("low_current_ratio", "流动比率低于1", "high", f"{latest}年流动比率为{_fmt_ratio(current_ratio)}")
    if _is_number(cash_to_short_debt) and float(cash_to_short_debt) < 1:
        add("low_cash_to_short_debt", "现金短债比低于1", "medium", f"{latest}年现金短债比为{_fmt_ratio(cash_to_short_debt)}")
    if _is_number(receivable_days) and float(receivable_days) > 180:
        add("slow_receivable_turnover", "应收周转慢", "medium", f"{latest}年应收账款周转天数为{_fmt_days(receivable_days)}")
    if _is_number(inventory_days) and float(inventory_days) > 180:
        add("slow_inventory_turnover", "存货周转慢", "medium", f"{latest}年存货周转天数为{_fmt_days(inventory_days)}")
    if _is_number(net_profit) and float(net_profit) < 0 and _is_number(operating_cf) and float(operating_cf) > 0:
        add("profit_loss_cash_positive", "利润为负但经营现金流为正", "medium", "需用折旧摊销、减值损失和营运资本变动解释利润现金流差异")
    if deducted_values and all(_is_number(value) and float(value) < 0 for value in deducted_values):
        add("deducted_profit_negative", "扣非净利润连续为负", "high", "主营业务盈利基础尚未完全修复")
    if _is_number(receivable_growth) and _is_number(revenue_growth) and float(receivable_growth) > float(revenue_growth) * 1.5:
        add("receivable_growth_outpaces_revenue", "应收增速显著高于收入", "medium", "需核查信用政策、客户集中度和期后回款")
    return flags


def build_structured_financial_package(
    enterprise_name: str,
    years: List[str],
    codeact_analysis: Dict[str, Any],
    generated_from: str = "已解析三大表",
    stock_code: str = "",
    source_type: str = "financial_statement",
    cross_provider_reconciliation: Optional[Dict[str, Any]] = None,
    evidence_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build the canonical structured financial package consumed downstream."""
    metrics_by_year = codeact_analysis.get("metrics") or {}
    years = [str(year) for year in (years or codeact_analysis.get("years") or []) if str(year).isdigit()]
    years = sorted(years)[-3:]
    metric_keys = [
        "revenue",
        "cost",
        "gross_profit",
        "net_profit",
        "deducted_net_profit",
        "operating_cashflow",
        "investing_cashflow",
        "financing_cashflow",
        "total_assets",
        "total_liabilities",
        "cash",
        "short_loan",
        "short_debt",
        "receivable",
        "inventory",
        "gross_margin",
        "net_margin",
        "debt_ratio",
        "current_ratio",
        "quick_ratio",
        "cash_to_short_debt",
        "ebitda_interest_coverage",
        "receivable_turnover_days",
        "inventory_turnover_days",
        "roe",
        "roa",
    ]
    metric_series = {key: _series_from_metrics(metrics_by_year, key, years) for key in metric_keys}
    display_series = {
        key: {year: _display_value(key, metric_series[key].get(year)) for year in years}
        for key in metric_keys
    }
    trends = {key: _trend(metric_series[key], years) for key in metric_keys}
    latest = years[-1] if years else ""
    latest_metrics = {
        key: {
            "label": METRIC_LABELS.get(key, key),
            "raw_value": metric_series[key].get(latest),
            "display_value": display_series[key].get(latest, "数据不可用"),
            "trend": trends[key],
        }
        for key in metric_keys
    }
    reconciliation = cross_provider_reconciliation or {}
    data_boundary: List[str] = []
    coverage = _coverage(metric_series, years)
    if coverage["missing_metrics"]:
        data_boundary.append("缺失字段：" + "、".join(coverage["missing_metrics"][:8]))
    if reconciliation:
        if reconciliation.get("passed"):
            data_boundary.append("AKShare/东方财富结构化字段交叉校验未发现超阈值差异。")
        else:
            data_boundary.append(f"跨源校验存在{reconciliation.get('mismatch_count', 0)}项超阈值差异，需回查巨潮/交易所原始公告。")
    if not data_boundary:
        data_boundary.append("结构化三大表关键字段覆盖较完整，仍需结合审计报告附注和原始公告复核。")

    return {
        "version": "structured_financial_data_layer_v1",
        "enterprise_name": enterprise_name,
        "stock_code": stock_code,
        "periods": years,
        "period_type": "annual",
        "unit_base": "yuan",
        "generated_from": generated_from,
        "source_type": source_type,
        "metric_labels": {key: METRIC_LABELS.get(key, key) for key in metric_keys},
        "metrics": metric_series,
        "display_metrics": display_series,
        "latest_metrics": latest_metrics,
        "trends": trends,
        "coverage": coverage,
        "cross_source_validation": reconciliation,
        "red_flags": _red_flags(metric_series, years),
        "data_boundary": data_boundary,
        "evidence_refs": evidence_refs or [],
    }

