# ========================================
# 上市公司数据获取工具
# 从东方财富公开接口获取 A 股财务数据
# ========================================

from typing import Type, Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx
import json
import re


class FetchListedCompanyFinancialInput(BaseModel):
    """获取上市公司财务数据输入"""
    enterprise_name: str = Field(description="企业名称")
    stock_code: str = Field(default="", description="股票代码")
    stock_exchange: str = Field(default="", description="上市交易所")


LISTED_COMPANY_MAP = {
    "欣旺达": {"stock_code": "300207", "stock_exchange": "SZ", "secu_code": "300207.SZ", "security_name": "欣旺达", "company_name": "欣旺达电子股份有限公司"},
    "欣旺达电子股份有限公司": {"stock_code": "300207", "stock_exchange": "SZ", "secu_code": "300207.SZ", "security_name": "欣旺达", "company_name": "欣旺达电子股份有限公司"},
    "比亚迪": {"stock_code": "002594", "stock_exchange": "SZ", "secu_code": "002594.SZ", "security_name": "比亚迪", "company_name": "比亚迪股份有限公司"},
    "宁德时代": {"stock_code": "300750", "stock_exchange": "SZ", "secu_code": "300750.SZ", "security_name": "宁德时代", "company_name": "宁德时代新能源科技股份有限公司"},
    "贵州茅台": {"stock_code": "600519", "stock_exchange": "SH", "secu_code": "600519.SH", "security_name": "贵州茅台", "company_name": "贵州茅台酒股份有限公司"},
    "士兰微": {"stock_code": "600460", "stock_exchange": "SH", "secu_code": "600460.SH", "security_name": "士兰微", "company_name": "杭州士兰微电子股份有限公司"},
    "杭州士兰微电子股份有限公司": {"stock_code": "600460", "stock_exchange": "SH", "secu_code": "600460.SH", "security_name": "士兰微", "company_name": "杭州士兰微电子股份有限公司"},
    "闻泰科技": {"stock_code": "600745", "stock_exchange": "SH", "secu_code": "600745.SH", "security_name": "*ST闻泰", "company_name": "闻泰科技股份有限公司"},
    "闻泰科技股份有限公司": {"stock_code": "600745", "stock_exchange": "SH", "secu_code": "600745.SH", "security_name": "*ST闻泰", "company_name": "闻泰科技股份有限公司"},
}


TASK_WORDS = [
    "完成", "帮我", "请", "做一下", "做", "生成", "分析", "查看", "跑", "开展", "进行",
    "完整尽调", "尽调", "贷前", "报告", "这个上市公司", "上市公司", "公司", "企业", "的",
]


def normalize_enterprise_name(text: str) -> str:
    """Strip common task wording and keep the likely enterprise name."""
    normalized = (text or "").strip()
    if not normalized:
        return normalized
    normalized = re.sub(r"（.*?）|\(.*?\)", "", normalized).strip()
    for word in TASK_WORDS:
        normalized = normalized.replace(word, "")
    normalized = re.sub(r"[，,。.!！?？：:\s]+", "", normalized).strip()
    return normalized or (text or "").strip()


INCOME_FIELD_MAP = {
    "营业收入": "TOTAL_OPERATE_INCOME",
    "营业成本": "OPERATE_COST",
    "销售费用": "SALE_EXPENSE",
    "管理费用": "MANAGE_EXPENSE",
    "研发费用": "RESEARCH_EXPENSE",
    "财务费用": "FINANCE_EXPENSE",
    "投资收益": "INVEST_INCOME",
    "营业利润": "OPERATE_PROFIT",
    "营业外收入": "NONBUSINESS_INCOME",
    "利润总额": "TOTAL_PROFIT",
    "净利润": "NETPROFIT",
}


BALANCE_FIELD_MAP = {
    "货币资金": "MONETARYFUNDS",
    "应收账款": "ACCOUNTS_RECE",
    "其他应收款": "TOTAL_OTHER_RECE",
    "存货": "INVENTORY",
    "流动资产合计": "TOTAL_CURRENT_ASSETS",
    "固定资产": "FIXED_ASSET",
    "在建工程": "CIP",
    "非流动资产合计": "TOTAL_NONCURRENT_ASSETS",
    "资产总计": "TOTAL_ASSETS",
    "短期借款": "SHORT_LOAN",
    "应付票据": "NOTE_PAYABLE",
    "应付账款": "ACCOUNTS_PAYABLE",
    "一年内到期非流动负债": "NONCURRENT_LIAB_1YEAR",
    "其他流动负债": "OTHER_CURRENT_LIAB",
    "流动负债合计": "TOTAL_CURRENT_LIAB",
    "长期借款": "LONG_LOAN",
    "应付债券": "BOND_PAYABLE",
    "长期应付款": "LONG_PAYABLE",
    "非流动负债合计": "TOTAL_NONCURRENT_LIAB",
    "负债合计": "TOTAL_LIABILITIES",
    "实收资本": "SHARE_CAPITAL",
    "资本公积": "CAPITAL_RESERVE",
    "所有者权益": "TOTAL_EQUITY",
}


CASHFLOW_FIELD_MAP = {
    "经营活动产生的现金流量净额": "NETCASH_OPERATE",
    "投资活动产生的现金流量净额": "NETCASH_INVEST",
    "筹资活动产生的现金流量净额": "NETCASH_FINANCE",
}


REPORT_MAP = {
    "income_statement": "RPT_F10_FINANCE_GINCOME",
    "balance_sheet": "RPT_F10_FINANCE_GBALANCE",
    "cash_flow": "RPT_F10_FINANCE_GCASHFLOW",
}


def resolve_listed_company(enterprise_name: str, stock_code: str = "", stock_exchange: str = "") -> Optional[Dict[str, str]]:
    """根据输入企业名或股票代码解析上市公司证券信息。"""
    enterprise_name = normalize_enterprise_name(enterprise_name)
    code_match = re.search(r"(?<!\d)([036]\d{5})(?!\d)", stock_code or enterprise_name or "")
    if stock_code or code_match:
        code = (stock_code or code_match.group(1)).split(".")[0]
        exchange = stock_exchange or ("SH" if code.startswith("6") else "SZ")
        for info in LISTED_COMPANY_MAP.values():
            if info["stock_code"] == code:
                return info
        return {
            "stock_code": code,
            "stock_exchange": exchange,
            "secu_code": f"{code}.{exchange}",
            "security_name": enterprise_name,
        }

    for keyword, info in LISTED_COMPANY_MAP.items():
        if keyword in enterprise_name:
            return info
    searched = _search_eastmoney_astock(enterprise_name)
    if searched:
        return searched
    return None


def _search_eastmoney_astock(keyword: str) -> Optional[Dict[str, str]]:
    """Use Eastmoney's public suggest API to resolve an A-share code by name."""
    text = (keyword or "").strip()
    if not text:
        return None
    text = re.sub(r"（.*?）|\(.*?\)", "", text).strip()
    params = {
        "input": text,
        "type": "14",
        "token": "44c9d251add88e27b65ed86506f6e5da",
        "count": "5",
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = httpx.get("https://searchapi.eastmoney.com/api/suggest/get", params=params, headers=headers, timeout=8)
        response.raise_for_status()
        rows = response.json().get("QuotationCodeTable", {}).get("Data", []) or []
    except Exception:
        return None

    for row in rows:
        code = str(row.get("Code") or row.get("UnifiedCode") or "")
        if not re.fullmatch(r"[036]\d{5}", code):
            continue
        security_type = str(row.get("SecurityTypeName") or row.get("Classify") or "")
        if "A" not in security_type and row.get("Classify") != "AStock":
            continue
        exchange = "SH" if code.startswith("6") else "SZ"
        security_name = str(row.get("Name") or text)
        return {
            "stock_code": code,
            "stock_exchange": exchange,
            "secu_code": f"{code}.{exchange}",
            "security_name": security_name,
            "company_name": security_name,
        }
    return None


def _fetch_eastmoney_report(secu_code: str, report_name: str) -> List[Dict[str, Any]]:
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECUCODE="{secu_code}")',
        "pageNumber": "1",
        "pageSize": "20",
        "sortTypes": "-1",
        "sortColumns": "REPORT_DATE",
        "source": "HSF10",
        "client": "PC",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://emweb.securities.eastmoney.com/",
    }
    response = httpx.get(
        "https://datacenter.eastmoney.com/securities/api/data/v1/get",
        params=params,
        headers=headers,
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result") or {}
    rows = result.get("data", []) if isinstance(result, dict) else []
    annual_rows = [row for row in rows if "年报" in str(row.get("REPORT_TYPE", ""))]
    return annual_rows[:3]


def _year_from_report(row: Dict[str, Any]) -> str:
    return str(row.get("REPORT_DATE", ""))[:4]


def _build_statement(rows: List[Dict[str, Any]], field_map: Dict[str, str]) -> List[Dict[str, Any]]:
    years = [_year_from_report(row) for row in rows]
    years = [year for year in years if year.isdigit()]
    statement = []
    for item, field in field_map.items():
        record = {"项目": item}
        for row in rows:
            year = _year_from_report(row)
            if year.isdigit():
                record[year] = row.get(field)
        if any(record.get(year) is not None for year in years):
            statement.append(record)
    return statement


def _add_gross_profit(income_statement: List[Dict[str, Any]]):
    revenue = next((row for row in income_statement if row.get("项目") == "营业收入"), None)
    cost = next((row for row in income_statement if row.get("项目") == "营业成本"), None)
    if not revenue or not cost:
        return

    record = {"项目": "毛利润"}
    for year, value in revenue.items():
        if year == "项目":
            continue
        cost_value = cost.get(year)
        record[year] = value - cost_value if value is not None and cost_value is not None else None
    income_statement.insert(2, record)


class FetchListedCompanyFinancialTool(BaseTool):
    """获取上市公司财务数据工具"""
    name: str = "fetch_listed_company_financial"
    description: str = "从东方财富公开接口获取上市公司近三年财务报表，并转换成标准三大表结构。"
    args_schema: Type[BaseModel] = FetchListedCompanyFinancialInput

    def _run(self, enterprise_name: str, stock_code: str = "", stock_exchange: str = "") -> str:
        company = resolve_listed_company(enterprise_name, stock_code, stock_exchange)
        if not company:
            return json.dumps({
                "success": False,
                "error": "未识别到上市公司证券代码",
                "enterprise_name": enterprise_name,
            }, ensure_ascii=False)

        try:
            income_rows = _fetch_eastmoney_report(company["secu_code"], REPORT_MAP["income_statement"])
            balance_rows = _fetch_eastmoney_report(company["secu_code"], REPORT_MAP["balance_sheet"])
            cash_rows = _fetch_eastmoney_report(company["secu_code"], REPORT_MAP["cash_flow"])

            income_statement = _build_statement(income_rows, INCOME_FIELD_MAP)
            _add_gross_profit(income_statement)
            balance_sheet = _build_statement(balance_rows, BALANCE_FIELD_MAP)
            cash_flow = _build_statement(cash_rows, CASHFLOW_FIELD_MAP)

            return json.dumps({
                "success": True,
                "enterprise_name": enterprise_name,
                "security_name": company["security_name"],
                "stock_code": company["stock_code"],
                "stock_exchange": company["stock_exchange"],
                "secu_code": company["secu_code"],
                "data_source": "东方财富公开财报接口",
                "years": sorted({key for row in income_statement for key in row.keys() if key.isdigit()}),
                "financial_statements": {
                    "income_statement": income_statement,
                    "balance_sheet": balance_sheet,
                    "cash_flow": cash_flow,
                },
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"获取上市公司公开财报失败: {str(e)}",
                "enterprise_name": enterprise_name,
                "stock_code": company.get("stock_code"),
                "stock_exchange": company.get("stock_exchange"),
            }, ensure_ascii=False)


fetch_listed_company_financial = FetchListedCompanyFinancialTool()
