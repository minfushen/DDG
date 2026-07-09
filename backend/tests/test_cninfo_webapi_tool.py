"""Smoke tests for cninfo_webapi_tool.

These tests call the live cninfo API and require CNINFO_ACCESS_TOKEN to be set.
They are NOT included in CI; run manually to verify API connectivity.
"""

import os
import pytest

# Skip entire module if token is not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("CNINFO_ACCESS_TOKEN"),
    reason="CNINFO_ACCESS_TOKEN not set",
)

STOCK = "600519"  # 贵州茅台


class TestFinancialAPIs:
    def test_balance_sheet(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_balance_sheet

        result = fetch_balance_sheet(STOCK, "2024-12-31")
        assert result["success"] is True
        assert result["total"] > 0
        record = result["records"][0]
        assert record["SECCODE"] == STOCK
        assert record["F038N"] is not None  # 资产总计

    def test_cash_flow(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_cash_flow

        result = fetch_cash_flow(STOCK, "2024-12-31")
        assert result["success"] is True
        assert result["total"] > 0

    def test_financial_indicators(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_financial_indicators

        result = fetch_financial_indicators(STOCK, "2024-12-31")
        assert result["success"] is True
        assert result["total"] > 0


class TestShareholderAPIs:
    def test_top_shareholders(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_top_shareholders

        result = fetch_top_shareholders(STOCK)
        assert result["success"] is True
        assert result["total"] > 0

    def test_actual_controller(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_actual_controller

        result = fetch_actual_controller(STOCK)
        assert result["success"] is True
        assert result["total"] > 0


class TestLegalAPIs:
    def test_litigation(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_litigation

        result = fetch_litigation(STOCK)
        assert result["success"] is True
        # 茅台可能没有诉讼，total 可以为 0

    def test_penalties(self):
        from app.agents.tools.cninfo_webapi_tool import fetch_penalties

        result = fetch_penalties(STOCK)
        assert result["success"] is True
        assert result["total"] > 0  # 茅台有处罚记录


class TestCompositeAPIs:
    def test_financial_summary(self):
        from app.agents.tools.cninfo_webapi_tool import build_financial_summary

        summary = build_financial_summary(STOCK, "2024-12-31")
        assert summary["stock_code"] == STOCK
        assert summary["balance_sheet"]["total_assets"] is not None
        assert summary["cash_flow"]["operating"] is not None
        assert summary["indicators"]["roe"] is not None

    def test_risk_profile(self):
        from app.agents.tools.cninfo_webapi_tool import build_risk_profile

        profile = build_risk_profile(STOCK)
        assert profile["stock_code"] == STOCK
        assert "litigation" in profile
        assert "penalties" in profile

    def test_shareholder_profile(self):
        from app.agents.tools.cninfo_webapi_tool import build_shareholder_profile

        profile = build_shareholder_profile(STOCK)
        assert profile["stock_code"] == STOCK
        assert profile["top_shareholders"]["count"] > 0
        assert profile["actual_controller"]["count"] > 0
