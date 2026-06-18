from app.agents.sub_agents import financial_narrative_writer as writer


def test_corrupted_llm_financial_diagnostics_are_rejected():
    raw_response = """
    {
      "overall_evaluation": {"risk_level": "中风险", "score": 75, "conclusion": "指标存在欠质量"},
      "diagnostics": [
        {"title": "盈利质量与成长性风险", "phenomenon": "现象与增益：主要血能力不足", "driver": "需复核", "risk_level": "中风险", "verification_action": ["目的要点"]},
        {"title": "资产真实性与营运效率风险", "phenomenon": "现象与极限：经营杠杆/利息异常", "driver": "应收昔较高", "risk_level": "中风险", "verification_action": ["获取账龄"]},
        {"title": "资本结构与偿债能力风险", "phenomenon": "流动负债为1.48", "driver": "有息保安明细待补充", "risk_level": "中风险", "verification_action": ["设有及或有库存清单"]}
      ],
      "data_boundary": "已解析的财务报表数据",
      "manual_review_items": ["审计报告"]
    }
    """
    key_metrics = {
        "enterprise_name": "三安光电",
        "latest_year": "2024",
        "revenue_growth": "14.60%",
        "revenue_cagr": "10.40%",
        "gross_margin": "11.90%",
        "net_margin": "1.57%",
        "receivable": "35.86亿元",
        "receivable_to_revenue": "22.27%",
        "receivable_growth": "1.36%",
        "debt_ratio_change": "3.94pct",
        "current_ratio": "1.62",
        "current_ratio_change": "-0.47",
        "operating_cf_to_net_profit": "10.34",
    }
    series = {
        "revenue": {"2022": "132.22亿元", "2023": "140.53亿元", "2024": "161.06亿元"},
        "net_profit": {"2022": "6.85亿元", "2023": "3.67亿元", "2024": "2.53亿元"},
        "debt_ratio": {"2022": "35.01%", "2023": "33.59%", "2024": "37.53%"},
        "operating_cash_flow": {"2022": "数据不可用", "2023": "39.77亿元", "2024": "26.17亿元"},
    }
    fallback_diagnostics = writer._fallback_diagnostics(
        "三安光电",
        key_metrics,
        [],
        "建议审慎准入",
        "medium",
        75,
        "已解析的财务报表数据",
        series,
    )
    fallback = writer._render_credit_style_summary(
        "三安光电",
        key_metrics,
        "medium",
        75,
        "建议审慎准入",
        "已解析的财务报表数据",
        series,
        fallback_diagnostics,
    )

    summary, diagnostics, warnings, _ = writer._parse_candidate(
        raw_response,
        "三安光电",
        "medium",
        "建议审慎准入",
        fallback,
        fallback_diagnostics,
        key_metrics,
        ["2022", "2023", "2024"],
        "已解析的财务报表数据",
        series,
        75,
    )

    assert warnings
    assert any("禁用表达" in warning for warning in warnings)
    assert "3.1 收入与利润分析" in "\n".join(summary)
    assert "主要血" not in "\n".join(summary)
    assert "现象与增益" in str(diagnostics)


def test_fallback_financial_summary_uses_credit_report_sections():
    summary = writer._fallback_summary(
        "三安光电",
        {
            "latest_year": "2024",
            "revenue_growth": "14.60%",
            "revenue_cagr": "10.40%",
            "gross_margin": "11.90%",
            "net_margin": "1.57%",
            "receivable": "35.86亿元",
            "receivable_to_revenue": "22.27%",
            "receivable_growth": "1.36%",
            "debt_ratio_change": "3.94pct",
            "current_ratio": "1.62",
            "current_ratio_change": "-0.47",
            "operating_cf_to_net_profit": "10.34",
        },
        [],
        "建议审慎准入",
        "medium",
        75,
        "已解析的财务报表数据",
        {
            "revenue": {"2022": "132.22亿元", "2023": "140.53亿元", "2024": "161.06亿元"},
            "net_profit": {"2022": "6.85亿元", "2023": "3.67亿元", "2024": "2.53亿元"},
            "debt_ratio": {"2022": "35.01%", "2023": "33.59%", "2024": "37.53%"},
            "operating_cash_flow": {"2023": "39.77亿元", "2024": "26.17亿元"},
        },
    )
    text = "\n".join(summary)
    assert "3.1 收入与利润分析" in text
    assert "3.2 资产负债分析" in text
    assert "3.3 盈利质量与营运效率" in text
    assert "3.4 偿债能力与财务信号异常" in text
    assert "近三年营业收入分别为2022年132.22亿元、2023年140.53亿元、2024年161.06亿元" in text


def test_ocr_corrupted_metric_labels_are_rejected():
    """OCR errors like '鱼子' for ROE must be caught by the quality gate."""
    raw_response = """
    {
      "overall_evaluation": {"risk_level": "高风险", "score": 55, "conclusion": "2025年销售净利率为-1.86%，ROA为-0.57%，ROE为-0.95%，盈利指标全面转负。"},
      "diagnostics": [
        {"title": "盈利质量与成长性风险", "phenomenon": "指标 2023年 2024年 2025年 趋势 EBITDA(亿元) 6.42 4.36 -1.53 持续下降 销售净利率(%) 2.61 1.59 -1.86 持续下降 ROA(%) 0.64 0.43 -0.57 持续下降 鱼子（％） 0.96 0.69 -0.95 持续下降", "driver": "若ROE显着于ROA，需判断是否主要由财务杠杆驱动。EBITDA和鱼子什么玩意儿", "risk_level": "高风险", "verification_action": ["复核三大表"]},
        {"title": "资产真实性与营运效率风险", "phenomenon": "经营现金流走弱", "driver": "利润含金量下降", "risk_level": "中风险", "verification_action": ["获取银行流水"]},
        {"title": "资本结构与偿债能力风险", "phenomenon": "资产负债率上升", "driver": "杠杆扩大", "risk_level": "高风险", "verification_action": ["核实有息负债"]}
      ],
      "data_boundary": "已解析的财务报表数据",
      "manual_review_items": ["审计报告"]
    }
    """
    key_metrics = {
        "enterprise_name": "测试企业",
        "latest_year": "2025",
        "net_margin": "-1.86%",
        "roa": "-0.57%",
        "roe": "-0.95%",
    }
    fallback_diagnostics = writer._fallback_diagnostics(
        "测试企业",
        key_metrics,
        [],
        "建议暂缓授信",
        "high",
        55,
        "已解析的财务报表数据",
        {},
    )
    fallback = writer._render_credit_style_summary(
        "测试企业",
        key_metrics,
        "high",
        55,
        "建议暂缓授信",
        "已解析的财务报表数据",
        {},
        fallback_diagnostics,
    )

    summary, diagnostics, warnings, _ = writer._parse_candidate(
        raw_response,
        "测试企业",
        "high",
        "建议暂缓授信",
        fallback,
        fallback_diagnostics,
        key_metrics,
        ["2023", "2024", "2025"],
        "已解析的财务报表数据",
        {},
        55,
    )

    assert warnings
    assert any("鱼子" in warning for warning in warnings)
    assert any("显着" in warning or "显著" in warning for warning in warnings)
    assert any("什么玩意儿" in warning for warning in warnings)
    assert "鱼子" not in "\n".join(summary)
    assert "什么玩意儿" not in "\n".join(summary)


def test_malformed_growth_phrases_are_rejected():
    """LLM-generated section titles and growth phrases must use standard terms."""
    raw_response = """
    {
      "overall_evaluation": {"risk_level": "低风险", "score": 85, "conclusion": "药明康德财务表现呈低风险。"},
      "diagnostics": [
        {"title": "盈利质量与成长性风险", "phenomenon": "近三年营业收入持续增长", "driver": "收入扩张带动利润", "risk_level": "低风险", "verification_action": ["复核主营构成"]},
        {"title": "资产真实性与营运效率风险", "phenomenon": "3.2 资产证券分析药明康德近三年总资产呈增长趋势，2025年总资产为103,120,968,579.11元，近期一期同期波动为28.38%。资产结构方面，2025年应收账款为7,262,654,076.99元，存货为8,993,244,894.24元，需结合账龄、跌价准备和项目结算周期判断资产质量。营业收入最新原来为15.84%，总资产最新原来为28.38%，可用于判断资产拓展是否有效转化为经营规模。", "driver": "资产扩张快于收入增长", "risk_level": "中风险", "verification_action": ["核实资产质量"]}
      ],
      "data_boundary": "已解析的财务报表数据",
      "manual_review_items": ["审计报告"]
    }
    """
    key_metrics = {
        "enterprise_name": "药明康德",
        "latest_year": "2025",
        "revenue_growth": "15.84%",
    }
    fallback_diagnostics = writer._fallback_diagnostics(
        "药明康德",
        key_metrics,
        [],
        "建议审慎准入",
        "low",
        85,
        "已解析的财务报表数据",
        {},
    )
    fallback = writer._render_credit_style_summary(
        "药明康德",
        key_metrics,
        "low",
        85,
        "建议审慎准入",
        "已解析的财务报表数据",
        {},
        fallback_diagnostics,
    )

    summary, diagnostics, warnings, _ = writer._parse_candidate(
        raw_response,
        "药明康德",
        "low",
        "建议审慎准入",
        fallback,
        fallback_diagnostics,
        key_metrics,
        ["2023", "2024", "2025"],
        "已解析的财务报表数据",
        {},
        85,
    )

    assert warnings
    assert any("资产证券分析" in warning for warning in warnings)
    assert any("最新原来" in warning for warning in warnings)
    assert any("同期波动" in warning for warning in warnings)
    assert any("近期一期" in warning for warning in warnings)
    assert any("资产拓展" in warning for warning in warnings)
    assert "资产证券分析" not in "\n".join(summary)
    assert "最新原来" not in "\n".join(summary)
