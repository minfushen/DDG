"""Deterministic financial CodeAct tools."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional


INCOME_KEYWORDS = {
    "revenue": ["营业收入", "主营业务收入", "收入"],
    "cost": ["营业成本", "主营业务成本", "成本"],
    "gross_profit": ["毛利润", "毛利"],
    "operating_profit": ["营业利润"],
    "total_profit": ["利润总额"],
    "net_profit": ["净利润"],
    "deducted_net_profit": ["扣除非经常性损益后的净利润", "扣非净利润", "归属于上市公司股东的扣除非经常性损益的净利润"],
    "financial_expense": ["财务费用"],
    "investment_income": ["投资收益", "投资净收益"],
    "asset_impairment": ["资产减值损失", "资产减值损失(损失以-号填列)", "资产减值损失（损失以-号填列）"],
    "credit_impairment": ["信用减值损失", "信用减值损失(损失以-号填列)", "信用减值损失（损失以-号填列）"],
}

BALANCE_KEYWORDS = {
    "cash": ["货币资金"],
    "receivable": ["应收账款"],
    "inventory": ["存货"],
    "fixed_assets": ["固定资产"],
    "construction": ["在建工程"],
    "short_loan": ["短期借款"],
    "notes_payable": ["应付票据"],
    "non_current_liabilities_due_within_one_year": ["一年内到期的非流动负债"],
    "current_assets": ["流动资产合计", "流动资产"],
    "total_assets": ["资产总计", "资产合计", "总资产"],
    "current_liabilities": ["流动负债合计", "流动负债"],
    "total_liabilities": ["负债合计", "负债总计", "总负债"],
    "equity": ["所有者权益(或股东权益)合计", "所有者权益", "股东权益", "净资产"],
}

CASH_FLOW_KEYWORDS = {
    "operating_cashflow": ["经营活动产生的现金流量净额", "经营活动产生现金流量净额", "经营活动现金流", "经营活动"],
    "investing_cashflow": ["投资活动产生的现金流量净额", "投资活动现金流", "投资活动"],
    "financing_cashflow": ["筹资活动产生的现金流量净额", "筹资活动现金流", "筹资活动"],
}


def calculate_financial_ratios(payload: Dict[str, Any]) -> Dict[str, Any]:
    statements = _statements(payload)
    years = _years_from_statements(statements)
    if not years:
        return {"passed": False, "years": [], "metrics": {}, "warnings": ["未识别到年度列"], "issues": []}

    series = _build_series(statements, years)
    metrics_by_year: Dict[str, Dict[str, Optional[float]]] = {}
    for year in years:
        revenue = series["revenue"].get(year)
        cost = series["cost"].get(year)
        gross_profit = series["gross_profit"].get(year)
        if gross_profit is None and revenue is not None and cost is not None:
            gross_profit = revenue - cost
        net_profit = series["net_profit"].get(year)
        deducted_net_profit = series["deducted_net_profit"].get(year)
        financial_expense = series["financial_expense"].get(year)
        investment_income = series["investment_income"].get(year)
        asset_impairment = series["asset_impairment"].get(year)
        credit_impairment = series["credit_impairment"].get(year)
        total_assets = series["total_assets"].get(year)
        current_assets = series["current_assets"].get(year)
        inventory = series["inventory"].get(year)
        total_liabilities = series["total_liabilities"].get(year)
        current_liabilities = series["current_liabilities"].get(year)
        equity = series["equity"].get(year)
        receivable = series["receivable"].get(year)
        inventory_balance = series["inventory"].get(year)
        fixed_assets = series["fixed_assets"].get(year)
        construction = series["construction"].get(year)
        short_loan = series["short_loan"].get(year)
        notes_payable = series["notes_payable"].get(year)
        due_within_one_year = series["non_current_liabilities_due_within_one_year"].get(year)
        operating_cf = series["operating_cashflow"].get(year)
        short_debt = _sum_optional(short_loan, notes_payable, due_within_one_year)
        ebitda_proxy = _sum_optional(net_profit, financial_expense)

        metrics_by_year[year] = {
            "revenue": revenue,
            "cost": cost,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "deducted_net_profit": deducted_net_profit,
            "financial_expense": financial_expense,
            "investment_income": investment_income,
            "asset_impairment": asset_impairment,
            "credit_impairment": credit_impairment,
            "short_loan": short_loan,
            "notes_payable": notes_payable,
            "non_current_liabilities_due_within_one_year": due_within_one_year,
            "short_debt": short_debt,
            "cash": series["cash"].get(year),
            "receivable": receivable,
            "inventory": inventory_balance,
            "fixed_assets": fixed_assets,
            "construction": construction,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "operating_cashflow": operating_cf,
            "investing_cashflow": series["investing_cashflow"].get(year),
            "financing_cashflow": series["financing_cashflow"].get(year),
            "ebitda_proxy": ebitda_proxy,
            "gross_margin": _safe_div(gross_profit, revenue),
            "net_margin": _safe_div(net_profit, revenue),
            "debt_ratio": _safe_div(total_liabilities, total_assets),
            "current_ratio": _safe_div(current_assets, current_liabilities),
            "quick_ratio": _safe_div(_subtract(current_assets, inventory), current_liabilities),
            "roe": _safe_div(net_profit, equity),
            "roa": _safe_div(net_profit, total_assets),
            "receivable_to_revenue": _safe_div(receivable, revenue),
            "cash_to_short_debt": _safe_div(series["cash"].get(year), short_debt),
            "operating_cashflow_to_revenue": _safe_div(operating_cf, revenue),
            "operating_cashflow_to_net_profit": _safe_div(operating_cf, net_profit),
            "receivable_turnover_days": _turnover_days(receivable, revenue),
            "inventory_turnover_days": _turnover_days(inventory, cost),
            "ebitda_interest_coverage": _safe_div(ebitda_proxy, financial_expense),
        }

    growth_metrics = _growth_metrics(metrics_by_year, years)
    warnings = _metric_warnings(metrics_by_year, years)
    return {
        "passed": True,
        "years": years,
        "metrics": metrics_by_year,
        "growth_metrics": growth_metrics,
        "warnings": warnings,
        "issues": [],
        "data_boundary": "指标由上传或公开解析后的三大表 records 确定性计算生成，未进行审计调整。",
    }


def validate_financial_statements(payload: Dict[str, Any]) -> Dict[str, Any]:
    statements = _statements(payload)
    years = _years_from_statements(statements)
    series = _build_series(statements, years)
    issues: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if not years:
        issues.append(_issue("P0", "schema", "未识别到年度列", "请确认三大表 records 中包含 2023/2024/2025 等年度字段。"))

    required_items = {
        "income_statement": ["revenue", "net_profit"],
        "balance_sheet": ["total_assets", "total_liabilities", "equity"],
        "cash_flow": ["operating_cashflow"],
    }
    for statement_name, keys in required_items.items():
        if not statements.get(statement_name):
            warnings.append(_issue("P1", statement_name, f"缺少{_statement_label(statement_name)}", "建议补充完整三大表，避免报告出现数据边界缺口。"))
        for key in keys:
            if years and all(series[key].get(year) is None for year in years):
                warnings.append(_issue("P1", key, f"缺少关键科目：{key}", "请检查科目名称是否需要映射或源表是否缺失。"))

    tolerance = float(payload.get("tolerance") or 1.0)
    for year in years:
        total_assets = series["total_assets"].get(year)
        total_liabilities = series["total_liabilities"].get(year)
        equity = series["equity"].get(year)
        if None not in (total_assets, total_liabilities, equity):
            diff = total_assets - total_liabilities - equity  # type: ignore[operator]
            if abs(diff) > tolerance:
                issues.append(_issue("P0", "balance_equation", f"{year}年资产负债表不平衡，差额 {diff:.2f}", "核对资产总计、负债合计、所有者权益合计是否口径一致。", year=year, diff=diff))

        revenue = series["revenue"].get(year)
        cost = series["cost"].get(year)
        gross_profit = series["gross_profit"].get(year)
        if None not in (revenue, cost, gross_profit):
            diff = revenue - cost - gross_profit  # type: ignore[operator]
            if abs(diff) > tolerance:
                warnings.append(_issue("P1", "gross_profit_reconciliation", f"{year}年毛利勾稽不一致，差额 {diff:.2f}", "核对营业收入、营业成本和毛利润是否同一报表口径。", year=year, diff=diff))

        operating_cf = series["operating_cashflow"].get(year)
        net_profit = series["net_profit"].get(year)
        if operating_cf is not None and net_profit is not None and net_profit > 0 and operating_cf < 0:
            warnings.append(_issue("P1", "cash_profit_mismatch", f"{year}年净利润为正但经营现金流为负", "重点核查应收账款、合同资产、收入确认和期后回款。", year=year))

    return {
        "passed": not any(item["severity"] == "P0" for item in issues),
        "years": years,
        "issues": issues,
        "warnings": warnings,
        "summary": _validation_summary(issues, warnings),
    }


def _statements(payload: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    financial_data = payload.get("financial_data") if isinstance(payload.get("financial_data"), dict) else payload
    return {
        "income_statement": _records(financial_data.get("income_statement")),
        "balance_sheet": _records(financial_data.get("balance_sheet")),
        "cash_flow": _records(financial_data.get("cash_flow") or financial_data.get("cashflow")),
    }


def _records(value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    raise ValueError("financial statements must be lists of row objects")


def _years_from_statements(statements: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    years = set()
    for records in statements.values():
        for row in records:
            for key in row.keys():
                text = str(key)
                if text.isdigit() and len(text) == 4:
                    years.add(text)
    return sorted(years)[-3:]


def _build_series(statements: Dict[str, List[Dict[str, Any]]], years: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    series: Dict[str, Dict[str, Optional[float]]] = {}
    for key, keywords in {**INCOME_KEYWORDS, **BALANCE_KEYWORDS, **CASH_FLOW_KEYWORDS}.items():
        if key in INCOME_KEYWORDS:
            records = statements["income_statement"]
        elif key in BALANCE_KEYWORDS:
            records = statements["balance_sheet"]
        else:
            records = statements["cash_flow"]
        series[key] = {year: _value_by_item(records, keywords, year) for year in years}
    return series


def _value_by_item(records: List[Dict[str, Any]], keywords: List[str], year: str) -> Optional[float]:
    rows = [(_row_label(row), row) for row in records]
    for keyword in keywords:
        for label, row in rows:
            if label == _clean_label(keyword):
                return _to_number(row.get(year))
    for keyword in keywords:
        clean_keyword = _clean_label(keyword)
        for label, row in rows:
            if clean_keyword in label:
                return _to_number(row.get(year))
    return None


def _row_label(row: Dict[str, Any]) -> str:
    for key, value in row.items():
        if not (str(key).isdigit() and len(str(key)) == 4):
            key_text = str(key)
            if any(word in key_text for word in ["项目", "科目", "指标", "名称"]):
                return _clean_label(value)
    for key, value in row.items():
        if not (str(key).isdigit() and len(str(key)) == 4):
            return _clean_label(value)
    return ""


def _clean_label(value: Any) -> str:
    return str(value or "").replace("\n", "").replace(" ", "").strip()


def _to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none", "n/a", "--", "-"}:
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


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _subtract(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None:
        return None
    return left - (right or 0)


def _sum_optional(*values: Optional[float]) -> Optional[float]:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _turnover_days(balance_item: Optional[float], flow_item: Optional[float]) -> Optional[float]:
    if balance_item is None or flow_item in (None, 0):
        return None
    return balance_item / abs(flow_item) * 365


def _growth_metrics(metrics_by_year: Dict[str, Dict[str, Optional[float]]], years: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    growth: Dict[str, Dict[str, Optional[float]]] = {}
    for index, year in enumerate(years):
        if index == 0:
            growth[year] = {"revenue_growth": None, "net_profit_growth": None}
            continue
        previous = years[index - 1]
        growth[year] = {
            "revenue_growth": _growth(metrics_by_year[year].get("revenue"), metrics_by_year[previous].get("revenue")),
            "net_profit_growth": _growth(metrics_by_year[year].get("net_profit"), metrics_by_year[previous].get("net_profit")),
        }
    return growth


def _growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous)


def _metric_warnings(metrics_by_year: Dict[str, Dict[str, Optional[float]]], years: List[str]) -> List[str]:
    if not years:
        return []
    latest = metrics_by_year[years[-1]]
    warnings: List[str] = []
    if latest.get("debt_ratio") is not None and latest["debt_ratio"] > 0.7:  # type: ignore[operator]
        warnings.append("最近一期资产负债率高于70%")
    if latest.get("current_ratio") is not None and latest["current_ratio"] < 1:  # type: ignore[operator]
        warnings.append("最近一期流动比率低于1")
    if latest.get("operating_cashflow_to_revenue") is not None and latest["operating_cashflow_to_revenue"] < 0:  # type: ignore[operator]
        warnings.append("最近一期经营现金流对收入覆盖为负")
    if latest.get("receivable_to_revenue") is not None and latest["receivable_to_revenue"] > 0.3:  # type: ignore[operator]
        warnings.append("最近一期应收账款/营业收入高于30%")
    if latest.get("cash_to_short_debt") is not None and latest["cash_to_short_debt"] < 1:  # type: ignore[operator]
        warnings.append("最近一期现金短债比低于1")
    if latest.get("receivable_turnover_days") is not None and latest["receivable_turnover_days"] > 180:  # type: ignore[operator]
        warnings.append("最近一期应收账款周转天数超过180天")
    if latest.get("inventory_turnover_days") is not None and latest["inventory_turnover_days"] > 180:  # type: ignore[operator]
        warnings.append("最近一期存货周转天数超过180天")
    return warnings


def _issue(severity: str, code: str, message: str, recommendation: str, **extra: Any) -> Dict[str, Any]:
    item = {"severity": severity, "code": code, "message": message, "recommendation": recommendation}
    item.update(extra)
    return item


def _statement_label(statement_name: str) -> str:
    return {"income_statement": "利润表", "balance_sheet": "资产负债表", "cash_flow": "现金流量表"}.get(statement_name, statement_name)


def _validation_summary(issues: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> str:
    if issues:
        return f"发现{len(issues)}项阻断性勾稽问题，需修正后再进入正式分析。"
    if warnings:
        return f"未发现阻断性勾稽问题，但存在{len(warnings)}项需复核事项。"
    return "三大表关键勾稽未发现异常。"
