# backend/tests/test_industry_report_builder_data_anchors.py
"""行业报告 builder 数据锚点展示测试。"""

from unittest.mock import patch

import pytest

from app.agents.sub_agents.industry_report_builder import build_industry_analysis_report


@pytest.fixture
def classification():
    return {
        "industry_code": "C39",
        "industry_name": "计算机、通信和其他电子设备制造业",
        "industry_path": ["制造业", "计算机、通信和其他电子设备制造业"],
        "industry_path_codes": ["C", "C39"],
        "semantic_industry_id": "semiconductor",
        "semantic_industry_name": "半导体",
        "confidence": 0.92,
        "matched_signals": ["芯片设计"],
        "candidates": [],
        "classification_source": "llm_adjudicated",
        "llm_reason": "主营含芯片设计",
        "ignored_noise": [],
        "guide_files": ["nonexistent_guide.md"],
    }


@pytest.fixture
def data_anchors():
    return {
        "success": True,
        "industry_name": "半导体",
        "index_data": {
            "success": True,
            "symbol": "半导体",
            "latest_close": 1234.56,
            "latest_date": "2025-06-20",
            "year_change_pct": 15.3,
            "avg_turnover": 89.12,
            "source": "东方财富行业指数",
            "error": "",
        },
        "market_size": {
            "queries": ["半导体 市场规模 2024 亿元 CAGR"],
            "results": [
                {
                    "title": "2024年中国半导体市场规模",
                    "snippet": "市场规模约 1.2 万亿元，同比增长 8%。",
                    "source": "东方财富",
                    "date": "2024-12-01",
                    "url": "https://example.com/ms",
                }
            ],
        },
        "concentration": {"queries": [], "results": []},
        "policy": {"queries": [], "results": []},
        "chain": {"queries": [], "results": []},
        "research_reports": {
            "queries": ["半导体 行业研究报告"],
            "results": [
                {
                    "title": "半导体行业深度报告",
                    "snippet": "周期底部渐近。",
                    "source": "某券商研究所",
                    "date": "2025-05-01",
                    "url": "https://example.com/report",
                }
            ],
        },
    }


@pytest.fixture
def diagnostic_narrative(data_anchors):
    return {
        "success": True,
        "source": "llm",
        "summary": ["【行业定位与周期判断】周期底部 | 半导体行业定位。"],
        "diagnostics": {
            "overall_position": {"cycle_stage": "底部", "positioning": "半导体"},
            "diagnostics": [
                {
                    "title": "测试风险1",
                    "current_anchor": "锚定",
                    "risk_substance": "风险",
                    "verification_actions": ["核查"],
                    "missing_items": [],
                    "evidence_ids": [],
                    "rule_ids": [],
                },
                {
                    "title": "测试风险2",
                    "current_anchor": "锚定",
                    "risk_substance": "风险",
                    "verification_actions": ["核查"],
                    "missing_items": [],
                    "evidence_ids": [],
                    "rule_ids": [],
                },
                {
                    "title": "测试风险3",
                    "current_anchor": "锚定",
                    "risk_substance": "风险",
                    "verification_actions": ["核查"],
                    "missing_items": [],
                    "evidence_ids": [],
                    "rule_ids": [],
                },
            ],
        },
        "quality_warnings": [],
        "llm_elapsed_ms": 1200,
        "llm_provider": "test",
        "data_anchors": data_anchors,
    }


def test_report_includes_data_anchor_section(classification, diagnostic_narrative, monkeypatch):
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    assert report["report_type"] == "industry_analysis"
    titles = [s["title"] for s in report["sections"]]
    assert "二、行业数据锚点" in titles
    assert "一、行业定位与周期判断" in titles
    assert "三、行业识别结论" in titles

    data_section = next(s for s in report["sections"] if s["title"] == "二、行业数据锚点")
    analysis = "\n".join(data_section["analysis"])
    assert "半导体" in analysis
    assert "1234.56" in analysis
    assert "15.3%" in analysis
    assert "2024年中国半导体市场规模" in analysis
    assert "半导体行业深度报告" in analysis

    evidence_labels = [e["label"] for e in report["evidence"]]
    assert "行业指数" in evidence_labels
    assert "公开搜索数据锚点" in evidence_labels


def test_report_renumbers_sections_when_data_anchors_missing(classification, diagnostic_narrative, monkeypatch):
    diagnostic_narrative["data_anchors"] = {}
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    titles = [s["title"] for s in report["sections"]]
    assert "二、行业数据锚点" in titles
    data_section = next(s for s in report["sections"] if s["title"] == "二、行业数据锚点")
    assert "未获取" in "\n".join(data_section["analysis"])


def test_quality_assessment_structure(classification, diagnostic_narrative, monkeypatch):
    """验证 _format_data_anchor_section 返回的 section 包含 quality_assessment，且字段结构与预期一致。"""
    diagnostic_narrative["data_anchors"] = {
        "index_data": {
            "success": True,
            "symbol": "半导体",
            "latest_close": 1234.56,
            "latest_date": "2025-06-20",
            "year_change_pct": 15.3,
            "avg_turnover": 89.12,
            "source": "东方财富行业指数",
            "quality_level": "ok",
        },
        "market_size": {
            "results": [
                {
                    "title": "2024年中国半导体市场规模",
                    "snippet": "市场规模约 1.2 万亿元，同比增长 8%。",
                    "source": "东方财富",
                    "date": "2024-12-01",
                    "url": "https://example.com/ms",
                    "trust_level": "medium",
                    "confidence": 0.72,
                    "requires_manual_review": True,
                }
            ],
            "quality_score": 0.72,
            "quality_level": "medium",
        },
        "concentration": {"results": [], "quality_score": 0.0, "quality_level": "none"},
        "policy": {
            "results": [
                {
                    "title": "半导体政策",
                    "snippet": "政策利好",
                    "source": "政府网",
                    "date": "2025-01-01",
                    "url": "https://example.com/policy",
                    "trust_level": "high",
                    "confidence": 0.9,
                    "requires_manual_review": False,
                }
            ],
            "quality_score": 0.9,
            "quality_level": "high",
        },
        "chain": {
            "results": [],
            "quality_score": 0.0,
            "quality_level": "low",
        },
        "research_reports": {
            "results": [
                {
                    "title": "半导体行业深度报告",
                    "snippet": "周期底部渐近。",
                    "source": "某券商研究所",
                    "date": "2025-05-01",
                    "url": "https://example.com/report",
                    "trust_level": "medium",
                    "confidence": 0.65,
                    "requires_manual_review": False,
                }
            ],
            "quality_score": 0.65,
            "quality_level": "medium",
        },
        "quality_summary": {
            "overall_quality": 0.65,
            "categories_present": 5,
            "categories_missing": ["concentration"],
            "needs_refill": True,
        },
    }
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    data_section = next(s for s in report["sections"] if s["title"] == "二、行业数据锚点")
    qa = data_section.get("quality_assessment", {})
    assert qa["overall_quality"] == 0.65
    assert qa["categories_present"] == 5
    assert qa["categories_missing"] == ["concentration"]
    assert qa["needs_refill"] is True
    assert qa["category_levels"] == {
        "index_data": "ok",
        "market_size": "medium",
        "concentration": "none",
        "policy": "high",
        "chain": "low",
        "research_reports": "medium",
    }


def test_quality_assessment_when_data_anchors_empty(classification, diagnostic_narrative, monkeypatch):
    """验证 data_anchors 为空时 quality_assessment 的默认值。"""
    diagnostic_narrative["data_anchors"] = {}
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    data_section = next(s for s in report["sections"] if s["title"] == "二、行业数据锚点")
    qa = data_section.get("quality_assessment", {})
    assert qa["overall_quality"] == 0
    assert qa["categories_missing"] == ["all"]
    assert qa["needs_refill"] is True
    assert qa["category_levels"] == {}


def test_evidence_includes_manual_review_warning(classification, diagnostic_narrative, monkeypatch):
    """验证当 data_anchors 中某条结果 requires_manual_review=true 时，evidence 中出现"数据质量警告"。"""
    diagnostic_narrative["data_anchors"] = {
        "market_size": {
            "results": [
                {
                    "title": "2024年中国半导体市场规模",
                    "snippet": "市场规模约 1.2 万亿元",
                    "source": "某博客",
                    "date": "2024-12-01",
                    "url": "https://example.com/ms",
                    "requires_manual_review": True,
                }
            ],
            "quality_level": "low",
        },
        "concentration": {"results": [], "quality_level": "none"},
        "policy": {"results": [], "quality_level": "none"},
        "chain": {"results": [], "quality_level": "none"},
        "research_reports": {"results": [], "quality_level": "none"},
        "quality_summary": {
            "overall_quality": 0.2,
            "categories_present": 1,
            "categories_missing": ["concentration", "policy", "chain", "research_reports"],
            "needs_refill": False,
        },
    }
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    evidence_labels = [e["label"] for e in report["evidence"]]
    assert "数据质量警告" in evidence_labels
    warning = next(e for e in report["evidence"] if e["label"] == "数据质量警告")
    assert warning["value"] == "部分公开搜索来源可信度低，需人工复核"
    assert warning["source"] == "Bocha/SearXNG 质量门控"


def test_evidence_includes_data_gap_when_needs_refill(classification, diagnostic_narrative, monkeypatch):
    """验证当 quality_summary.needs_refill=true 时，evidence 中出现"数据缺口"。"""
    diagnostic_narrative["data_anchors"] = {
        "market_size": {
            "results": [
                {
                    "title": "2024年中国半导体市场规模",
                    "snippet": "市场规模约 1.2 万亿元",
                    "source": "东方财富",
                    "date": "2024-12-01",
                    "url": "https://example.com/ms",
                    "requires_manual_review": False,
                }
            ],
            "quality_level": "medium",
        },
        "concentration": {"results": [], "quality_level": "none"},
        "policy": {"results": [], "quality_level": "none"},
        "chain": {"results": [], "quality_level": "none"},
        "research_reports": {"results": [], "quality_level": "none"},
        "quality_summary": {
            "overall_quality": 0.3,
            "categories_present": 1,
            "categories_missing": ["concentration", "policy", "chain", "research_reports"],
            "needs_refill": True,
        },
    }
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    evidence_labels = [e["label"] for e in report["evidence"]]
    assert "数据缺口" in evidence_labels
    gap = next(e for e in report["evidence"] if e["label"] == "数据缺口")
    assert gap["value"] == "部分数据锚点缺失或质量低，建议补充权威来源"
    assert gap["source"] == "行业数据质量摘要"


def test_evidence_no_warning_when_no_manual_review_and_no_refill(classification, diagnostic_narrative, monkeypatch):
    """验证当没有 requires_manual_review 且 needs_refill=false 时，evidence 中不出现警告和缺口。"""
    diagnostic_narrative["data_anchors"] = {
        "market_size": {
            "results": [
                {
                    "title": "2024年中国半导体市场规模",
                    "snippet": "市场规模约 1.2 万亿元",
                    "source": "东方财富",
                    "date": "2024-12-01",
                    "url": "https://example.com/ms",
                    "requires_manual_review": False,
                }
            ],
            "quality_level": "medium",
        },
        "concentration": {"results": [], "quality_level": "none"},
        "policy": {"results": [], "quality_level": "none"},
        "chain": {"results": [], "quality_level": "none"},
        "research_reports": {"results": [], "quality_level": "none"},
        "quality_summary": {
            "overall_quality": 0.3,
            "categories_present": 1,
            "categories_missing": ["concentration", "policy", "chain", "research_reports"],
            "needs_refill": False,
        },
    }
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    evidence_labels = [e["label"] for e in report["evidence"]]
    assert "数据质量警告" not in evidence_labels
    assert "数据缺口" not in evidence_labels


def test_backward_compatibility_missing_quality_fields(classification, diagnostic_narrative, monkeypatch):
    """验证 data_anchors 缺少 quality 字段时不报错，且 category_levels 默认 none。"""
    diagnostic_narrative["data_anchors"] = {
        "index_data": {"success": True, "symbol": "半导体", "latest_close": 1000},
        "market_size": {"results": [{"title": "t", "snippet": "s", "source": "src", "date": "2024-01-01", "url": "http://example.com"}]},
        "concentration": {"results": []},
        "policy": {"results": []},
        "chain": {"results": []},
        "research_reports": {"results": []},
    }
    monkeypatch.setattr(
        "app.agents.sub_agents.industry_report_builder.build_industry_diagnostic_narrative",
        lambda **kwargs: diagnostic_narrative,
    )

    report = build_industry_analysis_report(
        enterprise_name="测试半导体公司",
        classification=classification,
    )

    data_section = next(s for s in report["sections"] if s["title"] == "二、行业数据锚点")
    qa = data_section.get("quality_assessment", {})
    assert "overall_quality" in qa
    assert qa.get("category_levels") == {
        "index_data": "none",
        "market_size": "none",
        "concentration": "none",
        "policy": "none",
        "chain": "none",
        "research_reports": "none",
    }
    assert qa.get("needs_refill") is False
    # 没有 quality_summary，needs_refill 默认 False，所以不应出现数据缺口 evidence
    evidence_labels = [e["label"] for e in report["evidence"]]
    assert "数据缺口" not in evidence_labels
