from app.codeact import list_codeact_tools, run_codeact_tool


def _minimal_bad_report():
    return {
        "enterprise_name": "分析一下士兰微这个上市公司",
        "report_chapters": [{"id": "overview", "summary": ["报告专项待补充"]}],
        "evidence": [],
    }


def _financial_data():
    return {
        "income_statement": [
            {"项目": "营业收入", "2023": 1000, "2024": 1200, "2025": 1500},
            {"项目": "营业成本", "2023": 700, "2024": 810, "2025": 990},
            {"项目": "毛利润", "2023": 300, "2024": 390, "2025": 510},
            {"项目": "净利润", "2023": 80, "2024": 96, "2025": 135},
        ],
        "balance_sheet": [
            {"项目": "流动资产合计", "2023": 600, "2024": 700, "2025": 900},
            {"项目": "存货", "2023": 100, "2024": 130, "2025": 150},
            {"项目": "应收账款", "2023": 180, "2024": 220, "2025": 260},
            {"项目": "资产总计", "2023": 1800, "2024": 2100, "2025": 2600},
            {"项目": "流动负债合计", "2023": 300, "2024": 350, "2025": 450},
            {"项目": "负债合计", "2023": 800, "2024": 950, "2025": 1100},
            {"项目": "所有者权益", "2023": 1000, "2024": 1150, "2025": 1500},
        ],
        "cash_flow": [
            {"项目": "经营活动产生的现金流量净额", "2023": 120, "2024": 140, "2025": 180},
            {"项目": "投资活动产生的现金流量净额", "2023": -80, "2024": -100, "2025": -120},
            {"项目": "筹资活动产生的现金流量净额", "2023": 20, "2024": 30, "2025": 50},
        ],
    }


def test_codeact_lists_registered_tools():
    tools = list_codeact_tools()
    names = {tool["name"] for tool in tools}
    assert "evaluate_report_quality" in names
    assert "calculate_financial_ratios" in names
    assert "validate_financial_statements" in names
    assert "validate_t1_data_package" in names


def test_codeact_unknown_tool_returns_structured_failure():
    result = run_codeact_tool("missing_tool", {})
    assert result["success"] is False
    assert result["tool_name"] == "missing_tool"
    assert result["elapsed_ms"] >= 0
    assert "Unknown CodeAct tool" in result["error"]


def test_codeact_report_quality_tool_returns_score_and_issues():
    result = run_codeact_tool("evaluate_report_quality", {"report": _minimal_bad_report()})
    assert result["success"] is True
    assert result["tool_name"] == "evaluate_report_quality"
    assert result["display_name"] == "报告质量评测"
    assert result["source_type"] == "codeact_evaluation"
    assert result["elapsed_ms"] >= 0
    quality = result["result"]
    assert quality["passed"] is False
    assert isinstance(quality["overall_score"], int)
    assert any(issue["severity"] == "P0" for issue in quality["issues"])


def test_codeact_report_quality_requires_report_object():
    result = run_codeact_tool("evaluate_report_quality", {"sample": {}})
    assert result["success"] is False
    assert "payload.report" in result["error"]


def test_codeact_calculates_financial_ratios():
    result = run_codeact_tool("calculate_financial_ratios", {"financial_data": _financial_data()})
    assert result["success"] is True
    assert result["source_type"] == "codeact_financial_metric"
    metrics = result["result"]["metrics"]
    assert result["result"]["years"] == ["2023", "2024", "2025"]
    assert round(metrics["2025"]["gross_margin"], 4) == 0.34
    assert round(metrics["2025"]["debt_ratio"], 4) == 0.4231
    assert round(metrics["2025"]["current_ratio"], 4) == 2.0


def test_codeact_validates_financial_statement_reconciliation():
    data = _financial_data()
    result = run_codeact_tool("validate_financial_statements", {"financial_data": data})
    assert result["success"] is True
    assert result["result"]["passed"] is True

    broken = _financial_data()
    broken["balance_sheet"][3]["2025"] = 2700
    broken_result = run_codeact_tool("validate_financial_statements", {"financial_data": broken})
    assert broken_result["success"] is True
    assert broken_result["result"]["passed"] is False
    assert any(issue["code"] == "balance_equation" for issue in broken_result["result"]["issues"])


def test_codeact_validates_t1_data_package():
    package = {
        "package_id": "pkg_20260614_0001",
        "subject_name": "欣旺达电子股份有限公司",
        "subject_keys": {"stock_code": "300207", "aliases": ["欣旺达"]},
        "data_domain": "financial",
        "as_of_date": "2026-06-14",
        "source_name": "客户授权数据源",
        "source_type": "customer_authorized_data_feed",
        "trust_level": "high",
        "license_scope": "仅限本客户内网尽调用途",
        "records": [{"name": "营业收入", "value": 100}],
        "raw_refs": ["raw/pkg_20260614_0001.json"],
        "checksum": "abc123",
    }
    result = run_codeact_tool("validate_t1_data_package", {"package": package, "max_age_days": 30})
    assert result["success"] is True
    assert result["source_type"] == "codeact_t1_package_validation"
    assert result["result"]["passed"] is True
    assert result["result"]["metrics"]["record_count"] == 1

    bad_result = run_codeact_tool("validate_t1_data_package", {"package": {"data_domain": "unknown", "records": []}})
    assert bad_result["success"] is True
    assert bad_result["result"]["passed"] is False
    assert any(issue["severity"] == "P0" for issue in bad_result["result"]["issues"])
