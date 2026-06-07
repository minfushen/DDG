# backend/tests/test_adapter.py
"""适配器测试"""
import pytest
import pandas as pd
from app.engines.rebecca.adapter import AnalyzerAdapter


def test_dataframe_to_dict():
    """测试 DataFrame 转字典"""
    df = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"],
    })

    result = AnalyzerAdapter.dataframe_to_dict(df)

    assert "columns" in result
    assert "index" in result
    assert "data" in result
    assert result["columns"] == ["col1", "col2"]
    assert len(result["data"]) == 3


def test_dataframe_to_dict_none():
    """测试 None 输入"""
    result = AnalyzerAdapter.dataframe_to_dict(None)
    assert result is None


def test_analysis_to_json():
    """测试分析结果转 JSON"""
    analysis = {
        "profitability": {
            "gross_profit_margin": pd.DataFrame({
                "指标": ["毛利率"],
                "本期": ["40%"],
            }),
        },
    }

    result = AnalyzerAdapter.analysis_to_json(analysis)

    assert "profitability" in result
    assert "gross_profit_margin" in result["profitability"]
    assert "columns" in result["profitability"]["gross_profit_margin"]


def test_risks_to_summary():
    """测试风险摘要生成"""
    risks = {
        "high": ["资产负债率过高"],
        "medium": ["应收账款周转率偏低"],
        "low": ["现金流状况良好"],
    }

    result = AnalyzerAdapter.risks_to_summary(risks)

    assert "高风险" in result
    assert "中风险" in result
    assert "低风险" in result
    assert "资产负债率过高" in result


def test_risks_to_summary_empty():
    """测试空风险摘要"""
    risks = {"high": [], "medium": [], "low": []}
    result = AnalyzerAdapter.risks_to_summary(risks)
    assert result == "暂无风险提示"


def test_risks_to_dict():
    """测试风险转字典"""
    risks = {
        "high": ["风险1", "风险2"],
        "medium": ["风险3"],
        "low": [],
    }

    result = AnalyzerAdapter.risks_to_dict(risks)

    assert result["high"] == ["风险1", "风险2"]
    assert result["medium"] == ["风险3"]
    assert result["low"] == []
