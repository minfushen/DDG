from app.agents.sub_agents.financial_dashboard_builder import build_financial_dashboard


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
