"""企业客户财务状况分析报告生成器。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import math
import re

import pandas as pd

from app.codeact import run_codeact_tool
from app.agents.sub_agents.financial_dashboard_builder import build_financial_dashboard
from app.agents.sub_agents.financial_narrative_writer import build_financial_narrative
from app.agents.sub_agents.financial_knowledge_context import build_financial_knowledge_context
from app.agents.sub_agents.structured_financial_data import build_structured_financial_package


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


def _cagr(values: Dict[str, Optional[float]], years: List[str]) -> Optional[float]:
    available = [(year, values.get(year)) for year in years if values.get(year) not in (None, 0)]
    if len(available) < 2:
        return None
    start_value = available[0][1]
    end_value = available[-1][1]
    periods = max(1, int(available[-1][0]) - int(available[0][0]))
    if start_value is None or end_value is None or start_value <= 0 or end_value <= 0:
        return None
    return (end_value / start_value) ** (1 / periods) - 1


def _pct_delta(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None:
        return None
    return current - previous


def _format_amount(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:,.2f}"


def _format_amount_short(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    abs_value = abs(value)
    if abs_value >= 100000000:
        return f"{value / 100000000:.2f}亿元"
    if abs_value >= 10000:
        return f"{value / 10000:.2f}万元"
    return f"{value:.2f}元"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value * 100:.2f}%"


def _format_ratio(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:.2f}"


def _format_days(value: Optional[float]) -> str:
    if value is None:
        return "数据不可用"
    return f"{value:.1f}天"


# 财务指标标签常见 OCR / 识别错误纠错映射
_METRIC_LABEL_CORRECTIONS = {
    "鱼子": "ROE",
    "鱼籽": "ROE",
    "鱼子（％）": "ROE(%)",
    "鱼籽（％）": "ROE(%)",
}


def _sanitize_metric_label(label: str) -> str:
    """Fix common OCR errors in metric labels before they reach the report."""
    if not isinstance(label, str):
        label = str(label)
    for bad, good in _METRIC_LABEL_CORRECTIONS.items():
        if bad in label:
            return label.replace(bad, good)
    return label


def _trend_text(values: Dict[str, Optional[float]], years: List[str]) -> str:
    available = [values.get(year) for year in years if values.get(year) is not None]
    if len(available) < 2:
        return "数据不足"
    if available[-1] > available[0]:
        return "增长"
    if available[-1] < available[0]:
        return "下降"
    return "基本稳定"


def _series_amount_sentence(values: Dict[str, Optional[float]], years: List[str], label: str) -> str:
    rows = [f"{year}年{_format_amount_short(values.get(year))}" for year in years if values.get(year) is not None]
    if not rows:
        return f"近三年{label}数据不可用"
    return f"近三年{label}分别为" + "、".join(rows)


def _series_percent_sentence(values: Dict[str, Optional[float]], years: List[str], label: str) -> str:
    rows = [f"{year}年{_format_percent(values.get(year))}" for year in years if values.get(year) is not None]
    if not rows:
        return f"近三年{label}数据不可用"
    return f"近三年{label}分别为" + "、".join(rows)


def _profit_change_sentence(values: Dict[str, Optional[float]], years: List[str], label: str) -> str:
    available = [(year, values.get(year)) for year in years if values.get(year) is not None]
    if len(available) < 2:
        return f"{label}趋势数据不足，需补充完整利润表后判断。"
    start_year, start_value = available[0]
    end_year, end_value = available[-1]
    if start_value is None or end_value is None:
        return f"{label}趋势数据不足，需补充完整利润表后判断。"
    if start_value >= 0 and end_value < 0:
        trend = "由盈转亏"
    elif start_value < 0 and end_value < 0:
        trend = "亏损扩大" if abs(end_value) > abs(start_value) else "亏损收窄"
    elif end_value > start_value:
        trend = "持续改善" if all((values.get(year) or 0) >= (values.get(years[index - 1]) or 0) for index, year in enumerate(years) if index > 0 and values.get(year) is not None and values.get(years[index - 1]) is not None) else "波动改善"
    elif end_value < start_value:
        trend = "持续下滑" if all((values.get(year) or 0) <= (values.get(years[index - 1]) or 0) for index, year in enumerate(years) if index > 0 and values.get(year) is not None and values.get(years[index - 1]) is not None) else "波动下滑"
    else:
        trend = "基本稳定"
    return f"{label}从{start_year}年的{_format_amount_short(start_value)}变化至{end_year}年的{_format_amount_short(end_value)}，呈{trend}。"


def _all_negative(values: Dict[str, Optional[float]], years: List[str]) -> bool:
    available = [values.get(year) for year in years if values.get(year) is not None]
    return bool(available) and all((value or 0) < 0 for value in available)


def _available_amount_series(values: Dict[str, Optional[float]], years: List[str], label: str) -> str:
    rows = [f"{year}年{_format_amount_short(values.get(year))}" for year in years if values.get(year) is not None]
    if not rows:
        return f"[需补充：{label}]"
    return "、".join(rows)


def _build_profit_cash_bridge(
    years: List[str],
    net_profit: Dict[str, Optional[float]],
    deducted_net_profit: Dict[str, Optional[float]],
    operating_cf: Dict[str, Optional[float]],
    depreciation_amortization: Dict[str, Optional[float]],
    asset_impairment: Dict[str, Optional[float]],
    credit_impairment: Dict[str, Optional[float]],
    investment_income: Dict[str, Optional[float]],
    fixed_assets: Dict[str, Optional[float]],
    construction: Dict[str, Optional[float]],
) -> Dict[str, Any]:
    """Build a CPA-style bridge between accounting profit and operating cash flow."""
    latest = years[-1] if years else "最新年度"
    latest_profit = net_profit.get(latest)
    latest_ocf = operating_cf.get(latest)
    missing_items: List[str] = []
    if not any(depreciation_amortization.get(year) is not None for year in years):
        missing_items.append("折旧摊销明细")
    if not any(asset_impairment.get(year) is not None for year in years):
        missing_items.append("资产减值损失")
    if not any(credit_impairment.get(year) is not None for year in years):
        missing_items.append("信用减值损失")
    if not any(deducted_net_profit.get(year) is not None for year in years):
        missing_items.append("扣非净利润")
    if not any(investment_income.get(year) is not None for year in years):
        missing_items.append("投资收益明细")

    non_cash_parts = []
    if any(depreciation_amortization.get(year) is not None for year in years):
        non_cash_parts.append(f"折旧摊销（{_available_amount_series(depreciation_amortization, years, '折旧摊销')}）")
    if any(asset_impairment.get(year) is not None for year in years):
        non_cash_parts.append(f"资产减值损失（{_available_amount_series(asset_impairment, years, '资产减值损失')}）")
    if any(credit_impairment.get(year) is not None for year in years):
        non_cash_parts.append(f"信用减值损失（{_available_amount_series(credit_impairment, years, '信用减值损失')}）")
    non_cash_text = "、".join(non_cash_parts) if non_cash_parts else "[需补充：折旧摊销、资产减值损失、信用减值损失明细]"

    if latest_profit is not None and latest_ocf is not None:
        if latest_profit < 0 <= latest_ocf:
            conclusion = "利润承压但经营现金流仍为正，现金流表现阶段性优于账面利润。"
            implication = "该情形常见于重资产制造企业，可能由折旧摊销、资产减值等非现金成本拉低利润；但若扣非净利润持续为负，仍说明主营业务盈利基础尚未完全修复。"
        elif latest_profit >= 0 > latest_ocf:
            conclusion = "账面利润为正但经营现金流为负，利润现金含量不足。"
            implication = "该情形通常指向回款滞后、应收和存货占用、收入确认时点或信用政策变化，授信审查应优先核验银行流水、纳税和期后回款。"
        elif latest_profit < 0 and latest_ocf < 0:
            conclusion = "净利润和经营现金流均为负，主营造血和现金回笼均存在压力。"
            implication = "需同步核查亏损原因、订单质量、客户回款和短债到期安排，避免新增授信被动补流。"
        else:
            conclusion = "净利润和经营现金流同向为正，账面盈利与现金回款具备一定匹配基础。"
            implication = "仍需观察经营现金流对净利润的覆盖倍数、应收账款周转和资本开支压力。"
    else:
        conclusion = "利润与经营现金流桥数据不足，暂不能判断利润现金含量。"
        implication = "需补齐利润表、现金流量表及报表附注后再判断第一还款来源稳定性。"

    deducted_text = ""
    if _all_negative(deducted_net_profit, years):
        deducted_text = "扣非净利润近三年均为负，表明主营业务尚未实现真正盈利，净利润表现需剔除非经常性损益后审慎看待。"
    elif any(deducted_net_profit.get(year) is not None for year in years):
        deducted_text = f"扣非净利润序列为{_available_amount_series(deducted_net_profit, years, '扣非净利润')}，需与净利润差异联动核查政府补助、投资收益和资产处置等非核心利润来源。"
    else:
        deducted_text = "[需补充：扣非净利润和非经常性损益明细]，否则无法判断主营盈利是否真正修复。"

    heavy_asset_hint = ""
    latest_fixed = fixed_assets.get(latest)
    latest_cip = construction.get(latest)
    if latest_fixed is not None or latest_cip is not None:
        heavy_asset_hint = f"{latest}年固定资产为{_format_amount_short(latest_fixed)}、在建工程为{_format_amount_short(latest_cip)}，若企业处于重资产扩产或产能爬坡阶段，应重点核查新增折旧、转固节奏、产能利用率和减值测试。"
    else:
        heavy_asset_hint = "[需补充：固定资产、在建工程及产能利用率]，以判断利润波动是否受重资产投产和折旧摊销影响。"

    return {
        "conclusion": conclusion,
        "bridge_explanation": f"净利润序列为{_available_amount_series(net_profit, years, '净利润')}；经营活动现金流序列为{_available_amount_series(operating_cf, years, '经营活动现金流量净额')}。两者差异应优先从{non_cash_text}以及营运资本变动解释。",
        "deducted_profit_judgement": deducted_text,
        "heavy_asset_judgement": heavy_asset_hint,
        "investment_income_judgement": f"投资收益序列为{_available_amount_series(investment_income, years, '投资收益')}，若投资收益由盈转亏或占净利润比重较高，应归类为非核心利润波动来源。" if any(investment_income.get(year) is not None for year in years) else "[需补充：投资收益明细]，以判断利润波动是否受非主营因素影响。",
        "credit_implication": implication,
        "missing_items": missing_items,
    }


def _income_statement_analysis(
    years: List[str],
    revenue: Dict[str, Optional[float]],
    cost: Dict[str, Optional[float]],
    net_profit: Dict[str, Optional[float]],
    deducted_net_profit: Dict[str, Optional[float]],
    gross_margin: Dict[str, Optional[float]],
    net_margin: Dict[str, Optional[float]],
    revenue_growth: Dict[str, Optional[float]],
    profit_cash_bridge: Optional[Dict[str, Any]] = None,
    annual_report_notes: Optional[Dict[str, Any]] = None,
) -> List[str]:
    if not years:
        return ["利润表数据不足，需补充近三年营业收入、营业成本、净利润和扣非净利润后判断。"]
    latest = years[-1]
    revenue_trend = "持续增长" if _trend_text(revenue, years) == "增长" else "持续下降" if _trend_text(revenue, years) == "下降" else "基本稳定"
    revenue_cagr = _format_percent(_cagr(revenue, years))
    latest_growth = _format_percent(revenue_growth.get(latest))
    deducted_available = any(deducted_net_profit.get(year) is not None for year in years)
    deducted_sentence = _profit_change_sentence(deducted_net_profit, years, "扣非净利润") if deducted_available else "扣非净利润数据暂未稳定取得，需结合年报非经常性损益明细判断主营盈利质量。"

    notes = annual_report_notes or {}
    business_segments = notes.get("business_segments") or []
    rd_expenses = notes.get("rd_expenses") or {}
    attribution = notes.get("attribution") or {}

    # Revenue driver attribution from business segments when available.
    segment_sentence = ""
    if business_segments:
        def _parse_income_value(seg: Dict[str, Any]) -> float:
            raw = seg.get("income") or "0"
            cleaned = re.sub(r"[^\d.\-]", "", str(raw).replace(",", ""))
            try:
                return float(cleaned) if cleaned else 0.0
            except ValueError:
                return 0.0

        def _parse_growth_value(seg: Dict[str, Any]) -> Optional[float]:
            raw = (seg.get("raw") or {}).get("营业收入同比") or seg.get("income_growth") or ""
            cleaned = re.sub(r"[^\d.\-]", "", str(raw).replace(",", ""))
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None

        sorted_by_income = sorted(business_segments, key=_parse_income_value, reverse=True)
        top_segment = sorted_by_income[0]
        top_name = top_segment.get("item_name") or "主营业务"
        top_income = top_segment.get("income") or ""
        top_ratio = top_segment.get("income_ratio") or ""

        fastest = None
        fastest_growth = None
        for seg in business_segments:
            growth = _parse_growth_value(seg)
            if growth is not None and (fastest_growth is None or growth > fastest_growth):
                fastest = seg
                fastest_growth = growth

        parts = [f"收入构成中，{top_name}贡献主要份额（收入{top_income}）"]
        if top_ratio:
            parts[-1] += f"，占比{top_ratio}"
        parts[-1] += "。"
        if fastest is not None and fastest.get("item_name") != top_name and fastest_growth is not None:
            parts.append(f"其中{fastest.get('item_name')}营业收入同比增长{fastest_growth:.2f}%，是近三年营收增长的重要拉动。")
        segment_sentence = "".join(parts)

    # 年报深度归因：用管理层原文解释替换通用营收归因模板（若有）。
    from app.agents.sub_agents.annual_report_attribution_extractor import render_revenue_attribution
    revenue_attribution_sentence = render_revenue_attribution(attribution)
    if revenue_attribution_sentence:
        segment_sentence = (segment_sentence + revenue_attribution_sentence).strip()

    # R&D intensity.
    rd_sentence = ""
    rd_latest = rd_expenses.get(latest)
    if rd_latest is not None and revenue.get(latest):
        rd_ratio = rd_latest / revenue[latest]
        rd_series = _series_amount_sentence(rd_expenses, years, "研发费用")
        rd_sentence = f"研发投入方面，{rd_series}；{latest}年研发费用率为{_format_percent(rd_ratio)}，需结合行业技术迭代强度和资本化比例判断研发转化效率。"

    # Gross margin attribution: 优先使用年报管理层深度归因，回退到通用模板。
    margin_trend = _trend_text(gross_margin, years)
    from app.agents.sub_agents.annual_report_attribution_extractor import render_margin_attribution
    margin_attribution = render_margin_attribution(attribution)
    if margin_attribution:
        # 年报提供了具体归因（如产能过剩/价格下行/产能爬坡），直接引用，不再用通用模板。
        margin_attribution_text = margin_attribution
    elif margin_trend == "下降":
        margin_attribution_text = "毛利率下滑通常受行业产能过剩、产品价格下行、新产线产能爬坡期固定成本摊销较高、固定资产折旧增加等因素叠加影响，需结合具体业务结构和价格周期复核。"
    elif margin_trend == "增长":
        margin_attribution_text = "毛利率回升可能受益于产品结构优化、价格企稳或规模效应释放，但需区分是需求改善还是成本一次性下降驱动。"
    else:
        margin_attribution_text = "毛利率趋势相对平稳，但仍需结合产品结构、价格周期、产能利用率和折旧摊销影响复核。"

    lines = [
        f"公司近三年营业收入{revenue_trend}。{_series_amount_sentence(revenue, years, '营业收入')}，年复合增长率约{revenue_cagr}；{latest}年营收同比增长{latest_growth}，营业成本为{_format_amount_short(cost.get(latest))}。{segment_sentence}",
        f"盈利能力方面，{_profit_change_sentence(net_profit, years, '净利润')}{deducted_sentence}若扣非利润弱于净利润或持续为负，说明主营业务盈利修复基础仍需进一步核实。",
        f"毛利率方面，{_series_percent_sentence(gross_margin, years, '毛利率')}；{latest}年销售净利率为{_format_percent(net_margin.get(latest))}。{margin_attribution_text}",
    ]
    if rd_sentence:
        lines.append(rd_sentence)
    if profit_cash_bridge:
        lines.append(str(profit_cash_bridge.get("deducted_profit_judgement") or ""))
    return [line for line in lines if line]


def _balance_sheet_analysis(
    years: List[str],
    total_assets: Dict[str, Optional[float]],
    current_assets: Dict[str, Optional[float]],
    receivable: Dict[str, Optional[float]],
    inventory: Dict[str, Optional[float]],
    fixed_assets: Dict[str, Optional[float]],
    construction: Dict[str, Optional[float]],
    total_liabilities: Dict[str, Optional[float]],
    current_liabilities: Dict[str, Optional[float]],
    short_loan: Dict[str, Optional[float]],
    notes_payable: Dict[str, Optional[float]],
    due_within_one_year: Dict[str, Optional[float]],
    equity: Dict[str, Optional[float]],
    debt_ratio: Dict[str, Optional[float]],
    current_ratio: Dict[str, Optional[float]],
    annual_report_notes: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """资产负债分析：资产结构、负债结构、权益变化。"""
    if not years:
        return ["资产负债表数据不足，需补充近三年资产、负债和权益数据后判断。"]
    latest = years[-1]
    first = years[0]
    lines: List[str] = []

    # 资产结构分析
    notes = annual_report_notes or {}
    intangible_assets = notes.get("intangible_assets") or {}
    development_expenses = notes.get("development_expenses") or {}
    total_assets_latest = total_assets.get(latest)
    fixed_assets_latest = fixed_assets.get(latest)
    construction_latest = construction.get(latest)
    current_assets_latest = current_assets.get(latest)
    intangible_latest = intangible_assets.get(latest)
    develop_latest = development_expenses.get(latest)
    if total_assets_latest and total_assets_latest > 0:
        non_current_ratio = ((fixed_assets_latest or 0) + (construction_latest or 0)) / total_assets_latest
        non_current_pct = non_current_ratio * 100
        current_pct = ((current_assets_latest or 0) / total_assets_latest) * 100
        asset_structure = f"{latest}年总资产为{_format_amount_short(total_assets_latest)}，非流动资产占比约{non_current_pct:.1f}%（固定资产{_format_amount_short(fixed_assets_latest)}、在建工程{_format_amount_short(construction_latest)}"
        if intangible_latest is not None:
            asset_structure += f"、无形资产{_format_amount_short(intangible_latest)}"
            if develop_latest is not None:
                asset_structure += f"、开发支出{_format_amount_short(develop_latest)}"
        asset_structure += f"），流动资产占比约{current_pct:.1f}%。"
        if non_current_ratio > 0.5:
            asset_structure += "较高的非流动资产占比表明企业属于重资产运营模式，高额的固定资产和在建工程通常反映产能扩张或新产线投入，需关注新增折旧对利润的侵蚀和产能利用率。"
        else:
            asset_structure += "资产结构相对轻量，非流动资产占比低于50%。"
        lines.append(asset_structure)
    else:
        lines.append(f"{latest}年总资产数据暂未稳定取得，需补充资产负债表后判断资产结构。")

    # 负债结构分析
    ibd = notes.get("interest_bearing_debt") or {}
    ibd_latest = ibd.get(latest, {})
    ibd_total = ibd_latest.get("total")
    ibd_long = ibd_latest.get("long_term_loan")
    short_loan_latest = short_loan.get(latest)
    notes_payable_latest = notes_payable.get(latest)
    due_latest = due_within_one_year.get(latest)
    total_liabilities_latest = total_liabilities.get(latest)
    debt_ratio_latest = debt_ratio.get(latest)
    if total_liabilities_latest and total_liabilities_latest > 0:
        short_debt_sum = (short_loan_latest or 0) + (notes_payable_latest or 0) + (due_latest or 0)
        short_debt_pct = (short_debt_sum / total_liabilities_latest) * 100 if total_liabilities_latest > 0 else 0
        debt_text = f"{latest}年总负债为{_format_amount_short(total_liabilities_latest)}，资产负债率为{_format_percent(debt_ratio_latest)}。"
        if ibd_total is not None:
            debt_text += f"有息负债合计{_format_amount_short(ibd_total)}"
            if ibd_long is not None:
                debt_text += f"，其中长期借款{_format_amount_short(ibd_long)}"
            debt_text += "。"
        if short_loan_latest and short_loan_latest > 0:
            short_loan_first = short_loan.get(first)
            if short_loan_first and short_loan_first > 0:
                short_growth = (short_loan_latest - short_loan_first) / short_loan_first
                debt_text += f"短期借款为{_format_amount_short(short_loan_latest)}，较{first}年增长{_format_percent(short_growth)}。"
                if short_growth > 0.5:
                    debt_text += "短期借款大幅增长表明公司面临一定的流动性压力，需关注短期偿债安排和融资计划。"
            else:
                debt_text += f"短期借款为{_format_amount_short(short_loan_latest)}。"
        if short_debt_pct > 30:
            debt_text += f"有息负债（短期借款+应付票据+一年内到期非流动负债）占总负债约{short_debt_pct:.1f}%，债务结构偏短期，需关注再融资风险。"
        lines.append(debt_text)
    else:
        lines.append(f"{latest}年负债数据暂未稳定取得，需补充资产负债表后判断负债结构。")

    # 权益变化
    equity_latest = equity.get(latest)
    if equity_latest:
        equity_trend = _trend_text(equity, years)
        lines.append(f"所有者权益近三年呈{equity_trend}趋势，{latest}年为{_format_amount_short(equity_latest)}。权益增长来源需区分外部增资、利润留存还是其他权益变动，以判断资本实力是否实质性增强。")
    else:
        lines.append("所有者权益数据暂未稳定取得，需补充权益明细。")

    return lines


def _profit_quality_analysis(
    years: List[str],
    net_profit: Dict[str, Optional[float]],
    deducted_net_profit: Dict[str, Optional[float]],
    roe: Dict[str, Optional[float]],
    roa: Dict[str, Optional[float]],
    gross_margin: Dict[str, Optional[float]],
    net_margin: Dict[str, Optional[float]],
    operating_cf: Dict[str, Optional[float]],
    revenue: Dict[str, Optional[float]],
    cost: Dict[str, Optional[float]],
    receivable: Dict[str, Optional[float]],
    inventory: Dict[str, Optional[float]],
    receivable_turnover_days: Dict[str, Optional[float]],
    inventory_turnover_days: Dict[str, Optional[float]],
    asset_turnover: Dict[str, Optional[float]],
    profit_cash_bridge: Optional[Dict[str, Any]] = None,
    annual_report_notes: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """盈利质量与营运效率分析。"""
    if not years:
        return ["盈利质量与营运效率数据不足，需补充利润表、现金流量表和周转指标后判断。"]
    latest = years[-1]
    lines: List[str] = []

    # 盈利质量
    roe_latest = roe.get(latest)
    roa_latest = roa.get(latest)
    if roe_latest is not None and roa_latest is not None:
        roe_trend = _trend_text(roe, years)
        roa_trend = _trend_text(roa, years)
        profit_quality = f"{latest}年ROE为{_format_percent(roe_latest)}，ROA为{_format_percent(roa_latest)}。"
        if roe_latest < 0.02:
            profit_quality += "ROE低于2%，公司利用自有资本创造利润的能力较弱，远低于制造业合理水平。"
        elif roe_latest < 0.05:
            profit_quality += "ROE处于较低水平，需结合权益乘数和财务杠杆判断是否为高杠杆驱动的低质量盈利。"
        if roe_trend == "下降" and roa_trend == "下降":
            profit_quality += "ROE和ROA同步下滑，表明盈利能力和资产使用效率均在弱化，需排查资产减值、收入确认质量和费用管控。"
        lines.append(profit_quality)
    else:
        lines.append("ROE/ROA数据暂未稳定取得，需补充权益和资产数据后判断盈利质量。")

    # 扣非净利润与盈利依赖
    notes = annual_report_notes or {}
    government_subsidies = notes.get("government_subsidies") or {}
    subsidy_latest = government_subsidies.get(latest)

    if _all_negative(deducted_net_profit, years):
        subsidy_sentence = ""
        if subsidy_latest is not None and net_profit.get(latest) is not None:
            if net_profit[latest] > 0 and subsidy_latest > net_profit[latest]:
                subsidy_sentence = f"{latest}年其他收益（主要为政府补助）{_format_amount_short(subsidy_latest)}已超过净利润{_format_amount_short(net_profit[latest])}，若扣除该项，公司经营将转为亏损，盈利对非经常性损益依赖极高。"
            elif net_profit[latest] <= 0:
                subsidy_sentence = f"{latest}年其他收益（主要为政府补助）{_format_amount_short(subsidy_latest)}未能覆盖经营亏损，扣除非经常性损益后亏损更为显著。"
        lines.append(f"扣非净利润近三年均为负，表明主营业务尚未实现真正盈利。{subsidy_sentence}净利润表现需剔除非经常性损益后审慎看待，盈利高度依赖政府补助、投资收益或资产处置等非核心来源。")
    elif any(deducted_net_profit.get(year) is not None for year in years):
        lines.append(f"扣非净利润序列为{_available_amount_series(deducted_net_profit, years, '扣非净利润')}，需与净利润差异联动核查政府补助、投资收益和资产处置等非核心利润来源。若扣非利润持续弱于净利润，说明主营造血能力尚未实质修复。")
    else:
        lines.append("[需补充：扣非净利润和非经常性损益明细]，以判断盈利是否依赖非核心来源。")

    # 营运效率：应收/存货与收入/成本增速交叉验证
    previous = years[-2] if len(years) >= 2 else None
    revenue_growth_val = _growth(revenue.get(latest), revenue.get(previous)) if previous else None
    receivable_growth_val = _growth(receivable.get(latest), receivable.get(previous)) if previous else None
    inventory_growth_val = _growth(inventory.get(latest), inventory.get(previous)) if previous else None
    cost_growth_val = _growth(cost.get(latest), cost.get(previous)) if previous else None
    if receivable_growth_val is not None and revenue_growth_val is not None and receivable_growth_val > revenue_growth_val * 1.3:
        lines.append(f"应收账款增速（{_format_percent(receivable_growth_val)}）高于营业收入增速（{_format_percent(revenue_growth_val)}），规模扩张伴随营运资金占用增加，需重点核查客户信用政策、账龄结构和期后回款质量。")
    if inventory_growth_val is not None and cost_growth_val is not None and inventory_growth_val > cost_growth_val * 1.3:
        lines.append(f"存货增速（{_format_percent(inventory_growth_val)}）高于营业成本增速（{_format_percent(cost_growth_val)}），库存去化可能慢于销售增长，需关注跌价准备和产销匹配情况。")

    # 营运效率
    receivable_days = receivable_turnover_days.get(latest)
    inventory_days = inventory_turnover_days.get(latest)
    asset_turn = asset_turnover.get(latest)
    if receivable_days is not None or inventory_days is not None:
        efficiency_text = f"{latest}年"
        if receivable_days is not None:
            efficiency_text += f"应收账款周转天数为{_format_days(receivable_days)}"
            receivable_trend = _trend_text(receivable_turnover_days, years)
            if receivable_trend == "增长":
                efficiency_text += "，呈拉长趋势，表明公司对下游客户的账期政策有所放宽或回款质量下降，需关注期后回款和坏账计提充分性。"
            elif receivable_trend == "下降":
                efficiency_text += "，呈缩短趋势，回款效率有所改善。"
            else:
                efficiency_text += "。"
        if inventory_days is not None:
            efficiency_text += f"存货周转天数为{_format_days(inventory_days)}"
            inventory_trend = _trend_text(inventory_turnover_days, years)
            if inventory_trend == "增长":
                efficiency_text += "，周转放缓，可能因行业去库存周期或产品滞销，需关注跌价准备和去化压力。"
            elif inventory_trend == "下降":
                efficiency_text += "，周转加快，库存管理效率提升。"
            else:
                efficiency_text += "。"
        if asset_turn is not None:
            efficiency_text += f"总资产周转率为{_format_ratio(asset_turn)}，"
            if asset_turn < 0.3:
                efficiency_text += "资产使用效率偏低，大量资产沉淀未有效转化为收入。"
            elif asset_turn < 0.6:
                efficiency_text += "资产使用效率处于中等水平。"
            else:
                efficiency_text += "资产使用效率较好。"
        lines.append(efficiency_text)
    else:
        lines.append("[需补充：应收账款周转天数、存货周转天数和总资产周转率]，以判断营运效率变化。")

    # 现金流质量
    if profit_cash_bridge:
        lines.append(str(profit_cash_bridge.get("bridge_explanation") or ""))
        lines.append(str(profit_cash_bridge.get("credit_implication") or ""))
    else:
        operating_cf_latest = operating_cf.get(latest)
        net_profit_latest = net_profit.get(latest)
        if operating_cf_latest is not None and net_profit_latest is not None:
            if net_profit_latest > 0 and operating_cf_latest < 0:
                lines.append(f"账面净利润{_format_amount_short(net_profit_latest)}为正但经营现金流{_format_amount_short(operating_cf_latest)}为负，利润现金含量不足，通常指向回款滞后、应收和存货占用或收入确认时点变化。")
            elif net_profit_latest < 0 and operating_cf_latest >= 0:
                lines.append(f"利润承压但经营现金流仍为正，现金流表现阶段性优于账面利润。该情形常见于重资产制造企业，可能由折旧摊销等非现金成本拉低利润；但若扣非净利润持续为负，仍说明主营盈利基础尚未完全修复。")
            else:
                lines.append(f"净利润和经营现金流同向，需进一步观察经营现金流对净利润的覆盖倍数。")
        else:
            lines.append("[需补充：经营现金流和净利润数据]，以判断利润现金含量。")

    return [line for line in lines if line]


def _solvency_analysis(
    years: List[str],
    current_ratio: Dict[str, Optional[float]],
    quick_ratio: Dict[str, Optional[float]],
    cash_to_short_debt: Dict[str, Optional[float]],
    ebitda_interest_coverage: Dict[str, Optional[float]],
    interest_coverage: Dict[str, Optional[float]],
    operating_cf: Dict[str, Optional[float]],
    investing_cf: Dict[str, Optional[float]],
    financing_cf: Dict[str, Optional[float]],
    total_liabilities: Dict[str, Optional[float]],
    short_debt: Dict[str, Optional[float]],
    debt_ratio: Dict[str, Optional[float]],
    cash_type: Dict[str, str],
    profit_cash_bridge: Optional[Dict[str, Any]] = None,
    financial_expense: Optional[Dict[str, Optional[float]]] = None,
    interest_bearing_debt: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """偿债能力与财务信号异常分析。"""
    if not years:
        return ["偿债能力数据不足，需补充流动比率、速动比率、现金短债比和利息保障倍数后判断。"]
    latest = years[-1]
    first = years[0]
    lines: List[str] = []

    # 短期偿债能力
    current_ratio_latest = current_ratio.get(latest)
    quick_ratio_latest = quick_ratio.get(latest)
    cash_to_short_latest = cash_to_short_debt.get(latest)
    if current_ratio_latest is not None:
        solvency_text = f"{latest}年流动比率为{_format_ratio(current_ratio_latest)}，速动比率为{_format_ratio(quick_ratio_latest)}。"
        if current_ratio_latest < 1:
            solvency_text += "流动比率低于1，短期偿债安全边际不足，需警惕流动负债集中到期风险。"
        elif current_ratio_latest < 1.5:
            solvency_text += "流动比率处于1-1.5区间，短期偿债能力尚可，但需关注流动资产中应收账款和存货的变现能力。"
        else:
            solvency_text += "流动比率高于1.5，短期偿债能力相对充足。"

        # 流动比率变化趋势
        if len(years) >= 2:
            current_ratio_first = current_ratio.get(first)
            if current_ratio_first and current_ratio_first > 0:
                ratio_change = ((current_ratio_latest - current_ratio_first) / current_ratio_first) * 100
                if abs(ratio_change) > 10:
                    direction = "下降" if ratio_change < 0 else "上升"
                    solvency_text += f"较{first}年流动比率{direction}{abs(ratio_change):.1f}个百分点，"
                    if ratio_change < 0:
                        solvency_text += "主要因短期借款增加或流动资产占用增加导致，需结合未来12个月债务到期安排判断。"
                    else:
                        solvency_text += "流动性边际改善。"

        if cash_to_short_latest is not None:
            solvency_text += f"现金短债比为{_format_ratio(cash_to_short_latest)}，"
            if cash_to_short_latest < 1:
                solvency_text += "货币资金对短期有息债务的覆盖不足，需关注短期再融资安排和银行授信额度。"
            else:
                solvency_text += "货币资金对短期有息债务有一定覆盖能力。"
        lines.append(solvency_text)
    else:
        lines.append("[需补充：流动比率和速动比率]，以判断短期偿债能力。")

    # 利息保障能力
    ebitda_coverage = ebitda_interest_coverage.get(latest)
    interest_cov = interest_coverage.get(latest)
    if ebitda_coverage is not None or interest_cov is not None:
        interest_text = f"{latest}年"
        if ebitda_coverage is not None:
            interest_text += f"EBITDA利息保障倍数为{_format_ratio(ebitda_coverage)}，"
            if ebitda_coverage < 3:
                interest_text += "利息偿付能力偏弱，盈利对利息支出的覆盖不足，需关注财务费用变化和债务成本。"
            elif ebitda_coverage < 5:
                interest_text += "利息偿付能力一般，处于安全边际边缘。"
            else:
                interest_text += "利息偿付能力较强。"
        if interest_cov is not None:
            interest_text += f"利润总额利息保障倍数为{_format_ratio(interest_cov)}。"
        lines.append(interest_text)
    else:
        lines.append("[需补充：利息保障倍数]，以判断利息偿付能力。")

    # 现金流覆盖
    operating_cf_latest = operating_cf.get(latest)
    total_liabilities_latest = total_liabilities.get(latest)
    short_debt_latest = short_debt.get(latest)
    if operating_cf_latest is not None and total_liabilities_latest and total_liabilities_latest > 0:
        cf_coverage = operating_cf_latest / total_liabilities_latest if total_liabilities_latest > 0 else None
        if cf_coverage is not None:
            cf_text = f"{latest}年经营活动现金流净额为{_format_amount_short(operating_cf_latest)}，经营现金流对总负债的覆盖比率为{_format_ratio(cf_coverage)}。"
            if cf_coverage < 0.1:
                cf_text += "经营现金流对总负债的覆盖能力极低，长期债务安全性需重点关注，需核查持续经营现金流生成能力。"
            elif cf_coverage < 0.3:
                cf_text += "经营现金流对总负债的覆盖能力偏低，需关注债务到期安排和再融资计划。"
            else:
                cf_text += "经营现金流对总负债有一定覆盖能力。"
            lines.append(cf_text)
    else:
        lines.append("[需补充：经营现金流和负债数据]，以判断现金流覆盖能力。")

    # 经营现金流对有息负债与利息的覆盖
    ibd = interest_bearing_debt or {}
    ibd_latest = ibd.get(latest, {})
    ibd_total = ibd_latest.get("total")
    financial_expense_latest = (financial_expense or {}).get(latest)
    if operating_cf_latest is not None and ibd_total and ibd_total > 0:
        cf_to_ibd = operating_cf_latest / ibd_total
        ibd_text = f"{latest}年经营现金流对有息负债（短借+长借+应付债券+租赁负债+一年内到期非流动负债）的覆盖比率为{_format_ratio(cf_to_ibd)}。"
        if cf_to_ibd < 0.2:
            ibd_text += "该比率偏低，表明经营现金流对带息债务本金的偿还能力有限，长期债务安全性需重点关注。"
        elif cf_to_ibd < 0.5:
            ibd_text += "该比率处于中等偏低水平，需结合债务到期分布和再融资安排判断偿债压力。"
        else:
            ibd_text += "该比率尚可，经营现金流对有息债务具备一定覆盖能力。"
        lines.append(ibd_text)
    if operating_cf_latest is not None and financial_expense_latest is not None and financial_expense_latest > 0:
        cf_interest_coverage = operating_cf_latest / financial_expense_latest
        if cf_interest_coverage >= 0:
            lines.append(f"以经营现金流/财务费用衡量的现金流利息保障倍数为{_format_ratio(cf_interest_coverage)}，反映经营现金流对利息支出的实际覆盖能力。")

    # 三大现金流趋势与偿债含义
    if all(cf is not None for cf in [operating_cf_latest, investing_cf.get(latest), financing_cf.get(latest)]):
        investing_latest = investing_cf.get(latest) or 0
        financing_latest = financing_cf.get(latest) or 0
        cf_trend_text = f"现金流方面，{latest}年经营活动现金流净额为{_format_amount_short(operating_cf_latest)}，投资活动现金流净额为{_format_amount_short(investing_latest)}，筹资活动现金流净额为{_format_amount_short(financing_latest)}。"
        if len(years) >= 2:
            prev = years[-2]
            operating_prev = operating_cf.get(prev)
            investing_prev = investing_cf.get(prev)
            if operating_prev is not None and operating_prev != 0:
                ocf_change = (operating_cf_latest - operating_prev) / abs(operating_prev)
                cf_trend_text += f"经营现金流较{prev}年{_format_percent(ocf_change)}，"
                if ocf_change < -0.2:
                    cf_trend_text += "主要因应收账款和存货占用资金增加或回款放缓，需关注营运资本管理。"
                elif ocf_change > 0.2:
                    cf_trend_text += "经营现金流生成能力有所改善。"
                else:
                    cf_trend_text += "经营现金流基本稳定。"
            if investing_prev is not None:
                if investing_latest < 0 and investing_prev < 0:
                    cf_trend_text += "投资活动现金流持续净流出，反映公司在产能扩张或长期资产上的持续投入。"
                elif investing_latest < 0:
                    cf_trend_text += "投资活动现金流净流出，需结合资本开支计划和项目回报期判断资金缺口。"
            if financing_latest < 0:
                cf_trend_text += "筹资活动现金流净流出，表明公司融资需求边际减弱或处于偿债周期。"
            elif financing_latest > 0:
                cf_trend_text += "筹资活动现金流净流入，表明公司仍有外部融资需求以支撑经营和投资。"
        lines.append(cf_trend_text)

    # 现金流类型分析
    if cash_type:
        cash_type_items = []
        for year in years:
            ct = cash_type.get(year, "数据不足")
            cash_type_items.append(f"{year}年：{ct}")
        cash_type_text = "近三年现金流类型分别为：" + "; ".join(cash_type_items) + "。"
        lines.append(cash_type_text)

    # 利润-现金流桥诊断
    if profit_cash_bridge:
        bridge_conclusion = profit_cash_bridge.get("conclusion")
        if bridge_conclusion:
            lines.append(bridge_conclusion)
        heavy_asset = profit_cash_bridge.get("heavy_asset_judgement")
        if heavy_asset:
            lines.append(heavy_asset)
        investment = profit_cash_bridge.get("investment_income_judgement")
        if investment:
            lines.append(investment)

    # 异常信号汇总
    debt_ratio_latest = debt_ratio.get(latest)
    risk_signals: List[str] = []
    if debt_ratio_latest and debt_ratio_latest > 0.7:
        risk_signals.append("资产负债率高于70%")
    if current_ratio_latest and current_ratio_latest < 1:
        risk_signals.append("流动比率低于1")
    if operating_cf_latest and operating_cf_latest < 0:
        risk_signals.append("经营现金流为负")
    if cash_to_short_latest and cash_to_short_latest < 1:
        risk_signals.append("现金短债比不足")
    if ebitda_coverage and ebitda_coverage < 3:
        risk_signals.append("EBITDA利息保障倍数偏低")
    if risk_signals:
        lines.append(f"财务信号异常汇总：{', '.join(risk_signals)}。上述信号叠加时，需编制未来12个月债务到期和现金流预测，评估是否需要新增授信被动补流。")

    return [line for line in lines if line]


def _row(label: str, values: Dict[str, Optional[float]], years: List[str], formatter=_format_amount) -> Dict[str, Any]:
    return {"item": _sanitize_metric_label(label), "values": {year: formatter(values.get(year)) for year in years}}


def _ratio_row(label: str, values: Dict[str, Optional[float]], years: List[str], formatter=_format_percent) -> Dict[str, Any]:
    return {"item": _sanitize_metric_label(label), "values": {year: formatter(values.get(year)) for year in years}}


def _latest_growth_text(values: Dict[str, Optional[float]], years: List[str]) -> str:
    if len(years) < 2:
        return "数据不足"
    latest, previous = years[-1], years[-2]
    return _format_percent(_growth(values.get(latest), values.get(previous)))


def _records_for_codeact(df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    normalized = df.where(pd.notna(df), None)
    return normalized.to_dict(orient="records")


def _run_financial_codeact(financial_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    payload = {
        "financial_data": {
            "income_statement": _records_for_codeact(financial_data.get("income_statement")),
            "balance_sheet": _records_for_codeact(financial_data.get("balance_sheet")),
            "cash_flow": _records_for_codeact(financial_data.get("cash_flow")),
        }
    }
    ratios = run_codeact_tool("calculate_financial_ratios", payload)
    validation = run_codeact_tool("validate_financial_statements", payload)
    return {
        "ratios": ratios,
        "validation": validation,
        "metrics": (ratios.get("result") or {}).get("metrics") if ratios.get("success") else {},
        "growth_metrics": (ratios.get("result") or {}).get("growth_metrics") if ratios.get("success") else {},
        "validation_passed": (validation.get("result") or {}).get("passed") if validation.get("success") else None,
        "validation_issues": (validation.get("result") or {}).get("issues") if validation.get("success") else [],
        "validation_warnings": (validation.get("result") or {}).get("warnings") if validation.get("success") else [],
        "tool_meta": {
            "ratios_elapsed_ms": ratios.get("elapsed_ms"),
            "validation_elapsed_ms": validation.get("elapsed_ms"),
            "ratios_success": ratios.get("success"),
            "validation_success": validation.get("success"),
        },
    }


def _codeact_evidence_id(enterprise_name: str, key: str, year: str, value: Any) -> str:
    import hashlib

    raw = f"codeact|financial|{enterprise_name}|{key}|{year}|{value}"
    return "ev_codeact_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _format_codeact_metric(value: Any, metric_type: str = "ratio") -> str:
    if value is None:
        return "数据不可用"
    if not isinstance(value, (int, float)):
        return str(value)
    if metric_type == "amount":
        return _format_amount_short(float(value))
    if metric_type == "days":
        return _format_days(float(value))
    if metric_type == "multiple":
        return _format_ratio(float(value))
    return _format_percent(float(value))


def build_codeact_financial_evidence(enterprise_name: str, codeact_analysis: Dict[str, Any], source: str = "已解析三大表") -> List[Dict[str, Any]]:
    """Convert CodeAct financial results into auditable evidence items."""
    metrics_by_year = codeact_analysis.get("metrics") or {}
    validation_issues = codeact_analysis.get("validation_issues") or []
    validation_warnings = codeact_analysis.get("validation_warnings") or []
    if not isinstance(metrics_by_year, dict):
        metrics_by_year = {}
    evidence: List[Dict[str, Any]] = []
    metric_specs = {
        "cost": ("营业成本", "利润表营业成本科目", "amount"),
        "deducted_net_profit": ("扣非净利润", "扣除非经常性损益后的净利润科目", "amount"),
        "gross_margin": ("毛利率", "毛利润 / 营业收入", "ratio"),
        "net_margin": ("销售净利率", "净利润 / 营业收入", "ratio"),
        "debt_ratio": ("资产负债率", "负债合计 / 资产总计", "ratio"),
        "current_ratio": ("流动比率", "流动资产合计 / 流动负债合计", "multiple"),
        "quick_ratio": ("速动比率", "(流动资产合计 - 存货) / 流动负债合计", "multiple"),
        "short_loan": ("短期借款", "资产负债表短期借款科目", "amount"),
        "cash_to_short_debt": ("现金短债比", "货币资金 / (短期借款 + 应付票据 + 一年内到期的非流动负债)", "multiple"),
        "receivable_to_revenue": ("应收账款/营业收入", "应收账款 / 营业收入", "ratio"),
        "receivable_turnover_days": ("应收账款周转天数", "应收账款 / 营业收入 * 365", "days"),
        "inventory_turnover_days": ("存货周转天数", "存货 / 营业成本 * 365", "days"),
        "operating_cashflow_to_revenue": ("经营现金流/营业收入", "经营活动现金流量净额 / 营业收入", "ratio"),
        "operating_cashflow_to_net_profit": ("经营现金流/净利润", "经营活动现金流量净额 / 净利润", "multiple"),
        "ebitda_interest_coverage": ("EBITDA利息保障倍数", "(净利润 + 财务费用) / 财务费用；缺少折旧摊销时为近似口径", "multiple"),
    }
    for year in sorted(str(year) for year in metrics_by_year.keys())[-3:]:
        row = metrics_by_year.get(year) or {}
        if not isinstance(row, dict):
            continue
        for key, (label, basis, metric_type) in metric_specs.items():
            value = row.get(key)
            if value is None:
                continue
            display_value = _format_codeact_metric(value, metric_type)
            evidence.append({
                "id": _codeact_evidence_id(enterprise_name, key, year, display_value),
                "label": f"{year}年{label}",
                "value": display_value,
                "claim": f"内部财务计算工具基于三大表计算得出{year}年{label}为{display_value}。",
                "source": "内部财务计算工具",
                "source_name": "内部财务计算工具",
                "source_type": "codeact_financial_metric",
                "agent": "financial",
                "domain": "financial",
                "category": "financial",
                "confidence": 0.92,
                "trust_level": "high",
                "requires_manual_review": False,
                "metadata": {
                    "tool_name": "calculate_financial_ratios",
                    "display_tool_name": "财务指标计算",
                    "metric_key": key,
                    "year": year,
                    "raw_value": value,
                    "calculation_basis": basis,
                    "input_source": source,
                },
            })

    for index, issue in enumerate((validation_issues or []) + (validation_warnings or []), 1):
        if not isinstance(issue, dict):
            continue
        severity = issue.get("severity") or "P1"
        year = str(issue.get("year") or "all")
        code = str(issue.get("code") or f"validation_{index}")
        evidence.append({
            "id": _codeact_evidence_id(enterprise_name, code, year, issue.get("message")),
            "label": f"三大表勾稽校验：{issue.get('message') or code}",
            "value": issue.get("message") or code,
            "claim": f"内部校验发现{issue.get('message') or code}，建议：{issue.get('recommendation') or '需人工复核原始报表'}",
            "source": "内部财务校验工具",
            "source_name": "内部财务校验工具",
            "source_type": "codeact_financial_validation",
            "agent": "financial",
            "domain": "financial",
            "category": "financial",
            "confidence": 0.9,
            "trust_level": "high",
            "requires_manual_review": severity in {"P0", "P1"},
            "metadata": {
                "tool_name": "validate_financial_statements",
                "display_tool_name": "三大表勾稽校验",
                "severity": severity,
                "validation_code": code,
                "year": issue.get("year"),
                "recommendation": issue.get("recommendation"),
                "raw_issue": issue,
            },
        })
    return evidence


def _numeric_sign(raw: Any) -> int:
    """Return -1/0/1 for a raw numeric or formatted string value."""
    if raw is None:
        return 0
    text = str(raw).strip()
    if not text or text in ("数据不可用", "--", "-", "nan"):
        return 0
    cleaned = re.sub(r"[^\d.\-]", "", text.split("（")[0].split("(")[0])
    try:
        number = float(cleaned)
        return 1 if number > 0 else -1 if number < 0 else 0
    except ValueError:
        return 0


def build_financial_analysis_report(
    enterprise_name: str,
    financial_data: Dict[str, pd.DataFrame],
    public_context: Optional[List[Dict[str, Any]]] = None,
    generated_from: str = "用户上传财报",
    stock_code: str = "",
    source_type: str = "financial_statement",
    cross_provider_reconciliation: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    annual_report_notes: Optional[Dict[str, Any]] = None,
    financial_business_hints: Optional[List[str]] = None,
    industry_context: Optional[Dict[str, Any]] = None,
    business_segments: Optional[List[Dict[str, Any]]] = None,
    annual_business_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """基于三大表生成银行财务状况分析报告结构。"""
    income = financial_data.get("income_statement")
    balance = financial_data.get("balance_sheet")
    cash_flow = financial_data.get("cash_flow")
    codeact_analysis = _run_financial_codeact(financial_data)
    codeact_evidence = build_codeact_financial_evidence(enterprise_name, codeact_analysis)
    years = sorted(set(_year_columns(income)) | set(_year_columns(balance)) | set(_year_columns(cash_flow)))
    years = years[-3:] if len(years) > 3 else years
    codeact_evidence_refs = [item["id"] for item in codeact_evidence if item.get("id")]

    annual_report_notes = annual_report_notes or {}
    business_segments = annual_report_notes.get("business_segments") or []
    rd_expenses = annual_report_notes.get("rd_expenses") or {}
    government_subsidies = annual_report_notes.get("government_subsidies") or {}
    intangible_assets = annual_report_notes.get("intangible_assets") or {}
    development_expenses = annual_report_notes.get("development_expenses") or {}
    interest_bearing_debt = annual_report_notes.get("interest_bearing_debt") or {}

    structured_package = build_structured_financial_package(
        enterprise_name=enterprise_name,
        years=years,
        codeact_analysis=codeact_analysis,
        generated_from=generated_from,
        stock_code=stock_code,
        source_type=source_type,
        cross_provider_reconciliation=cross_provider_reconciliation,
        evidence_refs=codeact_evidence_refs,
    )

    revenue = _series(income, ["营业收入", "主营业务收入", "收入"], years)
    cost = _series(income, ["营业成本", "主营业务成本"], years)
    gross_profit = {year: (revenue.get(year) - cost.get(year)) if revenue.get(year) is not None and cost.get(year) is not None else _value_by_item(income, ["毛利润", "毛利"], year) for year in years}
    net_profit = _series(income, ["净利润"], years)
    deducted_net_profit = _series(income, ["扣除非经常性损益后的净利润", "扣非净利润", "归属于上市公司股东的扣除非经常性损益的净利润"], years)
    financial_expense = _series(income, ["财务费用"], years)
    investment_income = _series(income, ["投资收益", "投资净收益"], years)
    asset_impairment = _series(income, ["资产减值损失", "资产减值损失(损失以-号填列)", "资产减值损失（损失以-号填列）"], years)
    credit_impairment = _series(income, ["信用减值损失", "信用减值损失(损失以-号填列)", "信用减值损失（损失以-号填列）"], years)
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
    due_within_one_year = _series(balance, ["一年内到期的非流动负债"], years)
    payable = _series(balance, ["应付账款"], years)
    equity = _series(balance, ["所有者权益(或股东权益)合计", "所有者权益", "股东权益", "净资产"], years)
    paid_in_capital = _series(balance, ["实收资本"], years)
    capital_reserve = _series(balance, ["资本公积"], years)
    retained_earnings = _series(balance, ["未分配利润"], years)

    operating_cf = _series(cash_flow, ["经营活动产生的现金流量净额", "经营活动产生现金流量净额", "经营活动现金流"], years)
    investing_cf = _series(cash_flow, ["投资活动产生的现金流量净额", "投资活动现金流"], years)
    financing_cf = _series(cash_flow, ["筹资活动产生的现金流量净额", "筹资活动现金流"], years)
    depreciation_amortization = _series(cash_flow, ["固定资产折旧、油气资产折耗、生产性生物资产折旧", "固定资产折旧", "折旧与摊销", "折旧摊销", "无形资产摊销", "长期待摊费用摊销"], years)

    debt_ratio = {year: _safe_div(total_liabilities.get(year), total_assets.get(year)) for year in years}
    current_ratio = {year: _safe_div(current_assets.get(year), current_liabilities.get(year)) for year in years}
    quick_ratio = {year: _safe_div((current_assets.get(year) or 0) - (inventory.get(year) or 0), current_liabilities.get(year)) if current_assets.get(year) is not None else None for year in years}
    gross_margin = {year: _safe_div(gross_profit.get(year), revenue.get(year)) for year in years}
    net_margin = {year: _safe_div(net_profit.get(year), revenue.get(year)) for year in years}
    roa = {year: _safe_div(net_profit.get(year), total_assets.get(year)) for year in years}
    roe = {year: _safe_div(net_profit.get(year), equity.get(year)) for year in years}
    receivable_turnover = {year: _safe_div(revenue.get(year), receivable.get(year)) for year in years}
    inventory_turnover = {year: _safe_div(cost.get(year), inventory.get(year)) for year in years}
    receivable_turnover_days = {year: _safe_div(receivable.get(year), revenue.get(year) / 365 if revenue.get(year) not in (None, 0) else None) for year in years}
    inventory_turnover_days = {year: _safe_div(inventory.get(year), cost.get(year) / 365 if cost.get(year) not in (None, 0) else None) for year in years}
    asset_turnover = {year: _safe_div(revenue.get(year), total_assets.get(year)) for year in years}
    revenue_growth = {year: _growth(revenue.get(year), revenue.get(years[index - 1])) if index > 0 else None for index, year in enumerate(years)}
    profit_growth = {year: _growth(net_profit.get(year), net_profit.get(years[index - 1])) if index > 0 else None for index, year in enumerate(years)}
    capital_growth = {year: _growth(equity.get(year), equity.get(years[index - 1])) if index > 0 else None for index, year in enumerate(years)}
    ebitda_proxy = {year: (net_profit.get(year) + financial_expense.get(year)) if net_profit.get(year) is not None and financial_expense.get(year) is not None else None for year in years}
    interest_coverage = {year: _safe_div((total_profit.get(year) or operating_profit.get(year)), financial_expense.get(year)) for year in years}
    ebitda_interest_coverage = {year: _safe_div(ebitda_proxy.get(year), financial_expense.get(year)) for year in years}
    receivable_to_revenue = {year: _safe_div(receivable.get(year), revenue.get(year)) for year in years}
    short_debt = {year: sum(value for value in [short_loan.get(year), notes_payable.get(year), due_within_one_year.get(year)] if value is not None) if any(value is not None for value in [short_loan.get(year), notes_payable.get(year), due_within_one_year.get(year)]) else None for year in years}
    cash_to_short_debt = {year: _safe_div(cash.get(year), short_debt.get(year)) for year in years}

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
    if cash_to_short_debt.get(latest) is not None and cash_to_short_debt[latest] < 1:
        risk_items.append("现金短债比低于1，需关注短期有息债务覆盖能力。")
    if receivable_turnover_days.get(latest) is not None and receivable_turnover_days[latest] > 180:
        risk_items.append("应收账款周转天数超过180天，需关注账期拉长和回款质量。")
    if inventory_turnover_days.get(latest) is not None and inventory_turnover_days[latest] > 180:
        risk_items.append("存货周转天数超过180天，需关注跌价准备和产品去化压力。")
    if not risk_items:
        risk_items.append("未发现明显重大财务异常，但仍需结合审计意见、授信用途和行业景气度复核。")

    profit_cash_bridge = _build_profit_cash_bridge(
        years,
        net_profit,
        deducted_net_profit,
        operating_cf,
        depreciation_amortization,
        asset_impairment,
        credit_impairment,
        investment_income,
        fixed_assets,
        construction,
    )

    risk_score = max(50, 85 - max(0, len(risk_items) - 1) * 10)
    risk_rating = "low" if risk_score >= 80 else "medium" if risk_score >= 60 else "high"
    recommendation = "财务指标整体可接受，仍需结合审计意见、授信用途、担保结构和行业景气度综合判断。" if risk_rating == "low" else "财务指标存在需核实事项，应重点复核重点科目、现金流质量和偿债压力。" if risk_rating == "medium" else "财务风险较高，应待重大风险排查和关键科目核验后再形成授信意见。"

    cash_type = {
        year: "".join("正" if (value or 0) >= 0 else "负" for value in [operating_cf.get(year), investing_cf.get(year), financing_cf.get(year)])
        for year in years
    }

    # 4-core section structure aligned with bank DD best practice
    # 3.1 Revenue & Profit / 3.2 Balance Sheet / 3.3 Profit Quality & Efficiency / 3.4 Solvency & Anomaly Signals
    income_analysis = _income_statement_analysis(
        years, revenue, cost, net_profit, deducted_net_profit, gross_margin, net_margin, revenue_growth, profit_cash_bridge, annual_report_notes
    )
    balance_analysis = _balance_sheet_analysis(
        years, total_assets, current_assets, receivable, inventory, fixed_assets, construction,
        total_liabilities, current_liabilities, short_loan, notes_payable, due_within_one_year,
        equity, debt_ratio, current_ratio, annual_report_notes,
    )
    quality_analysis = _profit_quality_analysis(
        years, net_profit, deducted_net_profit, roe, roa, gross_margin, net_margin,
        operating_cf, revenue, cost, receivable, inventory, receivable_turnover_days, inventory_turnover_days, asset_turnover, profit_cash_bridge,
        annual_report_notes,
    )
    solvency_analysis = _solvency_analysis(
        years, current_ratio, quick_ratio, cash_to_short_debt, ebitda_interest_coverage,
        interest_coverage, operating_cf, investing_cf, financing_cf, total_liabilities, short_debt, debt_ratio, cash_type, profit_cash_bridge,
        financial_expense=financial_expense,
        interest_bearing_debt=interest_bearing_debt,
    )

    # Risk signal per section
    section_risks_31: List[str] = []
    if _numeric_sign(revenue_growth.get(latest)) > 0 and (_numeric_sign(profit_growth.get(latest)) < 0 or _all_negative(net_profit, years)):
        section_risks_31.append("收入增长未能转化为利润，规模扩张与盈利能力背离")
    if _all_negative(deducted_net_profit, years):
        section_risks_31.append("扣非净利润持续为负，主营业务尚未实现真正盈利")
    if margin_trend_text := _trend_text(gross_margin, years):
        if margin_trend_text == "下降":
            margin_risk = "毛利率持续下滑，需排查产能过剩、价格下行、折旧摊销或产品结构变化"
            # 若年报深度归因已给出具体原因（如产能过剩/价格下行），在风险提示里点明，提升具体性。
            attribution = (annual_report_notes or {}).get("attribution") or {}
            margin_drivers = attribution.get("margin_drivers") or []
            if margin_drivers:
                top_driver = margin_drivers[0].get("factor") or ""
                if top_driver:
                    margin_risk += f"（年报管理层归因：{top_driver}）"
            section_risks_31.append(margin_risk)
    if not section_risks_31:
        section_risks_31.append("收入与利润结构无显著异常，但需结合审计报告和报表附注复核")

    section_risks_32: List[str] = []
    short_loan_first = short_loan.get(years[0]) if years else None
    short_loan_latest = short_loan.get(latest)
    if short_loan_first and short_loan_first > 0 and short_loan_latest and short_loan_latest > 0:
        if (short_loan_latest - short_loan_first) / short_loan_first > 0.5:
            section_risks_32.append("短期借款大幅增长，面临流动性压力和再融资风险")
    if debt_ratio.get(latest) is not None and debt_ratio.get(latest) > 0.7:
        section_risks_32.append("资产负债率高于70%，杠杆水平偏高")
    if not section_risks_32:
        section_risks_32.append("资产负债结构无显著异常，但需关注资产扩张效率和权益增长来源")

    section_risks_33: List[str] = []
    if _all_negative(deducted_net_profit, years):
        section_risks_33.append("盈利高度依赖非经常性损益，主营造血能力未实质修复")
    rd_trend = _trend_text(receivable_turnover_days, years)
    if rd_trend == "增长":
        section_risks_33.append("应收账款周转天数拉长，回款质量可能下降")
    id_trend = _trend_text(inventory_turnover_days, years)
    if id_trend == "增长":
        section_risks_33.append("存货周转天数拉长，可能存在积压或跌价风险")
    if net_profit.get(latest) is not None and operating_cf.get(latest) is not None:
        if net_profit.get(latest) > 0 and operating_cf.get(latest) < 0:
            section_risks_33.append("账面利润为正但经营现金流为负，利润现金含量不足")
    if not section_risks_33:
        section_risks_33.append("盈利质量与营运效率无显著异常，仍需结合期后回款和库存盘点复核")

    section_risks_34: List[str] = []
    if current_ratio.get(latest) is not None and current_ratio.get(latest) < 1:
        section_risks_34.append("流动比率低于1，短期偿债安全边际不足")
    if cash_to_short_debt.get(latest) is not None and cash_to_short_debt.get(latest) < 1:
        section_risks_34.append("现金短债比不足，货币资金对短期有息债务覆盖能力偏弱")
    if ebitda_interest_coverage.get(latest) is not None and ebitda_interest_coverage.get(latest) < 3:
        section_risks_34.append("EBITDA利息保障倍数偏低，利息偿付能力需关注")
    if operating_cf.get(latest) is not None and total_liabilities.get(latest) and total_liabilities.get(latest) > 0:
        if operating_cf.get(latest) / total_liabilities.get(latest) < 0.1:
            section_risks_34.append("经营现金流对总负债覆盖比率极低，长期债务安全性需重点关注")
    if not section_risks_34:
        section_risks_34.append("偿债能力指标整体可接受，但需编制未来12个月债务到期和现金流预测")

    sections = [
        {
            "title": "三、财务状况与偿债能力",
            "subsections": [
                {
                    "title": "3.1 收入与利润分析",
                    "unit": "",
                    "table": {
                        "columns": years,
                        "rows": [
                            _row("营业收入", revenue, years),
                            _row("营业成本", cost, years),
                            _row("营业毛利润", gross_profit, years),
                            _row("净利润", net_profit, years),
                            _row("扣非净利润", deducted_net_profit, years),
                            _row("研发费用", rd_expenses, years),
                            _ratio_row("毛利率", gross_margin, years),
                            _ratio_row("销售净利率", net_margin, years),
                        ],
                    },
                    "business_segments": business_segments,
                    "analysis": income_analysis,
                    "risk提示": "；".join(section_risks_31),
                },
                {
                    "title": "3.2 资产负债分析",
                    "unit": "",
                    "table": {
                        "columns": years,
                        "rows": [
                            _row("总资产", total_assets, years),
                            _row("货币资金", cash, years),
                            _row("应收账款", receivable, years),
                            _row("存货", inventory, years),
                            _row("固定资产", fixed_assets, years),
                            _row("在建工程", construction, years),
                            _row("无形资产", intangible_assets, years),
                            _row("开发支出", development_expenses, years),
                            _row("短期借款", short_loan, years),
                            _row("有息负债合计", {y: (interest_bearing_debt.get(y) or {}).get("total") for y in years}, years),
                            _row("总负债", total_liabilities, years),
                            _ratio_row("资产负债率", debt_ratio, years),
                        ],
                    },
                    "analysis": balance_analysis,
                    "risk提示": "；".join(section_risks_32),
                },
                {
                    "title": "3.3 盈利质量与营运效率",
                    "unit": "",
                    "table": {
                        "columns": years,
                        "rows": [
                            _row("其他收益", government_subsidies, years),
                            _ratio_row("ROE", roe, years),
                            _ratio_row("ROA", roa, years),
                            _ratio_row("应收账款周转天数", receivable_turnover_days, years, _format_days),
                            _ratio_row("存货周转天数", inventory_turnover_days, years, _format_days),
                            _ratio_row("总资产周转率", asset_turnover, years, _format_ratio),
                            _ratio_row("经营现金流/净利润", {y: _safe_div(operating_cf.get(y), net_profit.get(y)) for y in years}, years, _format_ratio),
                        ],
                    },
                    "analysis": quality_analysis,
                    "risk提示": "；".join(section_risks_33),
                },
                {
                    "title": "3.4 偿债能力与财务信号异常",
                    "unit": "",
                    "table": {
                        "columns": years,
                        "rows": [
                            _ratio_row("流动比率", current_ratio, years, _format_ratio),
                            _ratio_row("速动比率", quick_ratio, years, _format_ratio),
                            _ratio_row("现金短债比", cash_to_short_debt, years, _format_ratio),
                            _ratio_row("EBITDA利息保障倍数", ebitda_interest_coverage, years, _format_ratio),
                            _ratio_row("利息保障倍数", interest_coverage, years, _format_ratio),
                            _ratio_row("资产负债率", debt_ratio, years),
                        ],
                    },
                    "analysis": solvency_analysis,
                    "risk提示": "；".join(section_risks_34),
                    "risks": risk_items,
                },
            ],
        },
    ]

    key_metrics = {
        "latest_year": latest,
        "revenue": _format_amount_short(revenue.get(latest)),
        "net_profit": _format_amount_short(net_profit.get(latest)),
        "deducted_net_profit": _format_amount_short(deducted_net_profit.get(latest)),
        "cost": _format_amount_short(cost.get(latest)),
        "short_loan": _format_amount_short(short_loan.get(latest)),
        "gross_margin": _format_percent(gross_margin.get(latest)),
        "net_margin": _format_percent(net_margin.get(latest)),
        "debt_ratio": _format_percent(debt_ratio.get(latest)),
        "current_ratio": _format_ratio(current_ratio.get(latest)),
        "operating_cash_flow": _format_amount_short(operating_cf.get(latest)),
        "depreciation_amortization": _format_amount_short(depreciation_amortization.get(latest)),
        "asset_impairment": _format_amount_short(asset_impairment.get(latest)),
        "credit_impairment": _format_amount_short(credit_impairment.get(latest)),
        "investment_income": _format_amount_short(investment_income.get(latest)),
        "receivable": _format_amount_short(receivable.get(latest)),
        "revenue_growth": _format_percent(revenue_growth.get(latest)),
        "profit_growth": _format_percent(profit_growth.get(latest)),
        "revenue_cagr": _format_percent(_cagr(revenue, years)),
        "receivable_to_revenue": _format_percent(receivable_to_revenue.get(latest)),
        "receivable_growth": _format_percent(_growth(receivable.get(latest), receivable.get(years[-2])) if len(years) >= 2 else None),
        "debt_ratio_change": _format_percent(_pct_delta(debt_ratio.get(latest), debt_ratio.get(years[0])) if years else None),
        "current_ratio_change": _format_ratio(_pct_delta(current_ratio.get(latest), current_ratio.get(years[0])) if years else None),
        "operating_cf_to_net_profit": _format_ratio(_safe_div(operating_cf.get(latest), net_profit.get(latest))),
        "inventory_turnover_days": _format_days(inventory_turnover_days.get(latest)),
        "receivable_turnover_days": _format_days(receivable_turnover_days.get(latest)),
        "cash_to_short_debt": _format_ratio(cash_to_short_debt.get(latest)),
        "ebitda_interest_coverage": _format_ratio(ebitda_interest_coverage.get(latest)),
        "rd_expense": _format_amount_short(rd_expenses.get(latest)),
        "rd_expense_ratio": _format_percent(_safe_div(rd_expenses.get(latest), revenue.get(latest))),
        "government_subsidy": _format_amount_short(government_subsidies.get(latest)),
        "government_subsidy_to_net_profit": _format_ratio(_safe_div(government_subsidies.get(latest), net_profit.get(latest))),
        "intangible_assets": _format_amount_short(intangible_assets.get(latest)),
        "development_expenses": _format_amount_short(development_expenses.get(latest)),
        "interest_bearing_debt": _format_amount_short((interest_bearing_debt.get(latest) or {}).get("total")),
    }
    key_metric_series = {
        "revenue": {year: _format_amount_short(revenue.get(year)) for year in years},
        "cost": {year: _format_amount_short(cost.get(year)) for year in years},
        "net_profit": {year: _format_amount_short(net_profit.get(year)) for year in years},
        "deducted_net_profit": {year: _format_amount_short(deducted_net_profit.get(year)) for year in years},
        "gross_margin": {year: _format_percent(gross_margin.get(year)) for year in years},
        "net_margin": {year: _format_percent(net_margin.get(year)) for year in years},
        "debt_ratio": {year: _format_percent(debt_ratio.get(year)) for year in years},
        "current_ratio": {year: _format_ratio(current_ratio.get(year)) for year in years},
        "operating_cash_flow": {year: _format_amount_short(operating_cf.get(year)) for year in years},
        "depreciation_amortization": {year: _format_amount_short(depreciation_amortization.get(year)) for year in years},
        "asset_impairment": {year: _format_amount_short(asset_impairment.get(year)) for year in years},
        "credit_impairment": {year: _format_amount_short(credit_impairment.get(year)) for year in years},
        "investment_income": {year: _format_amount_short(investment_income.get(year)) for year in years},
        "receivable": {year: _format_amount_short(receivable.get(year)) for year in years},
        "receivable_to_revenue": {year: _format_percent(receivable_to_revenue.get(year)) for year in years},
        "short_loan": {year: _format_amount_short(short_loan.get(year)) for year in years},
        "inventory_turnover_days": {year: _format_days(inventory_turnover_days.get(year)) for year in years},
        "receivable_turnover_days": {year: _format_days(receivable_turnover_days.get(year)) for year in years},
        "cash_to_short_debt": {year: _format_ratio(cash_to_short_debt.get(year)) for year in years},
        "ebitda_interest_coverage": {year: _format_ratio(ebitda_interest_coverage.get(year)) for year in years},
        "rd_expense": {year: _format_amount_short(rd_expenses.get(year)) for year in years},
        "rd_expense_ratio": {year: _format_percent(_safe_div(rd_expenses.get(year), revenue.get(year))) for year in years},
        "government_subsidy": {year: _format_amount_short(government_subsidies.get(year)) for year in years},
        "intangible_assets": {year: _format_amount_short(intangible_assets.get(year)) for year in years},
        "interest_bearing_debt": {year: _format_amount_short((interest_bearing_debt.get(year) or {}).get("total")) for year in years},
    }
    structured_metrics = structured_package.get("metrics") or {}
    financial_dashboard = build_financial_dashboard(
        enterprise_name=enterprise_name,
        years=years,
        metrics={
            "revenue": structured_metrics.get("revenue") or revenue,
            "net_profit": structured_metrics.get("net_profit") or net_profit,
            "gross_margin": structured_metrics.get("gross_margin") or gross_margin,
            "net_margin": structured_metrics.get("net_margin") or net_margin,
            "debt_ratio": structured_metrics.get("debt_ratio") or debt_ratio,
            "current_ratio": structured_metrics.get("current_ratio") or current_ratio,
            "quick_ratio": structured_metrics.get("quick_ratio") or quick_ratio,
            "operating_cf": structured_metrics.get("operating_cashflow") or operating_cf,
            "depreciation_amortization": depreciation_amortization,
            "asset_impairment": asset_impairment,
            "credit_impairment": credit_impairment,
            "investment_income": investment_income,
            "investing_cf": structured_metrics.get("investing_cashflow") or investing_cf,
            "financing_cf": structured_metrics.get("financing_cashflow") or financing_cf,
            "cash": structured_metrics.get("cash") or cash,
            "receivable": structured_metrics.get("receivable") or receivable,
            "inventory": structured_metrics.get("inventory") or inventory,
            "fixed_assets": fixed_assets,
            "construction": construction,
            "short_loan": structured_metrics.get("short_loan") or short_loan,
            "cash_to_short_debt": structured_metrics.get("cash_to_short_debt") or cash_to_short_debt,
            "inventory_turnover_days": structured_metrics.get("inventory_turnover_days") or inventory_turnover_days,
            "receivable_turnover_days": structured_metrics.get("receivable_turnover_days") or receivable_turnover_days,
            "ebitda_interest_coverage": structured_metrics.get("ebitda_interest_coverage") or ebitda_interest_coverage,
            "notes_payable": notes_payable,
            "payable": payable,
            "roe": structured_metrics.get("roe") or roe,
            "roa": structured_metrics.get("roa") or roa,
        },
        evidence_refs=codeact_evidence_refs,
    )
    financial_knowledge_context = build_financial_knowledge_context(
        enterprise_name=enterprise_name,
        key_metrics=key_metrics,
        risk_summary=risk_items,
    )
    narrative = build_financial_narrative(
        enterprise_name=enterprise_name,
        years=years,
        key_metrics=key_metrics,
        risk_summary=risk_items,
        recommendation=recommendation,
        risk_rating=risk_rating,
        risk_score=risk_score,
        data_boundary="已解析的三大财务报表数据",
        key_metric_series=key_metric_series,
        knowledge_context=financial_knowledge_context,
        public_context=public_context,
        codeact_analysis=codeact_analysis,
        profit_cash_bridge=profit_cash_bridge,
        structured_financial_package=structured_package,
        annual_report_notes=annual_report_notes,
        financial_business_hints=financial_business_hints,
        industry_context=industry_context,
        business_segments=business_segments or annual_report_notes.get("business_segments") or [],
        annual_business_review=annual_business_review,
    )

    # 将 LLM 经营穿透叙事按四大板块映射到对应小节
    narrative_sections = narrative.get("sections") or []
    narrative_analysis_map: Dict[str, str] = {}
    for sec in narrative_sections:
        title = sec.get("section_title") or ""
        if "收入" in title and "利润" in title:
            narrative_analysis_map["income"] = sec.get("narrative") or ""
        elif "资产负债" in title:
            narrative_analysis_map["balance"] = sec.get("narrative") or ""
        elif "盈利质量" in title or "营运效率" in title:
            narrative_analysis_map["quality"] = sec.get("narrative") or ""
        elif "偿债能力" in title or "财务信号" in title:
            narrative_analysis_map["solvency"] = sec.get("narrative") or ""

    use_narrative = narrative.get("source") == "llm" and not narrative.get("quality_warnings")
    if use_narrative:
        for section in sections:
            for subsection in section.get("subsections") or []:
                sub_title = subsection.get("title") or ""
                if "收入" in sub_title and "利润" in sub_title and narrative_analysis_map.get("income"):
                    subsection["analysis"] = [narrative_analysis_map["income"]]
                    subsection["narrative_source"] = "llm"
                elif "资产负债" in sub_title and narrative_analysis_map.get("balance"):
                    subsection["analysis"] = [narrative_analysis_map["balance"]]
                    subsection["narrative_source"] = "llm"
                elif "盈利质量" in sub_title and narrative_analysis_map.get("quality"):
                    subsection["analysis"] = [narrative_analysis_map["quality"]]
                    subsection["narrative_source"] = "llm"
                elif "偿债能力" in sub_title and narrative_analysis_map.get("solvency"):
                    subsection["analysis"] = [narrative_analysis_map["solvency"]]
                    subsection["narrative_source"] = "llm"

    return {
        "report_type": "financial_analysis",
        "enterprise_name": enterprise_name,
        "risk_rating": risk_rating,
        "risk_score": risk_score,
        "recommendation": recommendation,
        "years": years,
        "generated_from": generated_from,
        "stock_code": stock_code,
        "source_type": source_type,
        "structured_financial_package": structured_package,
        "key_metrics": key_metrics,
        "key_metric_series": key_metric_series,
        "financial_dashboard": financial_dashboard,
        "profit_cash_bridge": profit_cash_bridge,
        "narrative_summary": narrative.get("summary") or [],
        "narrative_diagnostics": narrative.get("diagnostics") or {},
        "narrative_source": narrative.get("source"),
        "narrative_quality_warnings": narrative.get("quality_warnings") or [],
        "narrative_elapsed_ms": narrative.get("llm_elapsed_ms"),
        "narrative_provider": narrative.get("llm_provider"),
        "financial_knowledge_context": {
            "triggered_rules": financial_knowledge_context.get("triggered_rules") or [],
            "knowledge_briefs": financial_knowledge_context.get("knowledge_briefs") or [],
            "retrieval_mode": (financial_knowledge_context.get("retrieval") or {}).get("mode"),
            "query": financial_knowledge_context.get("query"),
        },
        "codeact_analysis": codeact_analysis,
        "codeact_evidence": codeact_evidence,
        "codeact_evidence_refs": codeact_evidence_refs,
        "public_context": public_context or [],
        "sections": sections,
        "narrative_sections": narrative_sections,
        "narrative_summary": narrative.get("summary") or [],
        "narrative_diagnostics": narrative.get("diagnostics") or {},
        "narrative_source": narrative.get("source"),
        "narrative_quality_warnings": narrative.get("quality_warnings") or [],
        "risk_summary": risk_items,
        "annual_report_notes": annual_report_notes,
    }
