from app.agents.research_engine.report_quality_evaluator import evaluate_report_quality


def _evidence(idx: int, domain: str = "financial", trust: str = "high"):
    return {
        "id": f"ev_{idx}",
        "label": f"证据{idx}",
        "value": "公开资料",
        "source": "交易所公告",
        "source_name": "交易所公告",
        "source_url": f"https://example.com/{idx}",
        "trust_level": trust,
        "reliability": trust,
        "confidence": 0.9 if trust == "high" else 0.7,
        "domain": domain,
    }


def _chapter(chapter_id: str, summary: str, refs: list[str]):
    return {
        "id": chapter_id,
        "title": chapter_id,
        "summary": [summary],
        "summary_citations": [{"text": summary, "evidence_refs": refs[:3]}],
        "subsections": [{"title": "小节", "items": [summary], "evidence_refs": refs[:2]}],
        "findings": [{"title": "发现", "conclusion": summary, "evidence_refs": refs[:2]}],
        "evidence_refs": refs[:5],
    }


def test_report_quality_evaluator_passes_structured_report():
    evidence = [_evidence(i, domain="financial" if i < 6 else "industry" if i < 11 else "legal") for i in range(1, 19)]
    refs = [item["id"] for item in evidence]
    report = {
        "enterprise_name": "士兰微",
        "risk_score": 82,
        "risk_rating": "low",
        "recommendation": "建议有条件准入",
        "credit_decision": {"suggestion": "有条件准入", "credit_limit_advice": "控制首笔额度", "term_advice": "短期限", "collateral_advice": "应收账款监管"},
        "report_chapters": [
            _chapter("overview", "综合评级、准入建议、核心风险、授信边界和数据边界。", refs),
            _chapter("business", "统一社会信用代码、法定代表人、注册资本、经营范围、股权和行政处罚已核验。", refs),
            _chapter("financial", "近三年营业收入、净利润、毛利率、经营现金流、资产负债率、流动比率和应收账款已形成诊断。", refs),
            _chapter("industry", "行业定位为半导体，已分析周期、竞争格局、政策、上下游、议价能力、同业和授信关注点。", refs),
            _chapter("legal", "裁判、被执行、失信和行政处罚线索已核验。", refs),
            _chapter("risks", "交叉验证财务与经营范围、现金流与利润、司法风险和行业周期。", refs),
            _chapter("credit", "额度、期限、担保、提款和贷后条件已结构化输出。", refs),
            _chapter("evidence", "证据链和待补充材料。", refs),
        ],
        "evidence": evidence,
    }
    result = evaluate_report_quality(report, sample={"expected_aliases": ["士兰微"], "expected_industry_keywords": ["半导体"]})
    assert result["passed"] is True
    assert result["overall_score"] >= 75


def test_report_quality_evaluator_catches_subject_pollution_and_missing_refs():
    report = {
        "enterprise_name": "分析一下士兰微这个上市公司",
        "risk_score": 79,
        "risk_rating": "medium",
        "credit_decision": {"suggestion": "建议采纳"},
        "report_chapters": [{"id": "overview", "summary": ["报告专项待补充"]}],
        "evidence": [],
    }
    result = evaluate_report_quality(report)
    assert result["passed"] is False
    severities = {issue["severity"] for issue in result["issues"]}
    assert "P0" in severities
    assert any(issue["dimension"] == "subject_identity" for issue in result["issues"])
    assert any(issue["dimension"] == "inline_citations" for issue in result["issues"])


def test_report_quality_evaluator_catches_ocr_corrupted_terms():
    report = {
        "enterprise_name": "测试企业",
        "risk_score": 82,
        "risk_rating": "low",
        "recommendation": "建议有条件准入",
        "credit_decision": {"suggestion": "有条件准入"},
        "report_chapters": [
            _chapter("overview", "综合评级、准入建议、核心风险和数据边界。", ["ev_1"]),
            _chapter("business", "统一社会信用代码、法定代表人、注册资本、经营范围已核验。", ["ev_2"]),
            _chapter("financial", "指标 2023年 2024年 2025年 趋势 EBITDA(亿元) 6.42 4.36 -1.53 持续下降 销售净利率(%) 2.61 1.59 -1.86 持续下降 ROA(%) 0.64 0.43 -0.57 持续下降 鱼子（％） 0.96 0.69 -0.95 持续下降。", ["ev_3"]),
            _chapter("industry", "行业定位为半导体。", ["ev_4"]),
            _chapter("legal", "司法合规风险已核验。", ["ev_5"]),
            _chapter("risks", "交叉验证财务与司法风险。", ["ev_6"]),
            _chapter("credit", "额度、期限、担保、提款和贷后条件已输出。", ["ev_7"]),
            _chapter("evidence", "证据链和待补充材料。", ["ev_8"]),
        ],
        "evidence": [_evidence(i) for i in range(1, 9)],
    }
    result = evaluate_report_quality(report)
    assert result["passed"] is False
    assert any("鱼子" in issue["message"] for issue in result["issues"])
