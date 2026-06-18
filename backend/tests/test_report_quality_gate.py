from app.agents.research_engine.report_quality_gate import apply_report_quality_gate, build_quality_timeline_event


def _evidence(idx: int):
    return {
        "id": f"ev_{idx}",
        "label": f"证据{idx}",
        "value": "公开资料",
        "source_name": "内部财务计算工具" if idx <= 4 else "交易所公告",
        "source_url": f"https://example.com/{idx}",
        "trust_level": "high",
        "confidence": 0.9,
        "domain": "financial" if idx <= 6 else "industry" if idx <= 10 else "legal",
    }


def _chapter(chapter_id: str, text: str, refs: list[str]):
    return {
        "id": chapter_id,
        "title": chapter_id,
        "summary": [text],
        "summary_citations": [{"text": text, "evidence_refs": refs[:3]}],
        "findings": [{"title": "发现", "conclusion": text, "evidence_refs": refs[:2]}],
        "evidence_refs": refs[:5],
    }


def _structured_report():
    evidence = [_evidence(index) for index in range(1, 18)]
    refs = [item["id"] for item in evidence]
    return {
        "enterprise_name": "测试公司",
        "risk_score": 78,
        "risk_rating": "medium",
        "credit_decision": {"suggestion": "有条件准入", "credit_limit_advice": "控制首笔额度"},
        "report_chapters": [
            _chapter("overview", "综合评级、准入建议、核心风险、授信边界和数据边界。", refs),
            _chapter("business", "统一社会信用代码、法定代表人、注册资本、经营范围、股权和行政处罚已核验。", refs),
            _chapter("financial", "近三年营业收入、净利润、毛利率、经营现金流、资产负债率、流动比率和应收账款已形成诊断。", refs),
            _chapter("industry", "行业定位、周期、竞争格局、政策、上下游、议价能力、同业和授信关注点已形成诊断。", refs),
            _chapter("legal", "裁判、被执行、失信和行政处罚线索已核验。", refs),
            _chapter("risks", "交叉验证财务与经营范围、现金流与利润、司法风险和行业周期。", refs),
            _chapter("credit", "额度、期限、担保、提款和贷后条件已结构化输出。", refs),
            _chapter("evidence", "证据链和待补充材料。", refs),
        ],
        "evidence": evidence,
    }


def test_report_quality_gate_attaches_quality_fields():
    report = _structured_report()
    patch = apply_report_quality_gate(report)

    assert report["quality_evaluation"] == patch["quality_evaluation"]
    assert isinstance(report["quality_score"], int)
    assert "quality_passed" in report
    assert isinstance(report["quality_issues"], list)
    assert report["quality_gate_meta"]["tool_name"] == "evaluate_report_quality"


def test_report_quality_gate_builds_timeline_event():
    report = _structured_report()
    patch = apply_report_quality_gate(report)
    event = build_quality_timeline_event(patch)

    assert event["agent"] == "报告质检"
    assert event["type"] == "analysis"
    assert "quality_score" in event
    assert isinstance(event["findings"], list)
