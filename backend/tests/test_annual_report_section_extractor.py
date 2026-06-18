from app.agents.tools.annual_report_section_extractor import (
    extract_all_sections,
    extract_main_business_tables,
    extract_section,
    sections_to_evidence,
)


def sample_annual_report_text():
    return (
        "第三节 经营情况讨论与分析\n"
        "2025年，公司实现营业收入100亿元，同比增长12%。"
        "公司主营业务为半导体分立器件和集成电路。\n"
        "第四节 主营业务分析\n"
        "主营业务分产品情况\n"
        "产品A 营业收入 50亿元 占比 50%\n"
        "第五节 审计意见\n"
        "注册会计师出具标准无保留意见。\n"
        "第六节 资产减值\n"
        "本年度计提资产减值损失1亿元。\n"
        "第七节 重大风险提示\n"
        "市场竞争加剧、原材料价格波动。"
    )


def test_extract_section_matches_business_review():
    text = sample_annual_report_text()
    section = extract_section(text, [r"经营情况讨论与分析"], context_chars=500)
    assert section
    assert "营业收入" in section
    assert "主营业务" in section


def test_extract_all_sections_completeness():
    result = {"text": sample_annual_report_text(), "tables": [], "metadata": {}, "error": "", "success": True}
    sections = extract_all_sections(result)
    assert sections["business_review"]
    assert sections["audit_opinion"]
    assert sections["asset_impairment"]
    assert sections["major_risk_warnings"]


def test_extract_main_business_tables():
    tables = [
        [["产品", "营业收入", "占比", "毛利率"], ["产品A", "50亿元", "50%", "30%"]],
        [[" irrelevant ", "col"], ["a", "b"]],
    ]
    rows = extract_main_business_tables(tables)
    assert len(rows) == 1
    assert rows[0]["item_name"] == "产品A"
    assert rows[0]["income"] == "50亿元"


def test_sections_to_evidence_schema():
    sections = {
        "business_review": "2025年营收增长12%。",
        "audit_opinion": "标准无保留意见。",
    }
    evidence = sections_to_evidence(
        sections,
        source_url="https://static.cninfo.com.cn/fake.pdf",
        announcement_meta={
            "title": "测试公司2025年年度报告",
            "announcement_id": "12345",
            "announcement_type": "annual_report",
            "published_at": "2026-04-28",
            "parser_used": "pdfplumber",
            "full_text_length": 1000,
        },
    )
    assert len(evidence) == 2
    assert evidence[0]["source_type"] == "exchange_announcement"
    assert evidence[0]["trust_level"] == "high"
    assert evidence[0]["requires_manual_review"] is True
    assert "巨潮年报-" in evidence[0]["label"]
