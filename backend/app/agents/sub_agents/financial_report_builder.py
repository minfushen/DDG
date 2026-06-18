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
) -> List[str]:
    if not years:
        return ["利润表数据不足，需补充近三年营业收入、营业成本、净利润和扣非净利润后判断。"]
    latest = years[-1]
    revenue_trend = "持续增长" if _trend_text(revenue, years) == "增长" else "持续下降" if _trend_text(revenue, years) == "下降" else "基本稳定"
    revenue_cagr = _format_percent(_cagr(revenue, years))
    latest_growth = _format_percent(revenue_growth.get(latest))
    deducted_available = any(deducted_net_profit.get(year) is not None for year in years)
    deducted_sentence = _profit_change_sentence(deducted_net_profit, years, "扣非净利润") if deducted_available else "扣非净利润数据暂未稳定取得，需结合年报非经常性损益明细判断主营盈利质量。"
    lines = [
        f"公司近三年营业收入{revenue_trend}。{_series_amount_sentence(revenue, years, '营业收入')}，年复合增长率约{revenue_cagr}；{latest}年营收同比增长{latest_growth}，营业成本为{_format_amount_short(cost.get(latest))}。",
        f"盈利能力方面，{_profit_change_sentence(net_profit, years, '净利润')}{deducted_sentence}若扣非利润弱于净利润或持续为负，说明主营业务盈利修复基础仍需进一步核实。",
        f"毛利率方面，{_series_percent_sentence(gross_margin, years, '毛利率')}；{latest}年销售净利率为{_format_percent(net_margin.get(latest))}。毛利率和净利率变化需结合产品结构、价格周期、产能利用率、折旧摊销、政府补助和费用资本化影响复核。",
    ]
    if profit_cash_bridge:
        lines.append(str(profit_cash_bridge.get("deducted_profit_judgement") or ""))
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


def build_financial_analysis_report(
    enterprise_name: str,
    financial_data: Dict[str, pd.DataFrame],
    public_context: Optional[List[Dict[str, Any]]] = None,
    generated_from: str = "用户上传财报",
    stock_code: str = "",
    source_type: str = "financial_statement",
    cross_provider_reconciliation: Optional[Dict[str, Any]] = None,
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
                        _row("扣非净利润", deducted_net_profit, years),
                        _row("投资收益", investment_income, years),
                        _row("资产减值损失", asset_impairment, years),
                        _row("信用减值损失", credit_impairment, years),
                        _ratio_row("主营业务毛利率", gross_margin, years),
                    ]},
                    "analysis": [
                        *_income_statement_analysis(years, revenue, cost, net_profit, deducted_net_profit, gross_margin, net_margin, revenue_growth, profit_cash_bridge),
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
                        _row("折旧摊销", depreciation_amortization, years),
                    ]},
                    "analysis": [
                        f"近三年现金流类型分别为：{'; '.join(f'{year}年：{cash_type[year]}' for year in years)}。",
                        str(profit_cash_bridge.get("bridge_explanation") or ""),
                        str(profit_cash_bridge.get("credit_implication") or ""),
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
                        _ratio_row("现金短债比", cash_to_short_debt, years, _format_ratio),
                        _ratio_row("EBITDA利息保障倍数", ebitda_interest_coverage, years, _format_ratio),
                    ]},
                    "analysis": [f"{latest}年流动比率为{_format_ratio(current_ratio.get(latest))}，速动比率为{_format_ratio(quick_ratio.get(latest))}，资产负债率为{_format_percent(debt_ratio.get(latest))}，现金短债比为{_format_ratio(cash_to_short_debt.get(latest))}，EBITDA利息保障倍数为{_format_ratio(ebitda_interest_coverage.get(latest))}。"],
                    "risk提示": "重点关注短期偿债能力和有息负债成本。",
                },
                {
                    "title": "盈利能力分析",
                    "table": {"columns": years, "rows": [
                        _row("EBITDA近似值", ebitda_proxy, years),
                        _ratio_row("销售净利率", net_margin, years),
                        _ratio_row("ROA", roa, years),
                        _ratio_row("ROE", roe, years),
                    ]},
                    "analysis": [f"{latest}年销售净利率为{_format_percent(net_margin.get(latest))}，ROA为{_format_percent(roa.get(latest))}，ROE为{_format_percent(roe.get(latest))}。盈利指标持续下滑或转负时，需区分经营亏损、资产减值和非经常性损益的影响。"],
                    "risk提示": "ROE = ROA × 权益乘数；若ROE显著高于ROA，通常由较高财务杠杆驱动，需结合权益结构、有息负债和再融资安排判断。",
                },
                {
                    "title": "营运能力分析",
                    "table": {"columns": years, "rows": [
                        _ratio_row("存货周转率", inventory_turnover, years, _format_ratio),
                        _ratio_row("存货周转天数", inventory_turnover_days, years, _format_days),
                        _ratio_row("应收账款周转率", receivable_turnover, years, _format_ratio),
                        _ratio_row("应收账款周转天数", receivable_turnover_days, years, _format_days),
                        _ratio_row("总资产周转率", asset_turnover, years, _format_ratio),
                    ]},
                    "analysis": [f"{latest}年应收账款周转率为{_format_ratio(receivable_turnover.get(latest))}，应收账款周转天数为{_format_days(receivable_turnover_days.get(latest))}；存货周转率为{_format_ratio(inventory_turnover.get(latest))}，存货周转天数为{_format_days(inventory_turnover_days.get(latest))}。"],
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
    )

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
        "risk_summary": risk_items,
    }
