# ========================================
# Rebecca 引擎工具
# 用于财务Agent进行深度财务分析
# ========================================

from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json


class RebeccaAnalyzeInput(BaseModel):
    """Rebecca 分析输入"""
    financial_data_json: str = Field(description="财务数据 JSON 字符串")


class RebeccaAnalyzeTool(BaseTool):
    """使用 Rebecca 引擎进行 10 维度财务分析工具"""
    name: str = "rebecca_analyze"
    description: str = "使用 Rebecca 引擎进行 10 维度财务分析。当需要进行深度财务分析时调用此工具。"
    args_schema: Type[BaseModel] = RebeccaAnalyzeInput

    def _run(self, financial_data_json: str) -> str:
        """运行工具"""
        try:
            import pandas as pd
            from app.engines.rebecca.analyzers import FinancialDDAnalyzer
            from app.engines.rebecca.adapter import AnalyzerAdapter

            # 解析财务数据
            financial_data_raw = json.loads(financial_data_json)

            # 转换为 DataFrame
            financial_data = {}
            if "income_statement" in financial_data_raw:
                financial_data["income_statement"] = pd.DataFrame(
                    financial_data_raw["income_statement"]
                )
            if "balance_sheet" in financial_data_raw:
                financial_data["balance_sheet"] = pd.DataFrame(
                    financial_data_raw["balance_sheet"]
                )
            if "cash_flow" in financial_data_raw:
                financial_data["cash_flow"] = pd.DataFrame(
                    financial_data_raw["cash_flow"]
                )

            # 运行 Rebecca 分析
            analyzer = FinancialDDAnalyzer(financial_data)
            analysis_result = analyzer.generate_full_analysis()
            risks = analyzer.identify_risks()

            # 转换结果
            analysis_json = AnalyzerAdapter.analysis_to_json(analysis_result)
            risks_json = AnalyzerAdapter.risks_to_dict(risks)

            return json.dumps({
                "success": True,
                "analysis": analysis_json,
                "risks": risks_json,
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
            }, ensure_ascii=False)


# 创建工具实例
rebecca_analyze = RebeccaAnalyzeTool()
