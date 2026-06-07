# backend/app/agents/tools/analyze_tool.py
"""财务分析工具"""
from langchain_core.tools import tool
from typing import Dict, Optional
import json
import pandas as pd

from app.engines.rebecca.analyzers import FinancialDDAnalyzer
from app.engines.rebecca.adapter import AnalyzerAdapter


@tool
def analyze_financial_data(
    financial_data_json: str,
    supplementary_data_json: Optional[str] = None,
) -> str:
    """对企业财务数据进行 10 维度全面分析。

    当用户要求分析某企业财报时调用此工具。
    返回 31 张分析表格和风险识别结果。

    Args:
        financial_data_json: 财务数据 JSON 字符串，包含 income_statement、balance_sheet、cash_flow
        supplementary_data_json: 补充数据 JSON 字符串（可选）
    """
    try:
        # 解析 JSON 数据
        financial_data_raw = json.loads(financial_data_json)
        supplementary_data = (
            json.loads(supplementary_data_json) if supplementary_data_json else None
        )

        # 转换为 DataFrame
        financial_data = {}
        if "income_statement" in financial_data_raw:
            financial_data["income_statement"] = pd.DataFrame(
                financial_data_raw["income_statement"], index=[0]
            ).T
        if "balance_sheet" in financial_data_raw:
            financial_data["balance_sheet"] = pd.DataFrame(
                financial_data_raw["balance_sheet"], index=[0]
            ).T
        if "cash_flow" in financial_data_raw:
            financial_data["cash_flow"] = pd.DataFrame(
                financial_data_raw["cash_flow"], index=[0]
            ).T

        # 调用 Rebecca 引擎
        analyzer = FinancialDDAnalyzer(financial_data, supplementary_data)
        analysis = analyzer.generate_full_analysis()
        risks = analyzer.identify_risks()

        # 转换为 JSON
        result = {
            "analysis": AnalyzerAdapter.analysis_to_json(analysis),
            "risks": AnalyzerAdapter.risks_to_dict(risks),
            "summary": AnalyzerAdapter.summary_to_dict(analysis, risks),
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {"error": f"分析失败: {str(e)}"},
            ensure_ascii=False,
        )
