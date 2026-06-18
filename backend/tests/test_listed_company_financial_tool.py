import json

from app.agents.tools import listed_company_tool


def test_fetch_listed_company_financial_tool_builds_three_statements(monkeypatch):
    def fake_fetch(secu_code, report_name):
        assert secu_code == "300782.SZ"
        rows = [
            {
                "REPORT_DATE": "2025-12-31 00:00:00",
                "REPORT_TYPE": "年报",
                "TOTAL_OPERATE_INCOME": 100.0,
                "OPERATE_COST": 60.0,
                "NETPROFIT": 12.0,
                "TOTAL_ASSETS": 300.0,
                "TOTAL_LIABILITIES": 120.0,
                "TOTAL_EQUITY": 180.0,
                "NETCASH_OPERATE": 25.0,
            },
            {
                "REPORT_DATE": "2024-12-31 00:00:00",
                "REPORT_TYPE": "年报",
                "TOTAL_OPERATE_INCOME": 90.0,
                "OPERATE_COST": 55.0,
                "NETPROFIT": 10.0,
                "TOTAL_ASSETS": 280.0,
                "TOTAL_LIABILITIES": 100.0,
                "TOTAL_EQUITY": 180.0,
                "NETCASH_OPERATE": 20.0,
            },
        ]
        return rows

    monkeypatch.setattr(listed_company_tool, "_fetch_eastmoney_report", fake_fetch)

    payload = json.loads(listed_company_tool.fetch_listed_company_financial._run(
        enterprise_name="卓胜微",
        stock_code="300782",
        stock_exchange="SZ",
    ))

    statements = payload["financial_statements"]
    assert payload["success"] is True
    assert payload["secu_code"] == "300782.SZ"
    assert payload["years"] == ["2025", "2024"]
    assert statements["income_statement"][0]["项目"] == "营业收入"
    assert any(row["项目"] == "毛利润" for row in statements["income_statement"])
    assert statements["balance_sheet"]
    assert statements["cash_flow"]
