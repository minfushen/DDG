"""授信五看与审批意见生成器离线测试（确定性，不依赖 LLM）。"""

from app.agents.sub_agents.five_see_analyzer import build_five_see_analysis
from app.agents.sub_agents.credit_approval_opinion import build_credit_approval_opinion


def test_five_see_dimensions_present():
    r = build_five_see_analysis(
        "测试企业",
        industry_context={"industry_name": "半导体", "diagnosis_summary": "行业周期下行"},
        business_segments=[{"产品": "LED芯片", "占比": "60%"}],
        financial_metrics={"operating_cash_flow": 2e9, "revenue": 14e9},
    )
    assert r["success"] is True
    dims = r["five_see"]
    assert set(dims.keys()) == {"see_industry", "see_customer", "see_product", "see_repayment", "see_guarantee"}
    assert "半导体" in dims["see_industry"]["facts"][0]
    assert dims["see_product"]["facts"]  # 主营构成已填入
    assert r["summary"]


def test_approval_defer_on_high_flow_flag():
    flow = {
        "status": "mismatch",
        "red_flags": [{"type": "related_party_large_flow", "severity": "high", "detail": "大额关联方资金往来，疑似资金占用"}],
        "check_items": [],
    }
    r = build_credit_approval_opinion("测试企业", flow_reconciliation=flow)
    assert r["decision"] == "暂缓准入"
    assert any("关联方" in reason for reason in r["reasons"])


def test_approval_conditional_on_data_gap():
    # 无任何数据：决策应为建议准入，但因数据缺口降级为有条件初步准入。
    r = build_credit_approval_opinion("测试企业")
    assert r["decision"] == "有条件初步准入"
    assert r["data_gaps"]  # 应提示未提供流水等缺口
    assert r["conditions"]  # 授信条件非空
    assert r["manual_review"]  # 人工复核清单非空


def test_approval_cautious_on_high_debt():
    r = build_credit_approval_opinion(
        "测试企业",
        financial_metrics={"debt_ratio": 0.78, "operating_cash_flow": 1e9, "roe": 0.05},
    )
    assert r["decision"] == "谨慎准入"
    assert any("资产负债率" in c for c in r["reasons"])
