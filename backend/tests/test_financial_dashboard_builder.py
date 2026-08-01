from app.agents.sub_agents.financial_dashboard_builder import build_dupont_mermaid, build_financial_dashboard


def test_financial_dashboard_builds_nine_charts_with_refs():
    years = ["2023", "2024", "2025"]
    metrics = {
        "revenue": {"2023": 1000, "2024": 1200, "2025": 1500},
        "net_profit": {"2023": 80, "2024": 96, "2025": 135},
        "gross_margin": {"2023": 0.3, "2024": 0.325, "2025": 0.34},
        "net_margin": {"2023": 0.08, "2024": 0.08, "2025": 0.09},
        "debt_ratio": {"2023": 0.44, "2024": 0.45, "2025": 0.42},
        "current_ratio": {"2023": 2.0, "2024": 2.0, "2025": 2.0},
        "quick_ratio": {"2023": 1.67, "2024": 1.63, "2025": 1.67},
        "operating_cf": {"2023": 120, "2024": 140, "2025": 180},
        "investing_cf": {"2023": -60, "2024": -80, "2025": -120},
        "financing_cf": {"2023": 20, "2024": 30, "2025": 10},
        "cash": {"2023": 100, "2024": 130, "2025": 180},
        "receivable": {"2023": 180, "2024": 220, "2025": 260},
        "inventory": {"2023": 100, "2024": 130, "2025": 150},
        "fixed_assets": {"2023": 500, "2024": 550, "2025": 700},
        "construction": {"2023": 50, "2024": 70, "2025": 80},
        "short_loan": {"2023": 100, "2024": 120, "2025": 160},
        "cash_to_short_debt": {"2023": 0.8, "2024": 0.9, "2025": 1.1},
        "inventory_turnover_days": {"2023": 52.1, "2024": 58.6, "2025": 55.3},
        "receivable_turnover_days": {"2023": 65.7, "2024": 66.9, "2025": 63.3},
        "ebitda_interest_coverage": {"2023": 9.0, "2024": 9.0, "2025": 10.0},
        "notes_payable": {"2023": 30, "2024": 40, "2025": 55},
        "payable": {"2023": 90, "2024": 100, "2025": 130},
        "roe": {"2023": 0.08, "2024": 0.083, "2025": 0.09},
        "roa": {"2023": 0.044, "2024": 0.046, "2025": 0.052},
    }

    dashboard = build_financial_dashboard("测试公司", years, metrics, evidence_refs=["ev_1", "ev_2"])

    assert dashboard["title"] == "测试公司近三年财务数据分析"
    assert len(dashboard["charts"]) == 9
    assert all(chart["diagnosis"] for chart in dashboard["charts"])
    assert all(chart["evidence_refs"] == ["ev_1", "ev_2"] for chart in dashboard["charts"])
    leverage = next(chart for chart in dashboard["charts"] if chart["id"] == "leverage_trend")
    liquidity = next(chart for chart in dashboard["charts"] if chart["id"] == "liquidity_trend")
    working_capital = next(chart for chart in dashboard["charts"] if chart["id"] == "working_capital")
    return_coverage = next(chart for chart in dashboard["charts"] if chart["id"] == "return_and_interest_coverage")
    assert leverage["threshold_lines"][0]["value"] == 0.7
    assert {line["value"] for line in liquidity["threshold_lines"]} == {1.0, 1.5}
    assert any(series["name"] == "现金短债比" for series in liquidity["series"])
    assert any(series["name"] == "应收账款周转天数" for series in working_capital["series"])
    assert any(series["name"] == "EBITDA利息保障倍数" for series in return_coverage["series"])


def test_financial_dashboard_skips_all_empty_charts():
    dashboard = build_financial_dashboard(
        "测试公司",
        ["2024", "2025"],
        {"revenue": {"2024": None, "2025": None}},
        evidence_refs=[],
    )

    assert dashboard["charts"] == []


def _mock_dupont_analysis():
    return {
        "success": True,
        "factors": {
            "roe": {"2023": 0.015},
            "net_margin": {"2023": 3 / 140},
            "asset_turnover": {"2023": 140 / 400},
            "equity_multiplier": {"2023": 2.0},
        },
        "decomposition": [
            {
                "year": "2023",
                "roe": 0.015,
                "net_margin": 3 / 140,
                "asset_turnover": 140 / 400,
                "equity_multiplier": 2.0,
                "revenue": 14_000_000_000.0,
                "net_profit": 300_000_000.0,
                "total_assets": 40_000_000_000.0,
                "equity": 20_000_000_000.0,
                "driver": "",
            }
        ],
        "red_flags": ["净利率仅 2.1%，主业盈利能力偏弱。"],
        "summary": "杜邦分析覆盖 2023 年共 1 年。",
    }


def test_build_dupont_mermaid_generates_flowchart():
    spec = build_dupont_mermaid("测试公司", _mock_dupont_analysis())

    assert spec is not None
    assert spec["title"] == "测试公司杜邦分解（2023年）"
    assert spec["mermaid"].startswith("graph TD")
    assert "ROE 净资产收益率<br/>1.50%" in spec["mermaid"]
    assert "销售净利率<br/>2.14%" in spec["mermaid"]
    assert "总资产周转率<br/>0.35" in spec["mermaid"]
    assert "权益乘数<br/>2.00" in spec["mermaid"]
    assert "净利润<br/>3.00亿元" in spec["mermaid"]
    assert "营业收入<br/>140.00亿元" in spec["mermaid"]
    assert "总资产<br/>400.00亿元" in spec["mermaid"]
    assert "所有者权益<br/>200.00亿元" in spec["mermaid"]
    assert "classDef roe" in spec["mermaid"]
    assert spec["red_flags"]
    assert spec["summary"]


def test_build_dupont_mermaid_returns_none_without_data():
    assert build_dupont_mermaid("测试公司", None) is None
    assert build_dupont_mermaid("测试公司", {"success": False}) is None
    assert build_dupont_mermaid("测试公司", {"success": True, "decomposition": []}) is None


def test_build_dupont_mermaid_handles_missing_values():
    spec = build_dupont_mermaid(
        "测试公司",
        {
            "success": True,
            "decomposition": [
                {
                    "year": "2024",
                    "roe": None,
                    "net_margin": None,
                    "asset_turnover": None,
                    "equity_multiplier": None,
                    "revenue": None,
                    "net_profit": None,
                    "total_assets": None,
                    "equity": None,
                }
            ],
            "red_flags": [],
            "summary": "",
        },
    )

    assert spec is not None
    assert "数据缺失" in spec["mermaid"]
