"""Build structured financial dashboard charts for report rendering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


NumberSeries = Dict[str, Optional[float]]


def _values(series: NumberSeries, years: List[str]) -> List[Optional[float]]:
    return [series.get(year) for year in years]


def _has_data(series_list: List[Dict[str, Any]]) -> bool:
    for series in series_list:
        if any(value is not None for value in series.get("data", [])):
            return True
    return False


def _series(name: str, data: NumberSeries, years: List[str], unit: str) -> Dict[str, Any]:
    return {"name": name, "data": _values(data, years), "unit": unit}


def _latest(series: NumberSeries, years: List[str]) -> Optional[float]:
    for year in reversed(years):
        value = series.get(year)
        if value is not None:
            return value
    return None


def _trend_word(series: NumberSeries, years: List[str]) -> str:
    values = [series.get(year) for year in years if series.get(year) is not None]
    if len(values) < 2:
        return "数据不足"
    if values[-1] > values[0]:
        return "上升"
    if values[-1] < values[0]:
        return "下降"
    return "基本稳定"


def _amount_text(value: Optional[float]) -> str:
    if value is None:
        return "数据缺失"
    abs_value = abs(value)
    if abs_value >= 100000000:
        return f"{value / 100000000:.2f}亿元"
    if abs_value >= 10000:
        return f"{value / 10000:.2f}万元"
    return f"{value:.2f}元"


def _pct_text(value: Optional[float]) -> str:
    if value is None:
        return "数据缺失"
    return f"{value * 100:.2f}%"


def _ratio_text(value: Optional[float]) -> str:
    if value is None:
        return "数据缺失"
    return f"{value:.2f}"


def _chart(
    chart_id: str,
    title: str,
    chart_type: str,
    years: List[str],
    series: List[Dict[str, Any]],
    diagnosis: str,
    unit: str = "",
    thresholds: Optional[List[Dict[str, Any]]] = None,
    evidence_refs: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    if not _has_data(series):
        return None
    return {
        "id": chart_id,
        "title": title,
        "chart_type": chart_type,
        "years": years,
        "unit": unit,
        "series": series,
        "threshold_lines": thresholds or [],
        "diagnosis": diagnosis,
        "evidence_refs": evidence_refs or [],
    }


def build_financial_dashboard(
    enterprise_name: str,
    years: List[str],
    metrics: Dict[str, NumberSeries],
    evidence_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a 3-year financial dashboard spec consumed by the frontend."""
    refs = (evidence_refs or [])[:8]
    latest_year = years[-1] if years else "最新年度"
    revenue = metrics.get("revenue", {})
    net_profit = metrics.get("net_profit", {})
    gross_margin = metrics.get("gross_margin", {})
    net_margin = metrics.get("net_margin", {})
    debt_ratio = metrics.get("debt_ratio", {})
    current_ratio = metrics.get("current_ratio", {})
    quick_ratio = metrics.get("quick_ratio", {})
    operating_cf = metrics.get("operating_cf", {})
    investing_cf = metrics.get("investing_cf", {})
    financing_cf = metrics.get("financing_cf", {})
    cash = metrics.get("cash", {})
    receivable = metrics.get("receivable", {})
    inventory = metrics.get("inventory", {})
    fixed_assets = metrics.get("fixed_assets", {})
    construction = metrics.get("construction", {})
    short_loan = metrics.get("short_loan", {})
    cash_to_short_debt = metrics.get("cash_to_short_debt", {})
    inventory_turnover_days = metrics.get("inventory_turnover_days", {})
    receivable_turnover_days = metrics.get("receivable_turnover_days", {})
    ebitda_interest_coverage = metrics.get("ebitda_interest_coverage", {})
    notes_payable = metrics.get("notes_payable", {})
    payable = metrics.get("payable", {})
    roe = metrics.get("roe", {})
    roa = metrics.get("roa", {})

    charts: List[Dict[str, Any]] = []
    candidates = [
        _chart(
            "revenue_profit_trend",
            "营业收入与净利润趋势",
            "bar_line",
            years,
            [_series("营业收入", revenue, years, "元"), _series("净利润", net_profit, years, "元")],
            f"{enterprise_name}营业收入近三年呈{_trend_word(revenue, years)}趋势，{latest_year}年净利润为{_amount_text(_latest(net_profit, years))}，需观察规模增长是否有效转化为利润。",
            "元",
            evidence_refs=refs,
        ),
        _chart(
            "margin_trend",
            "毛利率与净利率趋势",
            "line",
            years,
            [_series("毛利率", gross_margin, years, "%"), _series("销售净利率", net_margin, years, "%")],
            f"{latest_year}年毛利率为{_pct_text(_latest(gross_margin, years))}，销售净利率为{_pct_text(_latest(net_margin, years))}，用于判断主营盈利空间和费用消化能力。",
            "%",
            evidence_refs=refs,
        ),
        _chart(
            "leverage_trend",
            "杠杆水平趋势",
            "line",
            years,
            [_series("资产负债率", debt_ratio, years, "%")],
            f"{latest_year}年资产负债率为{_pct_text(_latest(debt_ratio, years))}，若接近或超过参考线，需要复核债务期限结构和再融资安排。",
            "%",
            thresholds=[{"name": "资产负债率参考线", "value": 0.7, "unit": "%", "color": "#EF4444"}],
            evidence_refs=refs,
        ),
        _chart(
            "liquidity_trend",
            "流动性与短期偿债能力",
            "line",
            years,
            [_series("流动比率", current_ratio, years, "倍"), _series("速动比率", quick_ratio, years, "倍"), _series("现金短债比", cash_to_short_debt, years, "倍")],
            f"{latest_year}年流动比率为{_ratio_text(_latest(current_ratio, years))}，速动比率为{_ratio_text(_latest(quick_ratio, years))}，现金短债比为{_ratio_text(_latest(cash_to_short_debt, years))}，需结合短期借款和应收回款判断真实流动性。",
            "倍",
            thresholds=[
                {"name": "流动比率参考线", "value": 1.5, "unit": "倍", "color": "#D97706"},
                {"name": "速动比率参考线", "value": 1.0, "unit": "倍", "color": "#EF4444"},
            ],
            evidence_refs=refs,
        ),
        _chart(
            "cashflow_trend",
            "现金流结构",
            "bar",
            years,
            [
                _series("经营现金流", operating_cf, years, "元"),
                _series("投资现金流", investing_cf, years, "元"),
                _series("筹资现金流", financing_cf, years, "元"),
            ],
            f"{latest_year}年经营现金流为{_amount_text(_latest(operating_cf, years))}，需与净利润、投资扩张和筹资变化交叉验证还款来源稳定性。",
            "元",
            evidence_refs=refs,
        ),
        _chart(
            "asset_structure",
            "资产结构",
            "bar",
            years,
            [
                _series("货币资金", cash, years, "元"),
                _series("应收账款", receivable, years, "元"),
                _series("存货", inventory, years, "元"),
                _series("固定资产", fixed_assets, years, "元"),
                _series("在建工程", construction, years, "元"),
            ],
            "资产结构用于识别资金沉淀位置，重点关注应收、存货、固定资产和在建工程是否持续占用经营现金。",
            "元",
            evidence_refs=refs,
        ),
        _chart(
            "working_capital",
            "营运周转天数",
            "line",
            years,
            [_series("应收账款周转天数", receivable_turnover_days, years, "天"), _series("存货周转天数", inventory_turnover_days, years, "天")],
            f"{latest_year}年应收账款周转天数为{_ratio_text(_latest(receivable_turnover_days, years))}天，存货周转天数为{_ratio_text(_latest(inventory_turnover_days, years))}天，需核查账龄、跌价准备和期后回款。",
            "天",
            evidence_refs=refs,
        ),
        _chart(
            "debt_structure",
            "短期债务与供应链应付款",
            "bar",
            years,
            [_series("短期借款", short_loan, years, "元"), _series("应付票据", notes_payable, years, "元"), _series("应付账款", payable, years, "元")],
            "短期借款反映金融债务压力，应付票据和应付账款反映供应链信用占用，需结合到期分布和核心供应商账期判断。",
            "元",
            evidence_refs=refs,
        ),
        _chart(
            "return_and_interest_coverage",
            "回报与利息保障",
            "line",
            years,
            [_series("ROE", roe, years, "%"), _series("ROA", roa, years, "%"), _series("EBITDA利息保障倍数", ebitda_interest_coverage, years, "倍")],
            f"{latest_year}年ROE为{_pct_text(_latest(roe, years))}，ROA为{_pct_text(_latest(roa, years))}，EBITDA利息保障倍数为{_ratio_text(_latest(ebitda_interest_coverage, years))}，用于观察资本回报和利息偿付安全边际。",
            "",
            evidence_refs=refs,
        ),
    ]
    charts = [chart for chart in candidates if chart]
    return {
        "title": f"{enterprise_name}近三年财务数据分析",
        "years": years,
        "charts": charts,
        "data_boundary": "图表基于已解析三大表和内部财务计算结果生成；缺失科目以空值处理，需结合审计报告附注和原始凭证复核。",
    }
