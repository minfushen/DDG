from app.agents.tools.akshare_financial_tool import fetch_akshare_financial_data
from app.agents.tools import akshare_financial_tool
from app.agents.tools.cninfo_announcement_tool import (
    announcement_to_evidence,
    classify_announcement,
    clean_cninfo_title,
    fetch_and_extract_annual_report_pdf,
    normalize_cninfo_announcement,
    search_cninfo_announcements,
)
from app.agents.tools.financial_provider_reconciliation import reconcile_financial_providers, reconciliation_to_evidence
from app.agents.research_engine.gap_reflector import reflect_task_gaps
from app.agents.sub_agents import financial_agent


def _sample_extraction_result() -> dict:
    return {
        "success": True,
        "text": (
            "第三节 经营情况讨论与分析\n"
            "2025年，公司实现营业收入100亿元，同比增长12%。"
            "公司主营业务为半导体分立器件和集成电路。\n"
            "主营业务分产品情况\n"
            "产品A 营业收入 50亿元 占比 50%\n"
            "第四节 审计意见\n"
            "标准无保留意见。\n"
            "第五节 重大风险提示\n"
            "市场竞争加剧、原材料价格波动。\n"
        ),
        "tables": [
            [["产品", "营业收入", "占比", "毛利率"], ["产品A", "50亿元", "50%", "30%"]],
        ],
        "metadata": {"page_count": 3, "parser_used": "pdfplumber"},
        "error": "",
    }


def _mock_cninfo_httpx_get(monkeypatch):
    """Mock httpx.get so CNINFO search returns one annual report without network."""
    import httpx

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "announcements": [{
                    "secCode": "300782",
                    "secName": "卓胜微",
                    "orgId": "9900036858",
                    "announcementId": "1225220151",
                    "announcementTitle": "<em>卓胜微</em>：2025年<em>年度报告</em>",
                    "announcementTime": 1777305600000,
                    "adjunctUrl": "finalpage/2026-04-28/1225220151.PDF",
                    "adjunctSize": 4928,
                }],
                "totalRecordNum": 1,
            }

    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: FakeResponse())


def _sample_pipeline_result():
    import pandas as pd
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    return PipelineResult(
        success=True,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 100000000.0},
                {"field": "net_profit", "label": "净利润", "2025": 12000000.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 300000000.0},
                {"field": "total_liabilities", "label": "负债合计", "2025": 120000000.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 20000000.0},
            ]),
        ),
        extraction_result=_sample_extraction_result(),
        main_table_coverage="3/3",
        auto_judgment_rate=1.0,
        needs_human_review=False,
        issues=[],
    )


def test_fetch_and_extract_annual_report_pdf_success(monkeypatch):
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.download_pdf",
        lambda url, timeout=30: b"fake pdf bytes",
    )
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.parse_annual_report_pdf",
        lambda **kwargs: _sample_pipeline_result(),
    )
    item = normalize_cninfo_announcement({
        "secCode": "300782",
        "secName": "卓胜微",
        "orgId": "9900036858",
        "announcementId": "1225220151",
        "announcementTitle": "<em>卓胜微</em>：2025年<em>年度报告</em>",
        "announcementTime": 1777305600000,
        "adjunctUrl": "finalpage/2026-04-28/1225220151.PDF",
        "adjunctSize": 4928,
    })

    result = fetch_and_extract_annual_report_pdf(item)

    assert result["success"] is True
    assert result["pdf_url"].endswith("1225220151.PDF")
    assert result["sections"]["business_review"]
    assert result["sections"]["audit_opinion"]
    assert result["sections"]["major_risk_warnings"]
    assert len(result["main_business_rows"]) >= 1
    evidence_labels = {ev["label"] for ev in result["evidence_items"]}
    assert "巨潮年报-经营情况讨论与分析" in evidence_labels
    assert "巨潮年报-主营业务构成表" in evidence_labels
    assert "年报PDF-三大表覆盖度" in evidence_labels


def test_search_cninfo_annual_report_pdf_extraction(monkeypatch):
    _mock_cninfo_httpx_get(monkeypatch)
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.download_pdf",
        lambda url, timeout=30: b"fake pdf bytes",
    )
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.parse_annual_report_pdf",
        lambda **kwargs: _sample_pipeline_result(),
    )
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.resolve_listed_company",
        lambda *args, **kwargs: {"stock_code": "300782", "stock_exchange": "SZ", "secu_code": "300782.SZ", "security_name": "卓胜微"},
    )

    result = search_cninfo_announcements(
        "卓胜微",
        stock_code="300782",
        extract_pdf_content=True,
        max_pdf_extract=1,
    )

    assert result["success"] is True
    assert len(result["pdf_extraction_results"]) >= 1
    assert len(result["extracted_evidence"]) > 0
    assert len(result["pipeline_results"]) >= 1
    labels = {ev["label"] for ev in result["evidence"]}
    assert any(label.startswith("巨潮年报-") for label in labels)


def test_search_cninfo_pdf_extraction_failure_graceful(monkeypatch):
    _mock_cninfo_httpx_get(monkeypatch)
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.download_pdf",
        lambda url, timeout=30: None,
    )
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.extract_pdf_from_url",
        lambda url, timeout=30: {"success": False, "text": "", "tables": [], "metadata": {}, "error": "download failed"},
    )
    monkeypatch.setattr(
        "app.agents.tools.cninfo_announcement_tool.resolve_listed_company",
        lambda *args, **kwargs: {"stock_code": "300782", "stock_exchange": "SZ", "secu_code": "300782.SZ", "security_name": "卓胜微"},
    )

    result = search_cninfo_announcements(
        "卓胜微",
        stock_code="300782",
        extract_pdf_content=True,
        max_pdf_extract=1,
    )

    assert result["success"] is True
    assert len(result["extracted_evidence"]) == 0
    assert any(ev["label"].startswith("巨潮公告") for ev in result["evidence"])


def test_cninfo_title_cleaning_and_classification():
    title = "<em>卓胜微</em>：2025年<em>年度报告</em>"
    assert clean_cninfo_title(title) == "卓胜微：2025年年度报告"
    assert classify_announcement(title) == "annual_report"
    assert classify_announcement("关于申请向特定对象发行股票的审核问询函回复") == "inquiry_letter"


def test_cninfo_announcement_normalize_and_evidence():
    item = normalize_cninfo_announcement({
        "secCode": "300782",
        "secName": "卓胜微",
        "orgId": "9900036858",
        "announcementId": "1225220151",
        "announcementTitle": "<em>卓胜微</em>：2025年<em>年度报告</em>",
        "announcementTime": 1777305600000,
        "adjunctUrl": "finalpage/2026-04-28/1225220151.PDF",
        "adjunctSize": 4928,
    })

    assert item["title"] == "卓胜微：2025年年度报告"
    assert item["announcement_type"] == "annual_report"
    assert item["pdf_url"].startswith("https://static.cninfo.com.cn/finalpage/")
    assert item["source_type"] == "official_or_authoritative_public_source"

    evidence = announcement_to_evidence(item)
    assert evidence["source_name"] == "巨潮资讯网"
    assert evidence["trust_level"] == "high"
    assert evidence["source_url"].endswith("1225220151.PDF")


def test_akshare_provider_is_optional_when_package_missing(monkeypatch):
    monkeypatch.setattr("app.agents.tools.akshare_financial_tool._akshare_available", lambda: False)
    result = fetch_akshare_financial_data("卓胜微", stock_code="300782", stock_exchange="SZ")
    assert result["success"] is False
    assert result["provider"] == "akshare"
    assert "未安装" in result["error"]


def test_akshare_wide_table_mapping(monkeypatch):
    import pandas as pd

    monkeypatch.setattr("app.agents.tools.akshare_financial_tool._akshare_available", lambda: True)
    monkeypatch.setattr(
        "app.agents.tools.akshare_financial_tool.resolve_listed_company",
        lambda *args, **kwargs: {"stock_code": "300782", "stock_exchange": "SZ", "secu_code": "300782.SZ", "security_name": "卓胜微"},
    )

    class FakeAk:
        @staticmethod
        def stock_financial_report_sina(stock, symbol):
            if symbol == "利润表":
                return pd.DataFrame([
                    {"报告日": "20251231", "是否审计": "是", "营业收入": 100.0, "营业成本": 60.0, "净利润": 12.0, "投资收益": 1.0},
                    {"报告日": "20250930", "是否审计": "未审计", "营业收入": 80.0, "营业成本": 50.0, "净利润": 9.0},
                ])
            if symbol == "资产负债表":
                return pd.DataFrame([{"报告日": "20251231", "是否审计": "是", "资产总计": 300.0, "负债合计": 120.0, "货币资金": 40.0}])
            return pd.DataFrame([{"报告日": "20251231", "是否审计": "是", "经营活动产生的现金流量净额": 20.0}])

    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAk)
    result = akshare_financial_tool.fetch_akshare_financial_data("卓胜微", stock_code="300782", stock_exchange="SZ")

    assert result["success"] is True
    assert result["years"] == ["2025"]
    assert result["financial_statements"]["income_statement"][0]["2025"] == 100.0
    assert result["financial_statements"]["balance_sheet"]
    assert result["financial_statements"]["cash_flow"]


def test_provider_reconciliation_flags_mismatch_and_gap():
    primary = {
        "income_statement": [{"项目": "营业收入", "2025": 100_000_000.0}],
        "balance_sheet": [{"项目": "资产总计", "2025": 300_000_000.0}],
        "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20_000_000.0}],
    }
    secondary = {
        "income_statement": [{"项目": "营业收入", "2025": 96_000_000.0}],
        "balance_sheet": [{"项目": "资产总计", "2025": 300_100_000.0}],
        "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20_000_000.0}],
    }

    reconciliation = reconcile_financial_providers("东方财富公开财报", primary, "AKShare", secondary)
    evidence = reconciliation_to_evidence("测试公司", reconciliation)
    gaps = reflect_task_gaps(
        {"id": "rt_financial", "category": "financial", "question": "财务交叉校验", "required_evidence": []},
        evidence + [{"source_type": "financial_statement", "trust_level": "high"}],
    )

    assert reconciliation["passed"] is False
    assert reconciliation["mismatch_count"] == 1
    assert evidence[0]["requires_manual_review"] is True
    assert any("公开结构化财报数据源" in gap["description"] for gap in gaps)


def test_financial_agent_fetches_eastmoney_and_cross_validates_akshare(monkeypatch):
    ak_result = {
        "success": True,
        "provider": "akshare",
        "data_source": "AKShare",
        "financial_statements": {
            "income_statement": [{"项目": "营业收入", "2025": 96_000_000.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300_000_000.0}],
            "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20_000_000.0}],
        },
    }
    em_result = {
        "success": True,
        "data_source": "东方财富公开财报",
        "financial_statements": {
            "income_statement": [{"项目": "营业收入", "2025": 100_000_000.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300_000_000.0}],
            "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20_000_000.0}],
        },
    }

    monkeypatch.setattr(financial_agent, "fetch_akshare_financial_data", lambda **kwargs: ak_result)
    monkeypatch.setattr(financial_agent.fetch_listed_company_financial, "_run", lambda **kwargs: __import__("json").dumps(em_result, ensure_ascii=False))

    result = financial_agent._fetch_listed_financial_data("测试公司", {"stock_code": "000001", "stock_exchange": "SZ"})

    assert result["data_source"] == "东方财富公开财报"
    assert result["cross_provider_reconciliation"]["passed"] is False
    assert result["provider_fallbacks"][0]["used_for"] == "cross_validation"
