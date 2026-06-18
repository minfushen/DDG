import pandas as pd

from app.agents.sub_agents import financial_report_builder
from app.agents.research_engine.report_assembler import financial_findings


def _financial_frames():
    return {
        "income_statement": pd.DataFrame([
            {"项目": "营业收入", "2023": 1000, "2024": 1200, "2025": 1500},
            {"项目": "营业成本", "2023": 700, "2024": 810, "2025": 990},
            {"项目": "毛利润", "2023": 300, "2024": 390, "2025": 510},
            {"项目": "净利润", "2023": 80, "2024": 96, "2025": 135},
            {"项目": "扣非净利润", "2023": 70, "2024": 88, "2025": 120},
            {"项目": "财务费用", "2023": 10, "2024": 12, "2025": 15},
        ]),
        "balance_sheet": pd.DataFrame([
            {"项目": "流动资产合计", "2023": 600, "2024": 700, "2025": 900},
            {"项目": "货币资金", "2023": 100, "2024": 130, "2025": 180},
            {"项目": "存货", "2023": 100, "2024": 130, "2025": 150},
            {"项目": "应收账款", "2023": 180, "2024": 220, "2025": 260},
            {"项目": "资产总计", "2023": 1800, "2024": 2100, "2025": 2600},
            {"项目": "流动负债合计", "2023": 300, "2024": 350, "2025": 450},
            {"项目": "短期借款", "2023": 100, "2024": 120, "2025": 160},
            {"项目": "应付票据", "2023": 20, "2024": 25, "2025": 30},
            {"项目": "一年内到期的非流动负债", "2023": 10, "2024": 10, "2025": 10},
            {"项目": "负债合计", "2023": 800, "2024": 950, "2025": 1100},
            {"项目": "所有者权益", "2023": 1000, "2024": 1150, "2025": 1500},
        ]),
        "cash_flow": pd.DataFrame([
            {"项目": "经营活动产生的现金流量净额", "2023": 120, "2024": 140, "2025": 180},
        ]),
    }


def test_financial_report_includes_codeact_analysis(monkeypatch):
    captured = {}

    def fake_narrative(**kwargs):
        captured.update(kwargs)
        return {"source": "fallback", "summary": ["测试摘要"], "diagnostics": {}, "quality_warnings": []}

    monkeypatch.setattr(financial_report_builder, "build_financial_narrative", fake_narrative)
    report = financial_report_builder.build_financial_analysis_report("测试公司", _financial_frames())

    codeact = report["codeact_analysis"]
    assert codeact["validation_passed"] is True
    assert round(codeact["metrics"]["2025"]["gross_margin"], 4) == 0.34
    assert round(codeact["metrics"]["2025"]["debt_ratio"], 4) == 0.4231
    assert codeact["metrics"]["2025"]["deducted_net_profit"] == 120
    assert codeact["metrics"]["2025"]["cost"] == 990
    assert codeact["metrics"]["2025"]["short_loan"] == 160
    assert round(codeact["metrics"]["2025"]["cash_to_short_debt"], 4) == 0.9
    assert round(codeact["metrics"]["2025"]["receivable_turnover_days"], 2) == 63.27
    assert round(codeact["metrics"]["2025"]["inventory_turnover_days"], 2) == 55.30
    assert round(codeact["metrics"]["2025"]["ebitda_interest_coverage"], 2) == 10.0
    assert report["key_metrics"]["deducted_net_profit"] == "120.00元"
    assert report["key_metrics"]["cash_to_short_debt"] == "0.90"
    package = report["structured_financial_package"]
    assert package["version"] == "structured_financial_data_layer_v1"
    assert package["unit_base"] == "yuan"
    assert package["display_metrics"]["revenue"]["2025"] == "1500.00元"
    assert package["latest_metrics"]["cash_to_short_debt"]["display_value"] == "0.90"
    assert package["coverage"]["coverage_ratio"] > 0.5
    assert any(flag["code"] == "low_cash_to_short_debt" for flag in package["red_flags"])
    assert report["codeact_evidence"]
    assert report["codeact_evidence_refs"]
    assert report["financial_dashboard"]["charts"]
    assert any(chart["id"] == "revenue_profit_trend" for chart in report["financial_dashboard"]["charts"])
    assert any(chart["id"] == "return_and_interest_coverage" for chart in report["financial_dashboard"]["charts"])
    assert any(item["source_type"] == "codeact_financial_metric" for item in report["codeact_evidence"])
    assert any(item["metadata"].get("metric_key") == "cash_to_short_debt" for item in report["codeact_evidence"])
    assert captured["codeact_analysis"] == codeact


def test_financial_report_codeact_detects_reconciliation_issue(monkeypatch):
    monkeypatch.setattr(
        financial_report_builder,
        "build_financial_narrative",
        lambda **kwargs: {"source": "fallback", "summary": ["测试摘要"], "diagnostics": {}, "quality_warnings": []},
    )
    data = _financial_frames()
    data["balance_sheet"].loc[data["balance_sheet"]["项目"] == "资产总计", "2025"] = 2700

    report = financial_report_builder.build_financial_analysis_report("测试公司", data)

    assert report["codeact_analysis"]["validation_passed"] is False
    assert any(issue["code"] == "balance_equation" for issue in report["codeact_analysis"]["validation_issues"])
    assert any(item["source_type"] == "codeact_financial_validation" for item in report["codeact_evidence"])


def test_financial_findings_use_codeact_evidence_refs(monkeypatch):
    monkeypatch.setattr(
        financial_report_builder,
        "build_financial_narrative",
        lambda **kwargs: {
            "source": "fallback",
            "summary": ["测试摘要"],
            "diagnostics": {
                "diagnostics": [{"title": "盈利质量与成长性风险", "phenomenon": "测试现象", "driver": "测试归因", "risk_level": "中风险"}]
            },
            "quality_warnings": [],
        },
    )
    report = financial_report_builder.build_financial_analysis_report("测试公司", _financial_frames())
    total_report_ev = {
        "id": "ev_report",
        "metadata": {"financial_analysis_report": report},
    }
    findings = financial_findings([total_report_ev] + report["codeact_evidence"])

    assert findings
    assert any(ref.startswith("ev_codeact_") for ref in findings[0]["evidence_refs"])


def test_financial_report_builds_cpa_profit_cash_bridge(monkeypatch):
    monkeypatch.setattr(
        financial_report_builder,
        "build_financial_narrative",
        lambda **kwargs: {
            "source": "fallback",
            "summary": financial_report_builder.build_financial_narrative.__name__ if False else [
                kwargs["profit_cash_bridge"]["conclusion"],
                kwargs["profit_cash_bridge"]["deducted_profit_judgement"],
            ],
            "diagnostics": {"profit_cash_bridge": kwargs["profit_cash_bridge"]},
            "quality_warnings": [],
        },
    )
    data = {
        "income_statement": pd.DataFrame([
            {"项目": "营业收入", "2023": 1000, "2024": 1200, "2025": 1400},
            {"项目": "营业成本", "2023": 800, "2024": 990, "2025": 1200},
            {"项目": "净利润", "2023": 90, "2024": 40, "2025": -20},
            {"项目": "扣非净利润", "2023": -10, "2024": -40, "2025": -60},
            {"项目": "财务费用", "2023": 10, "2024": 12, "2025": 15},
            {"项目": "投资收益", "2023": 30, "2024": 20, "2025": -5},
            {"项目": "资产减值损失", "2023": -5, "2024": -8, "2025": -12},
        ]),
        "balance_sheet": pd.DataFrame([
            {"项目": "流动资产合计", "2023": 600, "2024": 700, "2025": 780},
            {"项目": "货币资金", "2023": 100, "2024": 110, "2025": 120},
            {"项目": "存货", "2023": 180, "2024": 220, "2025": 260},
            {"项目": "应收账款", "2023": 200, "2024": 250, "2025": 330},
            {"项目": "固定资产", "2023": 900, "2024": 1100, "2025": 1300},
            {"项目": "在建工程", "2023": 200, "2024": 260, "2025": 310},
            {"项目": "资产总计", "2023": 2000, "2024": 2400, "2025": 2800},
            {"项目": "流动负债合计", "2023": 400, "2024": 520, "2025": 650},
            {"项目": "短期借款", "2023": 120, "2024": 200, "2025": 260},
            {"项目": "负债合计", "2023": 900, "2024": 1100, "2025": 1300},
            {"项目": "所有者权益", "2023": 1100, "2024": 1300, "2025": 1500},
        ]),
        "cash_flow": pd.DataFrame([
            {"项目": "经营活动产生的现金流量净额", "2023": 110, "2024": 100, "2025": 80},
            {"项目": "投资活动产生的现金流量净额", "2023": -220, "2024": -260, "2025": -300},
            {"项目": "筹资活动产生的现金流量净额", "2023": 150, "2024": 180, "2025": 160},
            {"项目": "折旧摊销", "2023": 60, "2024": 80, "2025": 95},
        ]),
    }

    report = financial_report_builder.build_financial_analysis_report("测试制造公司", data)
    bridge = report["profit_cash_bridge"]
    joined = "\n".join(report["narrative_summary"] + [text for section in report["sections"] for sub in section["subsections"] for text in sub.get("analysis", [])])

    assert "利润承压但经营现金流仍为正" in bridge["conclusion"]
    assert "扣非净利润近三年均为负" in bridge["deducted_profit_judgement"]
    assert "折旧摊销" in bridge["bridge_explanation"]
    assert "重资产" in bridge["heavy_asset_judgement"]
    assert "经营现金流" in joined
    assert "扣非净利润近三年均为负" in joined
    assert "鱼子" not in joined
    assert "最新原来" not in joined
