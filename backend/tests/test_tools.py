# backend/tests/test_tools.py
"""Agent 工具测试"""
import pytest
import json
from app.agents.tools.analyze_tool import analyze_financial_data
from app.agents.tools.explain_tool import explain_analysis_result
from app.agents.tools.knowledge_tool import search_knowledge_base
from app.agents.tools.report_tool import generate_due_diligence_report


def test_analyze_tool():
    """测试分析工具"""
    financial_data = {
        "income_statement": {
            "revenue": 1000000000,
            "cost_of_goods_sold": 600000000,
            "gross_profit": 400000000,
        },
        "balance_sheet": {
            "total_assets": 5000000000,
            "total_liabilities": 3000000000,
            "total_equity": 2000000000,
        },
        "cash_flow": {
            "operating_cash_flow": 300000000,
            "investing_cash_flow": -200000000,
            "financing_cash_flow": -50000000,
        },
    }

    result = analyze_financial_data.invoke({
        "financial_data_json": json.dumps(financial_data)
    })

    # 验证返回 JSON 字符串
    assert isinstance(result, str)
    data = json.loads(result)
    assert "analysis" in data
    assert "risks" in data


def test_explain_tool():
    """测试解读工具"""
    result = explain_analysis_result.invoke({
        "indicator_name": "毛利率",
        "indicator_value": 40.0,
        "industry_average": 35.0,
        "trend": "稳定",
    })

    assert isinstance(result, str)
    assert "毛利率" in result
    assert "40.0" in result


def test_knowledge_tool():
    """测试知识检索工具"""
    result = search_knowledge_base.invoke({
        "query": "应收账款",
        "knowledge_type": "all",
    })

    assert isinstance(result, str)
    # Mock 数据应该返回结果
    assert len(result) > 0


def test_knowledge_tool_with_type():
    """测试知识检索工具 - 指定类型"""
    result = search_knowledge_base.invoke({
        "query": "会计准则",
        "knowledge_type": "regulation",
    })

    assert isinstance(result, str)
