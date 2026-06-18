"""Optional AKShare financial statement provider.

AKShare is useful for POC and fallback structured data. It is intentionally
loaded dynamically so deployments without AKShare remain healthy.
"""

from __future__ import annotations

import importlib.util
import json
import re
from typing import Any, Dict, List

from app.agents.tools.listed_company_tool import resolve_listed_company


INCOME_LABEL_MAP = {
    "营业收入": ["营业总收入", "营业收入"],
    "营业成本": ["营业成本"],
    "营业利润": ["营业利润"],
    "利润总额": ["利润总额"],
    "净利润": ["净利润", "归属于母公司所有者的净利润", "归属于母公司股东的净利润", "归母净利润"],
    "扣非净利润": ["扣除非经常性损益后的净利润", "扣非净利润"],
    "财务费用": ["财务费用"],
    "投资收益": ["投资收益"],
    "资产减值损失": ["资产减值损失"],
    "信用减值损失": ["信用减值损失"],
}

BALANCE_LABEL_MAP = {
    "货币资金": ["货币资金"],
    "应收账款": ["应收账款"],
    "存货": ["存货"],
    "固定资产": ["固定资产"],
    "在建工程": ["在建工程"],
    "流动资产合计": ["流动资产合计"],
    "资产总计": ["资产总计", "资产总额"],
    "短期借款": ["短期借款"],
    "应付票据": ["应付票据"],
    "应付账款": ["应付账款"],
    "一年内到期的非流动负债": ["一年内到期的非流动负债"],
    "流动负债合计": ["流动负债合计"],
    "负债合计": ["负债合计", "负债总计"],
    "所有者权益": ["所有者权益合计", "股东权益合计"],
}

CASH_LABEL_MAP = {
    "经营活动产生的现金流量净额": ["经营活动产生的现金流量净额"],
    "投资活动产生的现金流量净额": ["投资活动产生的现金流量净额"],
    "筹资活动产生的现金流量净额": ["筹资活动产生的现金流量净额"],
    "折旧摊销": ["固定资产折旧", "无形资产摊销", "长期待摊费用摊销"],
}


def _akshare_available() -> bool:
    return importlib.util.find_spec("akshare") is not None


def _normalize_period(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else text[:4]


def _to_float(value: Any):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _pick_column(columns: List[str], candidates: List[str]) -> str:
    for candidate in candidates:
        for col in columns:
            if candidate == col or candidate in col:
                return col
    return ""


def _matching_columns(columns: List[str], aliases: List[str]) -> List[str]:
    exact = [col for alias in aliases for col in columns if col == alias]
    if exact:
        return list(dict.fromkeys(exact))
    fuzzy = [col for alias in aliases for col in columns if alias in col]
    return list(dict.fromkeys(fuzzy))


def _records_from_akshare_df(df: Any, label_map: Dict[str, List[str]], years: List[str]) -> List[Dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []
    columns = [str(col) for col in df.columns]
    item_col = _pick_column(columns, ["项目", "科目", "报表项目", "指标"])
    date_col = _pick_column(columns, ["报告日", "报告日期", "日期", "REPORT_DATE"])
    if not date_col:
        return []
    if not item_col:
        return _records_from_wide_akshare_df(df, label_map, years, date_col, columns)

    records: List[Dict[str, Any]] = []
    for target_label, aliases in label_map.items():
        record = {"项目": target_label}
        matched = df[df[item_col].astype(str).apply(lambda text: any(alias in text for alias in aliases))]
        if matched.empty:
            continue
        for _, row in matched.iterrows():
            year = _normalize_period(row.get(date_col))
            if year in years:
                value_col = _pick_column(columns, ["本期金额", "期末余额", "金额", "value", "VALUE"])
                if value_col:
                    record[year] = _to_float(row.get(value_col))
        if any(record.get(year) is not None for year in years):
            records.append(record)
    return records


def _annual_rows(df: Any, date_col: str):
    if "是否审计" in df.columns:
        audited = df[df["是否审计"].astype(str).str.contains("是", na=False)]
        if not audited.empty:
            return audited
    return df[df[date_col].astype(str).str.contains("1231|12-31", na=False)]


def _records_from_wide_akshare_df(df: Any, label_map: Dict[str, List[str]], years: List[str], date_col: str, columns: List[str]) -> List[Dict[str, Any]]:
    annual_df = _annual_rows(df, date_col)
    if annual_df.empty:
        annual_df = df
    records: List[Dict[str, Any]] = []
    for target_label, aliases in label_map.items():
        record = {"项目": target_label}
        matched_cols = _matching_columns(columns, aliases)
        if not matched_cols:
            continue
        for _, row in annual_df.iterrows():
            year = _normalize_period(row.get(date_col))
            if year not in years:
                continue
            values = [_to_float(row.get(col)) for col in matched_cols]
            values = [value for value in values if value is not None]
            if values:
                record[year] = sum(values) if target_label == "折旧摊销" and len(values) > 1 else values[0]
        if any(record.get(year) is not None for year in years):
            records.append(record)
    return records


def fetch_akshare_financial_data(enterprise_name: str, stock_code: str = "", stock_exchange: str = "") -> Dict[str, Any]:
    company = resolve_listed_company(enterprise_name, stock_code=stock_code, stock_exchange=stock_exchange)
    if not company:
        return {"success": False, "provider": "akshare", "error": "未识别到A股上市公司主体或股票代码。"}
    if not _akshare_available():
        return {
            "success": False,
            "provider": "akshare",
            "error": "AKShare 未安装，跳过该可选 Provider。",
            "install_hint": "pip install akshare==1.18.64",
        }

    try:
        import akshare as ak  # type: ignore

        symbol = company.get("stock_code") or ""
        income_df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
        balance_df = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
        cash_df = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")
        date_col = "报告日"
        annual_frames = [
            _annual_rows(df, date_col) if date_col in getattr(df, "columns", []) else df
            for df in [income_df, balance_df, cash_df]
        ]
        years = sorted({
            _normalize_period(value)
            for df in annual_frames
            for value in (df["报告日"].tolist() if "报告日" in df.columns else [])
            if _normalize_period(value).isdigit()
        }, reverse=True)[:3]
        financial_statements = {
            "income_statement": _records_from_akshare_df(income_df, INCOME_LABEL_MAP, years),
            "balance_sheet": _records_from_akshare_df(balance_df, BALANCE_LABEL_MAP, years),
            "cash_flow": _records_from_akshare_df(cash_df, CASH_LABEL_MAP, years),
        }
        if not all(financial_statements.values()):
            return {
                "success": False,
                "provider": "akshare",
                "stock_code": company.get("stock_code"),
                "years": years,
                "error": "AKShare 返回结果未能稳定映射为三大表标准字段。",
            }
        return {
            "success": True,
            "provider": "akshare",
            "source_type": "open_quant_financial_data",
            "data_source": "AKShare",
            "enterprise_name": enterprise_name,
            "stock_code": company.get("stock_code"),
            "stock_exchange": company.get("stock_exchange"),
            "secu_code": company.get("secu_code"),
            "security_name": company.get("security_name"),
            "years": years,
            "financial_statements": financial_statements,
        }
    except Exception as exc:
        return {
            "success": False,
            "provider": "akshare",
            "stock_code": company.get("stock_code"),
            "error": f"AKShare 取数失败：{type(exc).__name__}: {exc}",
        }


class _FetchAkshareFinancialTool:
    name = "fetch_akshare_financial_data"

    def _run(self, enterprise_name: str, stock_code: str = "", stock_exchange: str = "", **_: Any) -> str:
        return json.dumps(fetch_akshare_financial_data(enterprise_name, stock_code=stock_code, stock_exchange=stock_exchange), ensure_ascii=False)


fetch_akshare_financial_tool = _FetchAkshareFinancialTool()
