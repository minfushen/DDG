# backend/tests/test_analysis_api.py
"""分析 API 测试"""
import pytest
from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "running"


def test_health_check(client: TestClient):
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data


def test_analyze_financial_data(client: TestClient):
    """测试财务分析接口"""
    request_data = {
        "enterprise_name": "测试企业",
        "financial_data": {
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
        },
    }

    response = client.post("/api/v1/analysis/analyze", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["enterprise_name"] == "测试企业"
    assert "analysis_result" in data
    assert "risks" in data


def test_generate_report(client: TestClient):
    """测试报告生成接口"""
    request_data = {
        "enterprise_name": "测试企业",
        "analysis_result": {
            "profitability": {
                "gross_profit_margin": {
                    "columns": ["指标", "本期"],
                    "data": [["毛利率", "40%"]],
                }
            }
        },
        "report_format": "docx",
    }

    response = client.post("/api/v1/analysis/report", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["enterprise_name"] == "测试企业"
    assert "report_path" in data
    assert "download_url" in data
