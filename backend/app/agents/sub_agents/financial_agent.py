# ========================================
# 财务分析Agent
# 使用 Rebecca 引擎进行10维度财务分析
# ========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json

from app.agents.tools.search_tool import search_financial_data
from app.engines.rebecca.analyzers import FinancialDDAnalyzer
from app.engines.rebecca.adapter import AnalyzerAdapter
from app.agents.sub_agents.financial_report_builder import build_financial_analysis_report


def _frame_to_records(df):
    if df is None:
        return []
    return df.fillna(0).to_dict(orient="records")


def _latest_year_columns(df) -> List[str]:
    if df is None:
        return []
    years = []
    for col in df.columns:
        value = str(col)
        if value.isdigit() and len(value) == 4:
            years.append(value)
    return sorted(years, reverse=True)


def _column_for_year(df, year: str):
    for col in df.columns:
        if str(col) == str(year):
            return col
    return None


def _label_column(df):
    for col in df.columns:
        if any(keyword in str(col) for keyword in ["项目", "科目", "指标", "名称"]):
            return col
    for col in df.columns:
        if not (str(col).isdigit() and len(str(col)) == 4):
            return col
    return df.columns[0]


def _value_by_item(df, item_keywords: List[str], year: str) -> Optional[float]:
    if df is None:
        return None

    year_col = _column_for_year(df, year)
    if year_col is None:
        return None

    label_col = _label_column(df)
    for _, row in df.iterrows():
        label = str(row.get(label_col, ""))
        if any(keyword in label for keyword in item_keywords):
            try:
                return float(row.get(year_col, 0) or 0)
            except (TypeError, ValueError):
                return None
    return None


def _run_rebecca_analysis(
    enterprise_name: str,
    rebecca_data: Dict[str, Any],
    include_structured_report: bool = False,
) -> Dict[str, Any]:
    timeline = []
    evidence = []

    years = _latest_year_columns(rebecca_data.get("income_statement"))
    latest_year = years[0] if years else "最新年度"

    income = rebecca_data.get("income_statement")
    balance = rebecca_data.get("balance_sheet")
    cash_flow = rebecca_data.get("cash_flow")

    revenue = _value_by_item(income, ["营业收入", "主营业务收入", "收入"], latest_year)
    net_profit = _value_by_item(income, ["净利润"], latest_year)
    total_assets = _value_by_item(balance, ["资产总计", "资产合计", "总资产"], latest_year)
    total_liabilities = _value_by_item(balance, ["负债合计", "负债总计", "总负债"], latest_year)
    receivable = _value_by_item(balance, ["应收账款"], latest_year)
    operating_cash_flow = _value_by_item(cash_flow, ["经营活动产生的现金流量净额", "经营活动现金流"], latest_year)

    findings = []
    if revenue is not None:
        findings.append(f"{latest_year}年营收{revenue / 100000000:.1f}亿")
        evidence.append({"label": "营业收入", "value": f"{revenue / 100000000:.1f}亿", "source": "用户上传财报"})
    if revenue and net_profit is not None:
        findings.append(f"净利润率{net_profit / revenue * 100:.1f}%")
        evidence.append({"label": "净利润率", "value": f"{net_profit / revenue * 100:.1f}%", "source": "用户上传财报"})
    if total_assets and total_liabilities is not None:
        findings.append(f"资产负债率{total_liabilities / total_assets * 100:.0f}%")
        evidence.append({"label": "资产负债率", "value": f"{total_liabilities / total_assets * 100:.0f}%", "source": "用户上传财报"})

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "读取用户上传的近三年财务报表",
        "detail": "资产负债表、利润表、现金流量表",
        "status": "completed",
        "type": "discovery",
        "findings": findings or ["已读取上传财报，部分关键科目缺失"],
    })

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "分析应收账款结构",
        "detail": "基于上传资产负债表识别应收账款余额",
        "status": "completed",
        "type": "analysis",
        "findings": [f"应收账款余额{receivable / 100000000:.1f}亿"] if receivable is not None else ["未识别到应收账款科目"],
        "conclusion": "应收账款需结合账龄和客户集中度进一步核实" if receivable is not None else None,
    })
    if receivable is not None:
        evidence.append({"label": "应收账款", "value": f"{receivable / 100000000:.1f}亿", "source": "用户上传财报"})

    analyzer = FinancialDDAnalyzer(rebecca_data)
    analysis_result = analyzer.generate_full_analysis()
    risks = analyzer.identify_risks()
    analysis_json = AnalyzerAdapter.analysis_to_json(analysis_result)
    risks_json = AnalyzerAdapter.risks_to_dict(risks)

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "Rebecca引擎深度分析",
        "detail": "10维度财务分析、风险识别",
        "status": "completed",
        "type": "analysis",
        "findings": [
            f"毛利率：{analysis_json.get('profitability', {}).get('gross_profit_margin', {}).get('data', [['', '']])[0][1] if 'profitability' in analysis_json else 'N/A'}",
            f"流动比率：{analysis_json.get('solvency', {}).get('current_ratio', {}).get('data', [['', '']])[0][1] if 'solvency' in analysis_json else 'N/A'}",
        ],
    })

    for level, items in risks_json.items():
        for item in items:
            evidence.append({"label": f"风险-{level}", "value": item, "source": "Rebecca引擎分析"})

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "分析现金流覆盖率",
        "detail": "经营活动现金流/负债合计",
        "status": "completed",
        "type": "analysis",
        "findings": [f"经营活动现金流{operating_cash_flow / 100000000:.1f}亿"] if operating_cash_flow is not None else ["未识别到经营活动现金流净额"],
        "conclusion": "需结合负债规模判断现金流覆盖情况",
    })
    if operating_cash_flow is not None:
        evidence.append({"label": "经营活动现金流", "value": f"{operating_cash_flow / 100000000:.1f}亿", "source": "用户上传财报"})

    result = {"success": True, "timeline": timeline, "evidence": evidence}
    if include_structured_report:
        result["financial_analysis_report"] = build_financial_analysis_report(enterprise_name, rebecca_data)
    return result


async def run_financial_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行财务分析Agent

    Args:
        enterprise_name: 企业名称

    Returns:
        Dict: 分析结果，包含 timeline、evidence、success
    """
    try:
        result_json = search_financial_data._run(enterprise_name=enterprise_name)
        financial_data = json.loads(result_json)
        import pandas as pd

        rebecca_data = {
            "income_statement": pd.DataFrame({
                "项目": ["营业收入", "营业成本", "毛利润", "净利润"],
                "2024": [
                    financial_data["财务报表"]["2024"]["营业收入"],
                    financial_data["财务报表"]["2024"]["营业成本"],
                    financial_data["财务报表"]["2024"]["毛利润"],
                    financial_data["财务报表"]["2024"]["净利润"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["营业收入"],
                    financial_data["财务报表"]["2023"]["营业成本"],
                    financial_data["财务报表"]["2023"]["毛利润"],
                    financial_data["财务报表"]["2023"]["净利润"],
                ],
            }),
            "balance_sheet": pd.DataFrame({
                "项目": ["总资产", "总负债", "所有者权益"],
                "2024": [
                    financial_data["财务报表"]["2024"]["总资产"],
                    financial_data["财务报表"]["2024"]["总负债"],
                    financial_data["财务报表"]["2024"]["所有者权益"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["总资产"],
                    financial_data["财务报表"]["2023"]["总负债"],
                    financial_data["财务报表"]["2023"]["所有者权益"],
                ],
            }),
            "cash_flow": pd.DataFrame({
                "项目": ["经营活动现金流", "投资活动现金流", "筹资活动现金流"],
                "2024": [
                    financial_data["财务报表"]["2024"]["经营活动现金流"],
                    financial_data["财务报表"]["2024"]["投资活动现金流"],
                    financial_data["财务报表"]["2024"]["筹资活动现金流"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["经营活动现金流"],
                    financial_data["财务报表"]["2023"]["投资活动现金流"],
                    financial_data["财务报表"]["2023"]["筹资活动现金流"],
                ],
            }),
        }

        result = _run_rebecca_analysis(enterprise_name, rebecca_data)
        for item in result["evidence"]:
            if item.get("source") == "用户上传财报":
                item["source"] = "模拟财务数据"
        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "财务分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }


async def run_financial_agent_with_uploaded_data(
    enterprise_name: str,
    parsed_financial_data: Dict[str, Any],
) -> Dict[str, Any]:
    """基于用户上传并解析后的财务数据运行财务分析。"""
    try:
        import pandas as pd

        rebecca_data = {}
        for key in ["income_statement", "balance_sheet", "cash_flow"]:
            value = parsed_financial_data.get(key)
            if value:
                rebecca_data[key] = pd.DataFrame(value)

        required = ["income_statement", "balance_sheet", "cash_flow"]
        missing = [name for name in required if name not in rebecca_data]
        if missing:
            return {
                "success": False,
                "error": f"上传财报缺少必要表格: {', '.join(missing)}",
                "timeline": [{
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "财务Agent",
                    "content": "上传财报解析失败",
                    "detail": "请使用标准模板，或确保包含利润表、资产负债表、现金流量表",
                    "status": "completed",
                    "type": "risk",
                }],
                "evidence": [],
            }

        return _run_rebecca_analysis(enterprise_name, rebecca_data, include_structured_report=True)

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "上传财报分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }
