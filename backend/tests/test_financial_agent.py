import pytest
import pandas as pd

from app.agents.sub_agents import financial_agent


def test_select_rebecca_data_prefers_structured():
    listed_data = {
        "success": True,
        "data_source": "东方财富公开财报",
        "financial_statements": {
            "income_statement": [{"项目": "营业收入", "2025": 100.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300.0}],
            # cash_flow 缺失，由 pipeline 补齐
        },
    }
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    pipeline_result = PipelineResult(
        success=True,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 110.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 20.0},
            ]),
        ),
    )

    rebecca_data, data_source, fallbacks = financial_agent._select_rebecca_data(listed_data, pipeline_result)

    assert data_source == "东方财富公开财报"
    assert rebecca_data["income_statement"].iloc[0]["2025"] == 100.0
    assert rebecca_data["balance_sheet"] is not None
    assert rebecca_data["cash_flow"] is not None
    assert any(f["provider"] == "cninfo_pdf_pipeline" for f in fallbacks)


def test_select_rebecca_data_pipeline_fallback():
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    pipeline_result = PipelineResult(
        success=True,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 110.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 310.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 25.0},
            ]),
        ),
    )

    rebecca_data, data_source, fallbacks = financial_agent._select_rebecca_data(None, pipeline_result)

    assert data_source == "巨潮资讯网年报PDF解析"
    assert rebecca_data["income_statement"] is not None
    assert rebecca_data["balance_sheet"] is not None
    assert rebecca_data["cash_flow"] is not None


def test_select_rebecca_data_empty():
    rebecca_data, data_source, fallbacks = financial_agent._select_rebecca_data(None, None)
    assert rebecca_data == {}
    assert data_source == ""
    assert fallbacks == []


def test_select_rebecca_data_prefers_pdf_when_high_quality():
    """当 PDF pipeline 质量足够高时，优先使用 PDF 数据。"""
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    listed_data = {
        "success": True,
        "data_source": "东方财富公开财报",
        "financial_statements": {
            "income_statement": [{"项目": "营业收入", "2025": 100.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300.0}],
            "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20.0}],
        },
    }
    pipeline_result = PipelineResult(
        success=True,
        auto_judgment_rate=0.9,
        main_table_coverage="3/3",
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 110.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 310.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 25.0},
            ]),
        ),
    )

    rebecca_data, data_source, fallbacks = financial_agent._select_rebecca_data(listed_data, pipeline_result)

    assert data_source == "巨潮资讯网年报PDF解析"
    # PDF 数据优先
    assert rebecca_data["income_statement"].iloc[0]["2025"] == 110.0
    assert rebecca_data["balance_sheet"].iloc[0]["2025"] == 310.0
    assert rebecca_data["cash_flow"].iloc[0]["2025"] == 25.0
    assert not fallbacks  # 三张表都完整，无需补缺


def test_select_rebecca_data_structured_fallback_when_pdf_low_quality():
    """当 PDF pipeline 质量不足时，回退到结构化数据。"""
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    listed_data = {
        "success": True,
        "data_source": "东方财富公开财报",
        "financial_statements": {
            "income_statement": [{"项目": "营业收入", "2025": 100.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300.0}],
            "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20.0}],
        },
    }
    pipeline_result = PipelineResult(
        success=True,
        auto_judgment_rate=0.5,  # 低于 0.85 阈值
        main_table_coverage="3/3",
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 110.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 310.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 25.0},
            ]),
        ),
    )

    rebecca_data, data_source, fallbacks = financial_agent._select_rebecca_data(listed_data, pipeline_result)

    assert data_source == "东方财富公开财报"
    assert rebecca_data["income_statement"].iloc[0]["2025"] == 100.0
    assert rebecca_data["balance_sheet"].iloc[0]["2025"] == 300.0


def test_select_rebecca_data_pdf_with_structured_fallback():
    """PDF 优先但缺少某张表时，用结构化接口补齐。"""
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    listed_data = {
        "success": True,
        "data_source": "东方财富公开财报",
        "financial_statements": {
            "income_statement": [{"项目": "营业收入", "2025": 100.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300.0}],
            "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20.0}],
        },
    }
    pipeline_result = PipelineResult(
        success=True,
        auto_judgment_rate=0.9,
        main_table_coverage="3/3",
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 110.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 310.0},
            ]),
            # cash_flow 缺失
        ),
    )

    rebecca_data, data_source, fallbacks = financial_agent._select_rebecca_data(listed_data, pipeline_result)

    assert data_source == "巨潮资讯网年报PDF解析"
    assert rebecca_data["income_statement"].iloc[0]["2025"] == 110.0
    assert rebecca_data["balance_sheet"].iloc[0]["2025"] == 310.0
    assert rebecca_data["cash_flow"].iloc[0]["2025"] == 20.0
    assert any(f["used_for"] == "fallback_cash_flow" for f in fallbacks)


def test_should_prefer_pdf_pipeline():
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    assert financial_agent._should_prefer_pdf_pipeline(None) is False
    assert financial_agent._should_prefer_pdf_pipeline(PipelineResult(success=False)) is False
    assert financial_agent._should_prefer_pdf_pipeline(
        PipelineResult(success=True, auto_judgment_rate=0.9, main_table_coverage="3/3")
    ) is True
    assert financial_agent._should_prefer_pdf_pipeline(
        PipelineResult(success=True, auto_judgment_rate=0.84, main_table_coverage="3/3")
    ) is False
    assert financial_agent._should_prefer_pdf_pipeline(
        PipelineResult(success=True, auto_judgment_rate=0.9, main_table_coverage="2/3")
    ) is False


def test_pipeline_statements_to_records():
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData
    pipeline_result = PipelineResult(
        success=True,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 100.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 300.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 20.0},
            ]),
        ),
    )

    records = financial_agent._pipeline_statements_to_records(pipeline_result)

    assert records["income_statement"][0]["项目"] == "营业收入"
    assert records["income_statement"][0]["2025"] == 100.0
    assert records["balance_sheet"][0]["项目"] == "资产总计"
    assert records["cash_flow"][0]["项目"] == "经营活动产生的现金流量净额"


def test_supplement_years_from_older_pdfs():
    """用 older 年报 PDF 补充缺失年份。"""
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData

    base_result = PipelineResult(
        success=True,
        report_year=2025,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 100.0, "2024": 90.0},
            ]),
        ),
    )
    older_result = PipelineResult(
        success=True,
        report_year=2024,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2024": 88.0, "2023": 80.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2024": 300.0, "2023": 270.0},
            ]),
        ),
    )
    pdf_extraction_results = [
        {"pipeline_result": base_result},
        {"pipeline_result": older_result},
    ]

    base_rebecca_data = financial_agent._pipeline_result_to_rebecca_data(base_result)
    merged = financial_agent._supplement_years_from_older_pdfs(base_rebecca_data, pdf_extraction_results)

    income = merged["income_statement"]
    assert set(income.columns) >= {"项目", "2025", "2024", "2023"}
    revenue_row = income[income["项目"] == "营业收入"].iloc[0]
    assert revenue_row["2025"] == 100.0
    assert revenue_row["2024"] == 90.0  # 最新年报优先
    assert revenue_row["2023"] == 80.0  # 从 older PDF 补充

    balance = merged["balance_sheet"]
    assert set(balance.columns) >= {"项目", "2024", "2023"}
    assets_row = balance[balance["项目"] == "资产总计"].iloc[0]
    assert assets_row["2024"] == 300.0
    assert assets_row["2023"] == 270.0


@pytest.mark.asyncio
async def test_run_financial_agent_with_uploaded_data():
    result = await financial_agent.run_financial_agent_with_uploaded_data(
        "测试公司",
        {
            "income_statement": [{"项目": "营业收入", "2025": 100.0}, {"项目": "净利润", "2025": 10.0}],
            "balance_sheet": [{"项目": "资产总计", "2025": 300.0}, {"项目": "负债合计", "2025": 120.0}],
            "cash_flow": [{"项目": "经营活动产生的现金流量净额", "2025": 20.0}],
        },
    )

    assert result["success"] is True
    assert result.get("financial_analysis_report") is not None
    assert any(item.get("label") == "营业收入" for item in result.get("evidence", []))


@pytest.mark.asyncio
async def test_run_financial_agent_with_uploaded_data_empty():
    result = await financial_agent.run_financial_agent_with_uploaded_data("测试公司", {})
    assert result["success"] is False
    assert result["fallback_to_upload"] is True
