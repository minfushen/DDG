# backend/tests/test_analyzers.py
"""分析器测试"""
import pytest
import pandas as pd
from app.engines.rebecca.analyzers import FinancialDDAnalyzer


@pytest.fixture
def sample_financial_data():
    """示例财务数据"""
    return {
        "income_statement": pd.DataFrame({
            "项目": ["营业收入", "营业成本", "毛利", "净利润"],
            "本期": [1000000000, 600000000, 400000000, 150000000],
            "上期": [900000000, 550000000, 350000000, 120000000],
        }),
        "balance_sheet": pd.DataFrame({
            "项目": ["资产总计", "负债合计", "所有者权益", "流动资产", "流动负债"],
            "本期": [5000000000, 3000000000, 2000000000, 2000000000, 1500000000],
            "上期": [4500000000, 2800000000, 1700000000, 1800000000, 1400000000],
        }),
        "cash_flow": pd.DataFrame({
            "项目": ["经营活动现金流", "投资活动现金流", "筹资活动现金流"],
            "本期": [300000000, -200000000, -50000000],
            "上期": [250000000, -180000000, -40000000],
        }),
    }


def test_generate_full_analysis(sample_financial_data):
    """测试完整分析"""
    analyzer = FinancialDDAnalyzer(sample_financial_data)
    result = analyzer.generate_full_analysis()

    # 验证返回 10 个维度
    assert "profitability" in result
    assert "solvency" in result
    assert "efficiency" in result
    assert "growth" in result
    assert "cash_flow" in result
    assert "cost_structure" in result
    assert "asset_quality" in result
    assert "debt_structure" in result
    assert "profitability_trend" in result
    assert "risk_assessment" in result


def test_identify_risks(sample_financial_data):
    """测试风险识别"""
    analyzer = FinancialDDAnalyzer(sample_financial_data)
    risks = analyzer.identify_risks()

    # 验证返回风险字典
    assert "high" in risks
    assert "medium" in risks
    assert "low" in risks
    assert isinstance(risks["high"], list)
    assert isinstance(risks["medium"], list)
    assert isinstance(risks["low"], list)


def test_profitability_analysis(sample_financial_data):
    """测试盈利能力分析"""
    analyzer = FinancialDDAnalyzer(sample_financial_data)
    result = analyzer._analyze_profitability()

    # 验证包含关键表格
    assert "gross_profit_margin" in result
    assert "net_profit_margin" in result
    assert "roe" in result


def test_solvency_analysis(sample_financial_data):
    """测试偿债能力分析"""
    analyzer = FinancialDDAnalyzer(sample_financial_data)
    result = analyzer._analyze_solvency()

    # 验证包含关键表格
    assert "current_ratio" in result
    assert "quick_ratio" in result
    assert "debt_ratio" in result
