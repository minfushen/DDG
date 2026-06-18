import json

from scripts.run_report_quality_regression import run_offline_regression


def _evidence(idx: int, domain: str = "financial"):
    return {
        "id": f"ev_{idx}",
        "label": f"证据{idx}",
        "value": "公开资料",
        "source": "交易所公告",
        "source_name": "交易所公告",
        "source_url": f"https://example.com/{idx}",
        "trust_level": "high",
        "reliability": "high",
        "confidence": 0.9,
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


def test_offline_regression_generates_summary(tmp_path):
    input_dir = tmp_path / "reports"
    output_root = tmp_path / "runs"
    input_dir.mkdir()
    evidence = [_evidence(i, domain="financial" if i < 7 else "industry" if i < 13 else "legal") for i in range(1, 19)]
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
    (input_dir / "silan_micro_report.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    summary = run_offline_regression(input_dir=input_dir, output_root=output_root, run_id="test_run")

    assert summary["total_samples"] == 10
    assert summary["evaluated_count"] == 1
    assert summary["missing_count"] == 9
    assert (output_root / "test_run" / "summary.json").exists()
    assert (output_root / "test_run" / "summary.md").exists()
    evaluated = [item for item in summary["results"] if item["status"] == "evaluated"]
    assert evaluated[0]["sample_id"] == "silan_micro"
