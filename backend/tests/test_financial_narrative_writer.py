from app.agents.sub_agents.financial_narrative_writer import build_financial_narrative


def test_build_financial_narrative_uses_structured_package():
    package = {
        "latest_metrics": {
            "revenue": {"label": "营业收入", "raw_value": 1_000_000_000.0, "display_value": "10.00亿元", "trend": "持续增长"},
            "net_profit": {"label": "净利润", "raw_value": 100_000_000.0, "display_value": "1.00亿元", "trend": "持续增长"},
        },
        "display_metrics": {
            "revenue": {"2023": "8.00亿元", "2024": "9.00亿元", "2025": "10.00亿元"},
            "net_profit": {"2023": "0.80亿元", "2024": "0.90亿元", "2025": "1.00亿元"},
        },
        "trends": {"revenue": "持续增长", "net_profit": "持续增长"},
        "red_flags": [
            {"code": "high_debt_ratio", "label": "资产负债率高", "severity": "high", "detail": "2025年资产负债率为75.00%"},
        ],
        "data_boundary": ["AKShare/东方财富结构化字段交叉校验未发现超阈值差异。"],
    }

    result = build_financial_narrative(
        enterprise_name="测试公司",
        years=["2023", "2024", "2025"],
        key_metrics={"revenue": "旧值", "net_profit": "旧值"},
        risk_summary=["已有风险"],
        recommendation="建议进一步复核",
        risk_rating="medium",
        risk_score=70,
        structured_financial_package=package,
    )

    summary = "\n".join(result.get("summary") or [])
    assert "10.00亿元" in summary
    diagnostics = result.get("diagnostics") or {}
    diagnostics_text = str(diagnostics)
    assert "盈利质量与成长性风险" in diagnostics_text
    assert "资产真实性与营运效率风险" in diagnostics_text
    assert "资本结构与偿债能力风险" in diagnostics_text
