# backend/app/engines/rebecca/analyzers.py
"""财务分析引擎 - 10 维度分析"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class AnalysisDimension(str, Enum):
    """分析维度"""
    PROFITABILITY = "profitability"          # 盈利能力
    SOLVENCY = "solvency"                    # 偿债能力
    EFFICIENCY = "efficiency"                # 营运能力
    GROWTH = "growth"                        # 成长能力
    CASH_FLOW = "cash_flow"                  # 现金流分析
    COST_STRUCTURE = "cost_structure"        # 成本结构
    ASSET_QUALITY = "asset_quality"          # 资产质量
    DEBT_STRUCTURE = "debt_structure"        # 负债结构
    PROFITABILITY_TREND = "profitability_trend"  # 盈利趋势
    RISK_ASSESSMENT = "risk_assessment"      # 风险评估


@dataclass
class AnalysisResult:
    """分析结果"""
    dimension: str
    tables: Dict[str, pd.DataFrame]
    summary: str
    risk_level: str  # high, medium, low


class FinancialDDAnalyzer:
    """财务尽调分析器"""

    def __init__(
        self,
        financial_data: Dict[str, pd.DataFrame],
        supplementary_data: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化分析器

        Args:
            financial_data: 财务数据，包含 income_statement, balance_sheet, cash_flow
            supplementary_data: 补充数据（可选）
        """
        self.income = financial_data.get("income_statement")
        self.balance = financial_data.get("balance_sheet")
        self.cashflow = financial_data.get("cash_flow")
        self.supplementary = supplementary_data or {}

        # 分析结果缓存
        self._analysis_results: Dict[str, AnalysisResult] = {}

    def generate_full_analysis(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        执行完整的 10 维度分析

        Returns:
            Dict: 包含 10 个维度的分析结果，每个维度包含多个表格
        """
        analysis = {}

        # 1. 盈利能力分析
        analysis["profitability"] = self._analyze_profitability()

        # 2. 偿债能力分析
        analysis["solvency"] = self._analyze_solvency()

        # 3. 营运能力分析
        analysis["efficiency"] = self._analyze_efficiency()

        # 4. 成长能力分析
        analysis["growth"] = self._analyze_growth()

        # 5. 现金流分析
        analysis["cash_flow"] = self._analyze_cash_flow()

        # 6. 成本结构分析
        analysis["cost_structure"] = self._analyze_cost_structure()

        # 7. 资产质量分析
        analysis["asset_quality"] = self._analyze_asset_quality()

        # 8. 负债结构分析
        analysis["debt_structure"] = self._analyze_debt_structure()

        # 9. 盈利趋势分析
        analysis["profitability_trend"] = self._analyze_profitability_trend()

        # 10. 风险评估
        analysis["risk_assessment"] = self._analyze_risk_assessment()

        return analysis

    def identify_risks(self) -> Dict[str, List[str]]:
        """
        识别风险点

        Returns:
            Dict: 按风险等级分类的风险点列表
        """
        risks = {
            "high": [],
            "medium": [],
            "low": [],
        }

        # 盈利能力风险
        if self.income is not None:
            gross_margin = self._calculate_gross_margin()
            if gross_margin is not None and gross_margin < 0.2:
                risks["high"].append(f"毛利率过低: {gross_margin:.1%}")
            elif gross_margin is not None and gross_margin < 0.3:
                risks["medium"].append(f"毛利率偏低: {gross_margin:.1%}")

        # 偿债能力风险
        if self.balance is not None:
            current_ratio = self._calculate_current_ratio()
            if current_ratio is not None and current_ratio < 1:
                risks["high"].append(f"流动比率不足: {current_ratio:.2f}")
            elif current_ratio is not None and current_ratio < 1.5:
                risks["medium"].append(f"流动比率偏低: {current_ratio:.2f}")

            debt_ratio = self._calculate_debt_ratio()
            if debt_ratio is not None and debt_ratio > 0.7:
                risks["high"].append(f"资产负债率过高: {debt_ratio:.1%}")
            elif debt_ratio is not None and debt_ratio > 0.6:
                risks["medium"].append(f"资产负债率偏高: {debt_ratio:.1%}")

        # 现金流风险
        if self.cashflow is not None:
            operating_cashflow = self._get_operating_cashflow()
            if operating_cashflow is not None and operating_cashflow < 0:
                risks["high"].append("经营活动现金流为负")

        return risks

    def _analyze_profitability(self) -> Dict[str, pd.DataFrame]:
        """盈利能力分析"""
        tables = {}

        # 毛利率分析表
        gross_margin = self._calculate_gross_margin()
        tables["gross_profit_margin"] = pd.DataFrame({
            "指标": ["毛利率"],
            "本期": [f"{gross_margin:.1%}" if gross_margin else "N/A"],
            "行业平均": ["35%"],
            "评价": ["优秀" if gross_margin and gross_margin > 0.35 else "一般"],
        })

        # 净利率分析表
        net_margin = self._calculate_net_margin()
        tables["net_profit_margin"] = pd.DataFrame({
            "指标": ["净利率"],
            "本期": [f"{net_margin:.1%}" if net_margin else "N/A"],
            "行业平均": ["10%"],
            "评价": ["优秀" if net_margin and net_margin > 0.1 else "一般"],
        })

        # ROE 分析表
        roe = self._calculate_roe()
        tables["roe"] = pd.DataFrame({
            "指标": ["净资产收益率(ROE)"],
            "本期": [f"{roe:.1%}" if roe else "N/A"],
            "行业平均": ["15%"],
            "评价": ["优秀" if roe and roe > 0.15 else "一般"],
        })

        return tables

    def _analyze_solvency(self) -> Dict[str, pd.DataFrame]:
        """偿债能力分析"""
        tables = {}

        # 流动比率分析表
        current_ratio = self._calculate_current_ratio()
        tables["current_ratio"] = pd.DataFrame({
            "指标": ["流动比率"],
            "本期": [f"{current_ratio:.2f}" if current_ratio else "N/A"],
            "行业平均": ["1.5"],
            "评价": ["良好" if current_ratio and current_ratio >= 1.5 else "需关注"],
        })

        # 速动比率分析表
        quick_ratio = self._calculate_quick_ratio()
        tables["quick_ratio"] = pd.DataFrame({
            "指标": ["速动比率"],
            "本期": [f"{quick_ratio:.2f}" if quick_ratio else "N/A"],
            "行业平均": ["1.0"],
            "评价": ["良好" if quick_ratio and quick_ratio >= 1.0 else "需关注"],
        })

        # 资产负债率分析表
        debt_ratio = self._calculate_debt_ratio()
        tables["debt_ratio"] = pd.DataFrame({
            "指标": ["资产负债率"],
            "本期": [f"{debt_ratio:.1%}" if debt_ratio else "N/A"],
            "行业平均": ["60%"],
            "评价": ["良好" if debt_ratio and debt_ratio <= 0.6 else "需关注"],
        })

        return tables

    def _analyze_efficiency(self) -> Dict[str, pd.DataFrame]:
        """营运能力分析"""
        tables = {}

        # 应收账款周转率
        receivable_turnover = self._calculate_receivable_turnover()
        tables["receivable_turnover"] = pd.DataFrame({
            "指标": ["应收账款周转率"],
            "本期": [f"{receivable_turnover:.1f}" if receivable_turnover else "N/A"],
            "行业平均": ["6.0"],
            "评价": ["良好" if receivable_turnover and receivable_turnover >= 6 else "需关注"],
        })

        # 存货周转率
        inventory_turnover = self._calculate_inventory_turnover()
        tables["inventory_turnover"] = pd.DataFrame({
            "指标": ["存货周转率"],
            "本期": [f"{inventory_turnover:.1f}" if inventory_turnover else "N/A"],
            "行业平均": ["5.0"],
            "评价": ["良好" if inventory_turnover and inventory_turnover >= 5 else "需关注"],
        })

        return tables

    def _analyze_growth(self) -> Dict[str, pd.DataFrame]:
        """成长能力分析"""
        tables = {}

        # 营收增长率
        revenue_growth = self._calculate_revenue_growth()
        tables["revenue_growth"] = pd.DataFrame({
            "指标": ["营业收入增长率"],
            "本期": [f"{revenue_growth:.1%}" if revenue_growth else "N/A"],
            "行业平均": ["10%"],
            "评价": ["优秀" if revenue_growth and revenue_growth > 0.1 else "一般"],
        })

        # 净利润增长率
        profit_growth = self._calculate_profit_growth()
        tables["profit_growth"] = pd.DataFrame({
            "指标": ["净利润增长率"],
            "本期": [f"{profit_growth:.1%}" if profit_growth else "N/A"],
            "行业平均": ["15%"],
            "评价": ["优秀" if profit_growth and profit_growth > 0.15 else "一般"],
        })

        return tables

    def _analyze_cash_flow(self) -> Dict[str, pd.DataFrame]:
        """现金流分析"""
        tables = {}

        # 现金流结构分析
        operating = self._get_operating_cashflow()
        investing = self._get_investing_cashflow()
        financing = self._get_financing_cashflow()

        tables["cashflow_structure"] = pd.DataFrame({
            "项目": ["经营活动现金流", "投资活动现金流", "筹资活动现金流"],
            "金额": [
                f"{operating:,.0f}" if operating else "N/A",
                f"{investing:,.0f}" if investing else "N/A",
                f"{financing:,.0f}" if financing else "N/A",
            ],
            "评价": [
                "正常" if operating and operating > 0 else "需关注",
                "扩张" if investing and investing < 0 else "收缩",
                "融资" if financing and financing > 0 else "偿债",
            ],
        })

        return tables

    def _analyze_cost_structure(self) -> Dict[str, pd.DataFrame]:
        """成本结构分析"""
        tables = {}

        # 成本构成分析
        tables["cost_composition"] = pd.DataFrame({
            "项目": ["营业成本", "销售费用", "管理费用", "财务费用"],
            "占比": ["60%", "10%", "15%", "5%"],
            "评价": ["正常", "正常", "正常", "正常"],
        })

        return tables

    def _analyze_asset_quality(self) -> Dict[str, pd.DataFrame]:
        """资产质量分析"""
        tables = {}

        # 资产构成分析
        tables["asset_composition"] = pd.DataFrame({
            "项目": ["流动资产", "固定资产", "无形资产", "其他资产"],
            "占比": ["40%", "35%", "15%", "10%"],
            "评价": ["正常", "正常", "正常", "正常"],
        })

        return tables

    def _analyze_debt_structure(self) -> Dict[str, pd.DataFrame]:
        """负债结构分析"""
        tables = {}

        # 负债构成分析
        tables["debt_composition"] = pd.DataFrame({
            "项目": ["流动负债", "长期负债"],
            "占比": ["60%", "40%"],
            "评价": ["正常", "正常"],
        })

        return tables

    def _analyze_profitability_trend(self) -> Dict[str, pd.DataFrame]:
        """盈利趋势分析"""
        tables = {}

        # 趋势分析表
        tables["trend"] = pd.DataFrame({
            "指标": ["毛利率", "净利率", "ROE"],
            "趋势": ["稳定", "上升", "稳定"],
            "预测": ["继续保持", "有望提升", "保持稳定"],
        })

        return tables

    def _analyze_risk_assessment(self) -> Dict[str, pd.DataFrame]:
        """风险评估"""
        tables = {}

        risks = self.identify_risks()

        # 风险汇总表
        risk_items = []
        for level, items in risks.items():
            for item in items:
                risk_items.append({"风险等级": level, "风险描述": item})

        if not risk_items:
            risk_items.append({"风险等级": "low", "风险描述": "暂无重大风险"})

        tables["risk_summary"] = pd.DataFrame(risk_items)

        return tables

    # ========== 指标计算方法 ==========

    def _calculate_gross_margin(self) -> Optional[float]:
        """计算毛利率"""
        if self.income is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 0.40  # Mock 数据

    def _calculate_net_margin(self) -> Optional[float]:
        """计算净利率"""
        if self.income is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 0.15  # Mock 数据

    def _calculate_roe(self) -> Optional[float]:
        """计算净资产收益率"""
        if self.income is None or self.balance is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 0.18  # Mock 数据

    def _calculate_current_ratio(self) -> Optional[float]:
        """计算流动比率"""
        if self.balance is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 1.33  # Mock 数据

    def _calculate_quick_ratio(self) -> Optional[float]:
        """计算速动比率"""
        if self.balance is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 1.0  # Mock 数据

    def _calculate_debt_ratio(self) -> Optional[float]:
        """计算资产负债率"""
        if self.balance is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 0.60  # Mock 数据

    def _calculate_receivable_turnover(self) -> Optional[float]:
        """计算应收账款周转率"""
        if self.income is None or self.balance is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 8.0  # Mock 数据

    def _calculate_inventory_turnover(self) -> Optional[float]:
        """计算存货周转率"""
        if self.income is None or self.balance is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 6.0  # Mock 数据

    def _calculate_revenue_growth(self) -> Optional[float]:
        """计算营收增长率"""
        if self.income is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 0.12  # Mock 数据

    def _calculate_profit_growth(self) -> Optional[float]:
        """计算净利润增长率"""
        if self.income is None:
            return None
        # TODO: 从 DataFrame 中提取数据计算
        return 0.18  # Mock 数据

    def _get_operating_cashflow(self) -> Optional[float]:
        """获取经营活动现金流"""
        if self.cashflow is None:
            return None
        # TODO: 从 DataFrame 中提取数据
        return 300000000  # Mock 数据

    def _get_investing_cashflow(self) -> Optional[float]:
        """获取投资活动现金流"""
        if self.cashflow is None:
            return None
        # TODO: 从 DataFrame 中提取数据
        return -200000000  # Mock 数据

    def _get_financing_cashflow(self) -> Optional[float]:
        """获取筹资活动现金流"""
        if self.cashflow is None:
            return None
        # TODO: 从 DataFrame 中提取数据
        return -50000000  # Mock 数据
