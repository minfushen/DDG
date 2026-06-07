# backend/app/engines/rebecca/adapter.py
"""Rebecca 数据适配器 - 将 DataFrame 输出转换为 JSON 可序列化格式"""
import pandas as pd
from typing import Dict, Any, List, Optional


class AnalyzerAdapter:
    """Rebecca 数据适配器"""

    @staticmethod
    def dataframe_to_dict(df: pd.DataFrame) -> Dict[str, Any]:
        """
        DataFrame → 嵌套字典

        Args:
            df: pandas DataFrame

        Returns:
            Dict: 包含 columns、index、data 的字典
        """
        if df is None:
            return None

        return {
            "columns": [str(c) for c in df.columns],
            "index": [str(i) for i in df.index],
            "data": df.values.tolist(),
        }

    @staticmethod
    def analysis_to_json(analysis: Dict[str, Dict[str, pd.DataFrame]]) -> Dict:
        """
        完整分析结果 → JSON

        Args:
            analysis: 分析结果，结构为 {dimension: {table_name: DataFrame}}

        Returns:
            Dict: JSON 可序列化的分析结果
        """
        result = {}
        for dimension, tables in analysis.items():
            result[dimension] = {}
            for table_name, df in tables.items():
                if isinstance(df, pd.DataFrame):
                    result[dimension][table_name] = AnalyzerAdapter.dataframe_to_dict(df)
                else:
                    result[dimension][table_name] = df
        return result

    @staticmethod
    def risks_to_summary(risks: Dict[str, List[str]]) -> str:
        """
        风险结果 → 文本摘要（供 LLM 使用）

        Args:
            risks: 风险字典，结构为 {level: [risk_items]}

        Returns:
            str: 格式化的风险摘要文本
        """
        lines = []
        for level, items in risks.items():
            if items:
                level_name = {
                    "high": "高风险",
                    "medium": "中风险",
                    "low": "低风险",
                }.get(level, level)
                lines.append(f"\n【{level_name}】")
                for item in items:
                    lines.append(f"  - {item}")
        return "\n".join(lines) if lines else "暂无风险提示"

    @staticmethod
    def risks_to_dict(risks: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        风险结果 → 字典（确保可 JSON 序列化）

        Args:
            risks: 风险字典

        Returns:
            Dict: 风险字典
        """
        return {level: list(items) for level, items in risks.items()}

    @staticmethod
    def summary_to_dict(
        analysis_result: Dict[str, Any],
        risks: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        生成分析摘要

        Args:
            analysis_result: 分析结果
            risks: 风险结果

        Returns:
            Dict: 包含分析摘要和风险摘要的字典
        """
        # 提取关键指标
        key_indicators = {}

        if "profitability" in analysis_result:
            prof = analysis_result["profitability"]
            if "gross_profit_margin" in prof:
                # 转换为可序列化格式
                if isinstance(prof["gross_profit_margin"], pd.DataFrame):
                    key_indicators["gross_margin"] = AnalyzerAdapter.dataframe_to_dict(prof["gross_profit_margin"])
                else:
                    key_indicators["gross_margin"] = prof["gross_profit_margin"]
            if "net_profit_margin" in prof:
                if isinstance(prof["net_profit_margin"], pd.DataFrame):
                    key_indicators["net_margin"] = AnalyzerAdapter.dataframe_to_dict(prof["net_profit_margin"])
                else:
                    key_indicators["net_margin"] = prof["net_profit_margin"]

        if "solvency" in analysis_result:
            solv = analysis_result["solvency"]
            if "current_ratio" in solv:
                if isinstance(solv["current_ratio"], pd.DataFrame):
                    key_indicators["current_ratio"] = AnalyzerAdapter.dataframe_to_dict(solv["current_ratio"])
                else:
                    key_indicators["current_ratio"] = solv["current_ratio"]
            if "debt_ratio" in solv:
                if isinstance(solv["debt_ratio"], pd.DataFrame):
                    key_indicators["debt_ratio"] = AnalyzerAdapter.dataframe_to_dict(solv["debt_ratio"])
                else:
                    key_indicators["debt_ratio"] = solv["debt_ratio"]

        # 统计风险数量
        risk_counts = {
            "high": len(risks.get("high", [])),
            "medium": len(risks.get("medium", [])),
            "low": len(risks.get("low", [])),
        }

        return {
            "key_indicators": key_indicators,
            "risk_counts": risk_counts,
            "risk_summary": AnalyzerAdapter.risks_to_summary(risks),
            "total_risks": sum(risk_counts.values()),
        }
