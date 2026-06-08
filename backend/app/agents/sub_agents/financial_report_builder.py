"""企业客户财务状况分析报告生成器。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import math
import re

import pandas as pd


def _year_columns(df: Optional[pd.DataFrame]) -> List[str]:
    if df is None:
        return []
    years = [str(col) for col in df.columns if str(col).isdigit() and len(str(col)) == 4]
    return sorted(years)


def _label_column(df: pd.DataFrame):
    for col in df.columns:
        if any(keyword in str(col) for keyword in ["项目", "科目", "指标", "名称"]):
            return col
    for col in df.columns:
        if not (str(col).isdigit() and len(str(col)) == 4):
            return col
    return df.columns[0]


def _column_for_year(df: pd.DataFrame, year: str):
    for col in df.columns:
        if str(col) == str(year):
            return col
    return None


def _to_number(value: Any) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "--", "N/A", "nan"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"(?<=\d)\s+(?=\d{1,2}$)", ".", text)
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", "."}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return -number if negative else number


def _value_by_item(df: Optional[pd.DataFrame], keywords: List[str], year: str) -> Optional[float]:
    if df is None or df.empty:
        return None
    year_col = _column_for_year(df, year)
    if year_col is None:
        return None
    label_col = _label_column(df)

    rows = [(str(row.get(label_col, "")).replace("\n", "").replace(" ", ""), row) for _, row in df.iterrows()]
    for keyword in keywords:
        for label, row in rows:
            if label == keyword:
                return _to_number(row.get(year_col))
    for keyword in keywords:
        for label, row in rows:
            if keyword in label:
                return _to_number(row.get(year_col))
    return None


def _series(df: Optional[pd.DataFrame], keywords: List[str], years: List[str]) -> Dict[str, Optional[float]]:
    return {year: _value_by_item(df, keywords, year) for year in years}


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous)


def _format_amount(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:,.2f}"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value * 100:.2f}%"


def _format_ratio(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:.2f}"


def _trend_text(values: Dict[str, Optional[float]], years: List[str]) -> str:
    available = [values.get(year) for year in years if values.get(year) is not None]
    if len(available) < 2:
        return "数据不足"
    if available[-1] > available[0]:
        return "增长"
    if available[-1] < available[0]:
        return "下降"
    return "基本稳定"


def _row(label: str, values: Dict[str, Optional[float]], years: List[str], formatter=_format_amount) -> Dict[str, Any]:
    return {"item": label, "values": {year: formatter(values.get(year)) for year in years}}


def _ratio_row(label: str, values: Dict[str, Optional[float]], years: List[str], formatter=_format_percent) -> Dict[str, Any]:
    return {"item": label, "values": {year: formatter(values.get(year)) for year in years}}


def _latest_growth_text(values: Dict[str, Optional[float]], years: List[str]) -> str:
    if len(years) < 2:
        return "数据不足"
    latest, previous = years[-1], years[-2]
    return _format_percent(_growth(values.get(latest), values.get(previous)))


def build_financial_analysis_report(
    enterprise_name: str,
    financial_data: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """基于三大表生成银行财务状况分析报告结构。"""
    income = financial_data.get("income_statement")
    balance = financial_data.get("balance_sheet")
    cash_flow = financial_data.get("cash_flow")
    years = sorted(set(_year_columns(income)) | set(_year_columns(balance)) | set(_year_columns(cash_flow)))
    years = years[-3:] if len(years) > 3 else years

    revenue = _series(income, ["营业收入", "主营业务收入", "收入"], years)
    cost = _series(income, ["营业成本", "主营业务成本"], years)
    gross_profit = {year: (revenue.get(year) - cost.get(year)) if revenue.get(year) is not None and cost.get(year) is not None else _value_by_item(income, ["毛利润", "毛利"], year) for year in years}
    net_profit = _series(income, ["净利润"], years)
    financial_expense = _series(income, ["财务费用"], years)
    operating_profit = _series(income, ["营业利润"], years)
    total_profit = _series(income, ["利润总额"], years)

    total_assets = _series(balance, ["资产总计", "资产合计", "总资产"], years)
    current_assets = _series(balance, ["流动资产合计", "流动资产"], years)
    cash = _series(balance, ["货币资金"], years)
    receivable = _series(balance, ["应收账款"], years)
    inventory = _series(balance, ["存货"], years)
    fixed_assets = _series(balance, ["固定资产"], years)
    construction = _series(balance, ["在建工程"], years)
    total_liabilities = _series(balance, ["负债合计", "负债总计", "总负债"], years)
    current_liabilities = _series(balance, ["流动负债合计", "流动负债"], years)
    short_loan = _series(balance, ["短期借款"], years)
    notes_payable = _series(balance, ["应付票据"], years)
    payable = _series(balance, ["应付账款"], years)
    equity = _series(balance, ["所有者权益(或股东权益)合计", "所有者权益", "股东权益", "净资产"], years)
    paid_in_capital = _series(balance, ["实收资本"], years)
    capital_reserve = _series(balance, ["资本公积"], years)
    retained_earnings = _series(balance, ["未分配利润"], years)

    operating_cf = _series(cash_flow, ["经营活动产生的现金流量净额", "经营活动产生现金流量净额", "经营活动现金流"], years)
    investing_cf = _series(cash_flow, ["投资活动产生的现金流量净额", "投资活动现金流"], years)
    financing_cf = _series(cash_flow, ["筹资活动产生的现金流量净额", "筹资活动现金流"], years)

    debt_ratio = {year: _safe_div(total_liabilities.get(year), total_assets.get(year)) for year in years}
    current_ratio = {year: _safe_div(current_assets.get(year), current_liabilities.get(year)) for year in years}
    quick_ratio = {year: _safe_div((current_assets.get(year) or 0) - (inventory.get(year) or 0), current_liabilities.get(year)) if current_assets.get(year) is not None else None for year in years}
    gross_margin = {year: _safe_div(gross_profit.get(year), revenue.get(year)) for year in years}
    net_margin = {year: _safe_div(net_profit.get(year), revenue.get(year)) for year in years}
    roa = {year: _safe_div(net_profit.get(year), total_assets.get(year)) for year in years}
    roe = {year: _safe_div(net_profit.get(year), equity.get(year)) for year in years}
    receivable_turnover = {year: _safe_div(revenue.get(year), receivable.get(year)) for year in years}
    inventory_turnover = {year: _safe_div(cost.get(year), inventory.get(year)) for year in years}
    asset_turnover = {year: _safe_div(revenue.get(year), total_assets.get(year)) for year in years}
    revenue_growth = {year: _growth(revenue.get(year), revenue.get(years[index - 1])) if index > 0 else None for index, year in enumerate(years)}
    profit_growth = {year: _growth(net_profit.get(year), net_profit.get(years[index - 1])) if index > 0 else None for index, year in enumerate(years)}
    capital_growth = {year: _growth(equity.get(year), equity.get(years[index - 1])) if index > 0 else None for index, year in enumerate(years)}
    interest_coverage = {year: _safe_div((total_profit.get(year) or operating_profit.get(year)), financial_expense.get(year)) for year in years}

    latest = years[-1] if years else "最新年度"
    risk_items: List[str] = []
    if debt_ratio.get(latest) is not None and debt_ratio[latest] > 0.7:
        risk_items.append("资产负债率高于70%，需关注杠杆水平和再融资压力。")
    if current_ratio.get(latest) is not None and current_ratio[latest] < 1:
        risk_items.append("流动比率低于1，短期偿债安全边际不足。")
    if operating_cf.get(latest) is not None and operating_cf[latest] < 0:
        risk_items.append("经营性净现金流为负，需核实主营业务回款质量。")
    if receivable.get(latest) and revenue.get(latest) and receivable[latest] / revenue[latest] > 0.2:
        risk_items.append("应收账款占营业收入比例较高，需关注账龄结构和客户集中度。")
    if net_margin.get(latest) is not None and net_margin[latest] < 0.05:
        risk_items.append("销售净利率低于5%，盈利缓冲较薄。")
    if not risk_items:
        risk_items.append("未发现明显重大财务异常，但仍需结合审计意见、授信用途和行业景气度复核。")

    risk_score = max(50, 100 - max(0, len(risk_items) - 1) * 10)
    risk_rating = "low" if risk_score >= 80 else "medium" if risk_score >= 60 else "high"
    recommendation = "建议授信，风险可控" if risk_rating == "low" else "建议谨慎授信，需补充核实重点科目" if risk_rating == "medium" else "建议暂缓授信，待重大风险排查后再议"

    cash_type = {
        year: "".join("正" if (value or 0) >= 0 else "负" for value in [operating_cf.get(year), investing_cf.get(year), financing_cf.get(year)])
        for year in years
    }

    sections = [
        {
            "title": "一、财务重点及异常科目分析",
            "subsections": [
                {
                    "title": "资产分析",
                    "unit": "元",
                    "table": {"columns": years, "rows": [
                        _row("总资产", total_assets, years),
                        _row("货币资金", cash, years),
                        _row("应收账款", receivable, years),
                        _row("存货", inventory, years),
                        _row("固定资产", fixed_assets, years),
                        _row("在建工程", construction, years),
                    ]},
                    "analysis": [
                        f"{enterprise_name}近三年总资产呈{_trend_text(total_assets, years)}趋势，{latest}年总资产为{_format_amount(total_assets.get(latest))}元，最近一期同比变动为{_latest_growth_text(total_assets, years)}。",
                        f"资产结构方面，{latest}年应收账款为{_format_amount(receivable.get(latest))}元，存货为{_format_amount(inventory.get(latest))}元，需结合账龄、跌价准备和项目结算周期判断资产质量。",
                        f"营业收入最新同比增速为{_format_percent(revenue_growth.get(latest))}，总资产最新同比增速为{_latest_growth_text(total_assets, years)}，可用于判断资产扩张是否有效转化为经营规模。",
                    ],
                    "risk提示": "关注应收账款回款、存货变现能力及资产扩张效率。",
                },
                {
                    "title": "负债分析",
                    "unit": "元",
                    "table": {"columns": years, "rows": [
                        _row("短期借款", short_loan, years),
                        _row("应付票据", notes_payable, years),
                        _row("应付账款", payable, years),
                        _row("流动负债合计", current_liabilities, years),
                        _row("总负债", total_liabilities, years),
                        _row("财务费用", financial_expense, years),
                        _ratio_row("资产负债率", debt_ratio, years),
                    ]},
                    "analysis": [
                        f"{latest}年资产负债率为{_format_percent(debt_ratio.get(latest))}，总负债为{_format_amount(total_liabilities.get(latest))}元，最近一期总负债同比变动为{_latest_growth_text(total_liabilities, years)}。",
                        f"短期负债方面，{latest}年流动负债合计为{_format_amount(current_liabilities.get(latest))}元，流动负债占总负债比例为{_format_percent(_safe_div(current_liabilities.get(latest), total_liabilities.get(latest)))}。",
                        f"财务费用为{_format_amount(financial_expense.get(latest))}元，可作为融资成本变化的观察项，后续需结合借款明细和利率水平判断。",
                    ],
                    "risk提示": "关注短期债务集中到期、融资成本上升及供应商信用占用变化。",
                },
                {
                    "title": "所有者权益分析",
                    "unit": "元",
                    "table": {"columns": years, "rows": [
                        _row("所有者权益", equity, years),
                        _row("实收资本", paid_in_capital, years),
                        _row("资本公积", capital_reserve, years),
                        _row("未分配利润", retained_earnings, years),
                        _ratio_row("所有者权益增速", capital_growth, years),
                    ]},
                    "analysis": [
                        f"所有者权益近三年呈{_trend_text(equity, years)}趋势，{latest}年为{_format_amount(equity.get(latest))}元，最新增速为{_format_percent(capital_growth.get(latest))}。",
                        "若实收资本、资本公积或未分配利润数据不可用，需客户补充权益明细，以区分外部增资、利润留存和其他权益变动。",
                    ],
                    "risk提示": "关注权益增长来源是否稳定，利润是否有效沉淀为资本实力。",
                },
                {
                    "title": "利润表分析",
                    "unit": "元",
                    "table": {"columns": years, "rows": [
                        _row("营业收入", revenue, years),
                        _row("营业成本", cost, years),
                        _row("营业毛利润", gross_profit, years),
                        _row("营业利润", operating_profit, years),
                        _row("利润总额", total_profit, years),
                        _row("净利润", net_profit, years),
                        _ratio_row("主营业务毛利率", gross_margin, years),
                    ]},
                    "analysis": [
                        f"营业收入近三年呈{_trend_text(revenue, years)}趋势，{latest}年营业收入为{_format_amount(revenue.get(latest))}元，最新同比增速为{_format_percent(revenue_growth.get(latest))}。",
                        f"{latest}年毛利率为{_format_percent(gross_margin.get(latest))}，销售净利率为{_format_percent(net_margin.get(latest))}，反映主营业务盈利能力和费用消化能力。",
                        f"净利润最新同比增速为{_format_percent(profit_growth.get(latest))}，需结合费用率和非经常性损益判断利润质量。",
                    ],
                    "risk提示": "关注收入增长持续性、毛利率异常波动和净利润现金含量。",
                },
                {
                    "title": "现金流量表分析",
                    "unit": "元",
                    "table": {"columns": years, "rows": [
                        _row("经营性净现金流", operating_cf, years),
                        _row("投资性净现金流", investing_cf, years),
                        _row("筹资性净现金流", financing_cf, years),
                    ]},
                    "analysis": [
                        f"近三年现金流类型分别为：{'; '.join(f'{year}年：{cash_type[year]}' for year in years)}。",
                        f"{latest}年经营性净现金流为{_format_amount(operating_cf.get(latest))}元，若持续为正，说明主营业务现金回笼对偿债形成一定支撑。",
                        f"投资性净现金流为{_format_amount(investing_cf.get(latest))}元，筹资性净现金流为{_format_amount(financing_cf.get(latest))}元，需结合项目投资和融资计划判断资金缺口。",
                    ],
                    "risk提示": "关注经营现金流与利润是否匹配，以及投资扩张对外部融资的依赖。",
                },
            ],
        },
        {
            "title": "二、企业财务指标分析",
            "subsections": [
                {
                    "title": "偿债能力分析",
                    "table": {"columns": years, "rows": [
                        _ratio_row("资产负债率", debt_ratio, years),
                        _ratio_row("流动比率", current_ratio, years, _format_ratio),
                        _ratio_row("速动比率", quick_ratio, years, _format_ratio),
                        _ratio_row("利息保障倍数", interest_coverage, years, _format_ratio),
                    ]},
                    "analysis": [f"{latest}年流动比率为{_format_ratio(current_ratio.get(latest))}，速动比率为{_format_ratio(quick_ratio.get(latest))}，资产负债率为{_format_percent(debt_ratio.get(latest))}。"],
                    "risk提示": "重点关注短期偿债能力和有息负债成本。",
                },
                {
                    "title": "盈利能力分析",
                    "table": {"columns": years, "rows": [
                        _row("EBITDA", {year: (net_profit.get(year) or 0) + (financial_expense.get(year) or 0) for year in years}, years),
                        _ratio_row("销售净利率", net_margin, years),
                        _ratio_row("ROA", roa, years),
                        _ratio_row("ROE", roe, years),
                    ]},
                    "analysis": [f"{latest}年销售净利率为{_format_percent(net_margin.get(latest))}，ROA为{_format_percent(roa.get(latest))}，ROE为{_format_percent(roe.get(latest))}。"],
                    "risk提示": "若ROE显著高于ROA，需判断是否主要由财务杠杆驱动。",
                },
                {
                    "title": "营运能力分析",
                    "table": {"columns": years, "rows": [
                        _ratio_row("存货周转率", inventory_turnover, years, _format_ratio),
                        _ratio_row("应收账款周转率", receivable_turnover, years, _format_ratio),
                        _ratio_row("总资产周转率", asset_turnover, years, _format_ratio),
                    ]},
                    "analysis": [f"{latest}年应收账款周转率为{_format_ratio(receivable_turnover.get(latest))}，存货周转率为{_format_ratio(inventory_turnover.get(latest))}。"],
                    "risk提示": "关注应收账款周转放缓、存货积压和资产使用效率下降。",
                },
                {
                    "title": "增长能力分析",
                    "table": {"columns": years, "rows": [
                        _ratio_row("销售收入增长率", revenue_growth, years),
                        _ratio_row("净利润增长率", profit_growth, years),
                        _ratio_row("资本积累率", capital_growth, years),
                    ]},
                    "analysis": [f"{latest}年销售收入增长率为{_format_percent(revenue_growth.get(latest))}，净利润增长率为{_format_percent(profit_growth.get(latest))}，资本积累率为{_format_percent(capital_growth.get(latest))}。"],
                    "risk提示": "关注增长是否由主营业务驱动，以及利润增长能否沉淀为权益增长。",
                },
            ],
        },
        {
            "title": "三、风险总结",
            "subsections": [
                {
                    "title": "主要潜在风险提示",
                    "risks": risk_items,
                    "analysis": [recommendation],
                }
            ],
        },
    ]

    return {
        "report_type": "financial_analysis",
        "enterprise_name": enterprise_name,
        "risk_rating": risk_rating,
        "risk_score": risk_score,
        "recommendation": recommendation,
        "years": years,
        "generated_from": "用户上传财报",
        "sections": sections,
        "risk_summary": risk_items,
    }
