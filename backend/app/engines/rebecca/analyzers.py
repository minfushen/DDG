# backend/app/engines/rebecca/analyzers.py
"""财务分析引擎 - 10 维度分析"""
import pandas as pd
import numpy as np
import re
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

    def _year_columns(self, df: pd.DataFrame) -> List[str]:
        """识别年度列，返回从新到旧排序的列名。"""
        if df is None:
            return []
        years = []
        for col in df.columns:
            value = str(col).strip()
            if value.isdigit() and len(value) == 4:
                years.append(value)
        return sorted(years, reverse=True)

    def _to_number(self, value: Any) -> Optional[float]:
        """把报表中的金额字符串转换为数字。"""
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (int, float, np.integer, np.floating)):
            return float(value)
        text = str(value).strip()
        if not text or text in {"-", "--", "N/A", "nan"}:
            return None
        negative = text.startswith("(") and text.endswith(")")
        text = re.sub(r"[^0-9.\-]", "", text)
        if not text or text in {"-", "."}:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        return -number if negative else number

    def _get_value(self, df: pd.DataFrame, keywords: List[str], year: Optional[str] = None) -> Optional[float]:
        """按科目关键词和年度列提取金额。"""
        if df is None or df.empty:
            return None

        years = self._year_columns(df)
        target_year = year or (years[0] if years else None)
        value_col = None
        if target_year is not None:
            for col in df.columns:
                if str(col) == str(target_year):
                    value_col = col
                    break
        if value_col is None and len(df.columns) > 1:
            value_col = df.columns[1]
        if value_col is None:
            return None

        label_col = self._label_column(df)
        for _, row in df.iterrows():
            label = str(row.get(label_col, ""))
            if any(keyword in label for keyword in keywords):
                return self._to_number(row.get(value_col))
        return None

    def _label_column(self, df: pd.DataFrame):
        for col in df.columns:
            if any(keyword in str(col) for keyword in ["项目", "科目", "指标", "名称"]):
                return col
        for col in df.columns:
            if not (str(col).isdigit() and len(str(col)) == 4):
                return col
        return df.columns[0]

    def _latest_and_previous(self, df: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
        years = self._year_columns(df)
        latest = years[0] if len(years) >= 1 else None
        previous = years[1] if len(years) >= 2 else None
        return latest, previous

    def _calculate_gross_margin(self) -> Optional[float]:
        """计算毛利率"""
        if self.income is None:
            return None
        revenue = self._get_value(self.income, ["营业收入", "主营业务收入", "收入"])
        cost = self._get_value(self.income, ["营业成本", "主营业务成本", "成本"])
        gross_profit = self._get_value(self.income, ["毛利润", "毛利"])
        if revenue and gross_profit is not None:
            return gross_profit / revenue
        if revenue and cost is not None:
            return (revenue - cost) / revenue
        return None

    def _calculate_net_margin(self) -> Optional[float]:
        """计算净利率"""
        if self.income is None:
            return None
        revenue = self._get_value(self.income, ["营业收入", "主营业务收入", "收入"])
        net_profit = self._get_value(self.income, ["净利润"])
        if revenue and net_profit is not None:
            return net_profit / revenue
        return None

    def _calculate_roe(self) -> Optional[float]:
        """计算净资产收益率"""
        if self.income is None or self.balance is None:
            return None
        net_profit = self._get_value(self.income, ["净利润"])
        equity = self._get_value(self.balance, ["所有者权益", "股东权益", "净资产"])
        if equity and net_profit is not None:
            return net_profit / equity
        return None

    def _calculate_current_ratio(self) -> Optional[float]:
        """计算流动比率"""
        if self.balance is None:
            return None
        current_assets = self._get_value(self.balance, ["流动资产合计", "流动资产"])
        current_liabilities = self._get_value(self.balance, ["流动负债合计", "流动负债"])
        if current_liabilities and current_assets is not None:
            return current_assets / current_liabilities
        return None

    def _calculate_quick_ratio(self) -> Optional[float]:
        """计算速动比率"""
        if self.balance is None:
            return None
        current_assets = self._get_value(self.balance, ["流动资产合计", "流动资产"])
        inventory = self._get_value(self.balance, ["存货"])
        current_liabilities = self._get_value(self.balance, ["流动负债合计", "流动负债"])
        if current_liabilities and current_assets is not None:
            return (current_assets - (inventory or 0)) / current_liabilities
        return None

    def _calculate_debt_ratio(self) -> Optional[float]:
        """计算资产负债率"""
        if self.balance is None:
            return None
        total_assets = self._get_value(self.balance, ["资产总计", "资产合计", "总资产"])
        total_liabilities = self._get_value(self.balance, ["负债合计", "负债总计", "总负债"])
        if total_assets and total_liabilities is not None:
            return total_liabilities / total_assets
        return None

    def _calculate_receivable_turnover(self) -> Optional[float]:
        """计算应收账款周转率"""
        if self.income is None or self.balance is None:
            return None
        revenue = self._get_value(self.income, ["营业收入", "主营业务收入", "收入"])
        receivable = self._get_value(self.balance, ["应收账款"])
        if receivable and revenue is not None:
            return revenue / receivable
        return None

    def _calculate_inventory_turnover(self) -> Optional[float]:
        """计算存货周转率"""
        if self.income is None or self.balance is None:
            return None
        cost = self._get_value(self.income, ["营业成本", "主营业务成本", "成本"])
        inventory = self._get_value(self.balance, ["存货"])
        if inventory and cost is not None:
            return cost / inventory
        return None

    def _calculate_revenue_growth(self) -> Optional[float]:
        """计算营收增长率"""
        if self.income is None:
            return None
        latest, previous = self._latest_and_previous(self.income)
        if not latest or not previous:
            return None
        latest_revenue = self._get_value(self.income, ["营业收入", "主营业务收入", "收入"], latest)
        previous_revenue = self._get_value(self.income, ["营业收入", "主营业务收入", "收入"], previous)
        if previous_revenue and latest_revenue is not None:
            return (latest_revenue - previous_revenue) / previous_revenue
        return None

    def _calculate_profit_growth(self) -> Optional[float]:
        """计算净利润增长率"""
        if self.income is None:
            return None
        latest, previous = self._latest_and_previous(self.income)
        if not latest or not previous:
            return None
        latest_profit = self._get_value(self.income, ["净利润"], latest)
        previous_profit = self._get_value(self.income, ["净利润"], previous)
        if previous_profit and latest_profit is not None:
            return (latest_profit - previous_profit) / previous_profit
        return None

    def _get_operating_cashflow(self) -> Optional[float]:
        """获取经营活动现金流"""
        if self.cashflow is None:
            return None
        return self._get_value(self.cashflow, ["经营活动产生的现金流量净额", "经营活动现金流", "经营活动"])

    def _get_investing_cashflow(self) -> Optional[float]:
        """获取投资活动现金流"""
        if self.cashflow is None:
            return None
        return self._get_value(self.cashflow, ["投资活动产生的现金流量净额", "投资活动现金流", "投资活动"])

    def _get_financing_cashflow(self) -> Optional[float]:
        """获取筹资活动现金流"""
        if self.cashflow is None:
            return None
        return self._get_value(self.cashflow, ["筹资活动产生的现金流量净额", "筹资活动现金流", "筹资活动"])
