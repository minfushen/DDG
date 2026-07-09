"""Smoke tests for Yuandian legal/company tools.

These tests call the live Yuandian MCP API and require YUANDIAN_API_KEY to be set.
They are NOT included in CI; run manually to verify API connectivity.
"""

import pytest

# Skip entire module if key is not available.  settings.py reads backend/.env,
# so we rely on that rather than the process environment.
from app.config.settings import settings

pytestmark = pytest.mark.skipif(
    not settings.YUANDIAN_API_KEY,
    reason="YUANDIAN_API_KEY not configured",
)

ENTERPRISE = "华为技术有限公司"


class TestYuandianLegalTool:
    def test_build_legal_risk_profile(self):
        from app.agents.tools.yuandian_legal_tool import build_legal_risk_profile

        result = build_legal_risk_profile(ENTERPRISE, top_k=3)
        assert result["success"] is True
        assert result["enterprise_name"] == ENTERPRISE
        assert "case_summaries" in result
        assert "summary" in result
        if result.get("total", 0) > 0:
            first = result["case_summaries"][0]
            assert "court_level" in first
            assert "parties" in first

    def test_search_laws(self):
        from app.agents.tools.yuandian_legal_tool import search_laws

        result = search_laws("公司法 股东出资", top_k=3)
        assert result["success"] is True


class TestYuandianCompanyTool:
    def test_build_business_profile(self):
        from app.agents.tools.yuandian_company_tool import build_business_profile

        result = build_business_profile(ENTERPRISE)
        assert result["success"] is True
        assert result["enterprise_name"] == ENTERPRISE
        assert result.get("enterprise_id")
        assert result.get("tyshxydm")
        basic = result.get("basic_info") or {}
        assert basic.get("success") is True
        risk = result.get("risk_summary") or {}
        assert risk.get("success") is True
