import pytest
from unittest.mock import patch, MagicMock

from app.agents.tools.industry_market_data_tool import get_industry_market_data
from app.agents.sub_agents.industry_diagnostic_writer import (
    _build_market_data_anchor_text,
    _fetch_market_data_anchor,
    build_industry_diagnostic_narrative,
    render_industry_diagnostics,
)


@pytest.fixture
def fake_data_anchors():
    return {
        "success": True,
        "industry_name": "半导体",
        "index_data": {
            "success": True,
            "symbol": "半导体",
            "latest_close": 1150.0,
            "latest_date": "20241230",
            "year_change_pct": 13.86,
            "avg_turnover": 1.7,
            "source": "东方财富行业指数",
            "error": "",
            "quality_level": "ok",
            "fallback_search": {},
        },
        "market_size": {
            "queries": ["半导体 市场规模 2024"],
            "results": [
                {
                    "title": "半导体市场规模2024",
                    "snippet": "约5000亿元",
                    "source": "某券商",
                    "date": "2024-01",
                    "url": "http://a.com",
                    "trust_level": "medium",
                    "confidence": 0.72,
                    "source_type": "commercial_or_mainstream_public_source",
                    "requires_manual_review": False,
                    "query": "半导体 市场规模 2024",
                }
            ],
            "quality_score": 0.72,
            "quality_level": "medium",
            "refilled": False,
        },
        "concentration": {
            "queries": ["半导体 CR5"],
            "results": [
                {
                    "title": "半导体竞争格局",
                    "snippet": "CR5约60%",
                    "source": "某研究所",
                    "date": "2024-03",
                    "url": "http://b.com",
                    "trust_level": "low",
                    "confidence": 0.45,
                    "source_type": "aggregated_or_unknown",
                    "requires_manual_review": True,
                    "query": "半导体 CR5",
                }
            ],
            "quality_score": 0.45,
            "quality_level": "low",
            "refilled": False,
        },
        "policy": {"queries": [], "results": [], "quality_score": 0.0, "quality_level": "none", "refilled": False},
        "chain": {"queries": [], "results": [], "quality_score": 0.0, "quality_level": "none", "refilled": False},
        "research_reports": {"queries": [], "results": [], "quality_score": 0.0, "quality_level": "none", "refilled": False},
        "quality_summary": {
            "overall_quality": 0.65,
            "categories_present": 5,
            "categories_missing": ["concentration"],
            "needs_refill": True,
        },
    }


@pytest.fixture
def fake_classification():
    return {
        "industry_name": "半导体",
        "semantic_industry_name": "半导体",
        "semantic_industry_id": "semiconductor",
        "industry_path": ["电子", "半导体"],
    }


@pytest.fixture
def fake_public_info():
    return {"basic_info": {"main_business": "集成电路设计"}}


@pytest.fixture
def fake_knowledge_context():
    return {"triggered_rules": [], "knowledge_briefs": []}


class TestBuildMarketDataAnchorText:
    def test_success(self, fake_data_anchors):
        lines = _build_market_data_anchor_text(fake_data_anchors)
        assert len(lines) > 1
        assert "东方财富行业指数" in lines[0]
        assert "1150" in lines[0]
        assert "13.86%" in lines[0]
        assert "[市场规模]" in lines[1]

    def test_empty_index(self, fake_data_anchors):
        anchors = {**fake_data_anchors, "index_data": {"success": False}}
        lines = _build_market_data_anchor_text(anchors)
        assert "未获取到有效指数数据" in lines[0]

    def test_empty_all(self):
        lines = _build_market_data_anchor_text({})
        assert "未获取到有效指数数据" in lines[0]

    def test_quality_level_low_appended(self, fake_data_anchors):
        lines = _build_market_data_anchor_text(fake_data_anchors)
        concentration_lines = [l for l in lines if "[竞争格局]" in l]
        assert len(concentration_lines) > 0
        assert "[数据质量：low]" in concentration_lines[0]

    def test_requires_manual_review_appended(self, fake_data_anchors):
        lines = _build_market_data_anchor_text(fake_data_anchors)
        concentration_lines = [l for l in lines if "[竞争格局]" in l]
        assert len(concentration_lines) > 0
        assert "[需人工复核]" in concentration_lines[0]

    def test_index_quality_level_stale(self, fake_data_anchors):
        anchors = {**fake_data_anchors}
        anchors["index_data"] = {**anchors["index_data"], "quality_level": "stale"}
        lines = _build_market_data_anchor_text(anchors)
        assert "[指数数据：stale]" in lines[0]

    def test_missing_category_with_quality(self, fake_data_anchors):
        lines = _build_market_data_anchor_text(fake_data_anchors)
        policy_lines = [l for l in lines if "[政策]" in l]
        assert len(policy_lines) > 0
        assert "[数据质量：none]" in policy_lines[0]
        assert "[需补充]" in policy_lines[0]


class TestFetchMarketDataAnchor:
    @patch("app.agents.tools.industry_market_data_tool.get_industry_market_data")
    def test_success(self, mock_get_data, fake_data_anchors, fake_classification):
        mock_get_data.return_value = fake_data_anchors
        result = _fetch_market_data_anchor(fake_classification)
        assert result["success"] is True
        assert result["industry_name"] == "半导体"
        assert result["index_data"]["latest_close"] == 1150.0
        assert len(result["market_size"]["results"]) == 1
        # Verify truncation
        assert len(result["market_size"]["results"][0]["title"]) <= 120
        assert len(result["market_size"]["results"][0]["snippet"]) <= 120
        # Verify quality fields passed through
        assert result["quality_summary"]["overall_quality"] == 0.65
        assert result["market_size"]["quality_score"] == 0.72
        assert result["market_size"]["quality_level"] == "medium"
        assert result["concentration"]["quality_level"] == "low"
        assert result["index_data"]["quality_level"] == "ok"
        assert result["index_data"]["fallback_search"] == {}
        # Verify per-result quality fields
        r = result["market_size"]["results"][0]
        assert r["trust_level"] == "medium"
        assert r["confidence"] == 0.72
        assert r["source_type"] == "commercial_or_mainstream_public_source"
        assert r["requires_manual_review"] is False
        assert r["query"] == "半导体 市场规模 2024"

    @patch("app.agents.tools.industry_market_data_tool.get_industry_market_data")
    def test_failure(self, mock_get_data, fake_classification):
        mock_get_data.return_value = {"success": False, "error": "network error"}
        result = _fetch_market_data_anchor(fake_classification)
        assert result["success"] is False
        assert "network error" in result["error"]


class TestBuildIndustryDiagnosticNarrative:
    @patch("app.agents.sub_agents.industry_diagnostic_writer._fetch_market_data_anchor")
    @patch("app.agents.sub_agents.industry_diagnostic_writer._invoke_llm")
    def test_llm_success(self, mock_invoke, mock_fetch, fake_data_anchors, fake_classification, fake_public_info, fake_knowledge_context):
        mock_fetch.return_value = fake_data_anchors
        mock_invoke.return_value = {
            "provider": "primary",
            "diagnostics": {
                "overall_position": {
                    "cycle_stage": "成长期",
                    "positioning": "半导体设计",
                    "core_judgement": "行业景气度较高",
                    "confidence": 0.75,
                },
                "diagnostics": [
                    {
                        "title": "技术节点风险",
                        "current_anchor": "当前技术节点为7nm",
                        "risk_substance": "先进制程受限",
                        "verification_actions": ["核查技术路线图"],
                        "missing_items": ["良率数据"],
                        "evidence_ids": ["e1"],
                        "rule_ids": ["r1"],
                    },
                    {
                        "title": "产业链议价风险",
                        "current_anchor": "上游设备集中度高",
                        "risk_substance": "设备供应受限",
                        "verification_actions": ["核查供应商合同"],
                        "missing_items": ["替代供应商"],
                        "evidence_ids": ["e2"],
                        "rule_ids": ["r2"],
                    },
                    {
                        "title": "行业KPI适配风险",
                        "current_anchor": "KPI体系待完善",
                        "risk_substance": "缺乏行业基准",
                        "verification_actions": ["建立行业KPI"],
                        "missing_items": ["同业数据"],
                        "evidence_ids": ["e3"],
                        "rule_ids": ["r3"],
                    },
                ],
                "assumptions": ["假设1"],
                "data_boundary": "数据边界说明",
            },
            "quality_warnings": [],
            "race_errors": [],
            "summary": ["summary line"],
        }
        result = build_industry_diagnostic_narrative(
            "测试公司",
            fake_classification,
            public_info=fake_public_info,
            industry_knowledge_context=fake_knowledge_context,
        )
        assert result["success"] is True
        assert result["source"] == "llm"
        assert "data_anchors" in result
        assert result["data_anchors"]["index_data"]["latest_close"] == 1150.0

    @patch("app.agents.sub_agents.industry_diagnostic_writer._fetch_market_data_anchor")
    @patch("app.agents.sub_agents.industry_diagnostic_writer._invoke_llm")
    def test_llm_quality_warnings_fallback(self, mock_invoke, mock_fetch, fake_data_anchors, fake_classification, fake_public_info, fake_knowledge_context):
        mock_fetch.return_value = fake_data_anchors
        mock_invoke.return_value = {
            "provider": "primary",
            "diagnostics": {
                "overall_position": {
                    "cycle_stage": "竞争激烈",
                    "positioning": "半导体",
                    "core_judgement": "竞争激烈",
                    "confidence": 0.6,
                },
                "diagnostics": [
                    {
                        "title": "竞争激烈",
                        "current_anchor": "",
                        "risk_substance": "",
                        "verification_actions": [],
                        "missing_items": [],
                        "evidence_ids": [],
                        "rule_ids": [],
                    },
                ],
                "assumptions": [],
                "data_boundary": "",
            },
            "quality_warnings": ["LLM行业诊断包含泛化表达：竞争激烈"],
            "race_errors": [],
            "summary": ["summary line"],
        }
        result = build_industry_diagnostic_narrative(
            "测试公司",
            fake_classification,
            public_info=fake_public_info,
            industry_knowledge_context=fake_knowledge_context,
        )
        assert result["success"] is False
        assert result["source"] == "fallback"
        assert "data_anchors" in result

    @patch("app.agents.sub_agents.industry_diagnostic_writer._fetch_market_data_anchor")
    @patch("app.agents.sub_agents.industry_diagnostic_writer._invoke_llm")
    def test_llm_exception_fallback(self, mock_invoke, mock_fetch, fake_data_anchors, fake_classification, fake_public_info, fake_knowledge_context):
        mock_fetch.return_value = fake_data_anchors
        mock_invoke.side_effect = RuntimeError("LLM timeout")
        result = build_industry_diagnostic_narrative(
            "测试公司",
            fake_classification,
            public_info=fake_public_info,
            industry_knowledge_context=fake_knowledge_context,
        )
        assert result["success"] is False
        assert result["source"] == "fallback"
        assert "data_anchors" in result
        assert "RuntimeError" in str(result["quality_warnings"])


class TestRenderIndustryDiagnostics:
    def test_with_data_anchors(self, fake_data_anchors):
        diagnostics = {
            "overall_position": {
                "cycle_stage": "成长期",
                "positioning": "半导体设计",
                "core_judgement": "行业景气度较高",
            },
            "diagnostics": [
                {
                    "title": "技术风险",
                    "current_anchor": "技术节点7nm",
                    "risk_substance": "先进制程受限",
                    "verification_actions": ["核查技术路线"],
                    "missing_items": ["良率"],
                }
            ],
            "data_boundary": "基于公开资料",
            "data_anchors": fake_data_anchors,
        }
        lines = render_industry_diagnostics(diagnostics)
        assert len(lines) > 1
        assert "数据锚点" in lines[1]
        assert "东方财富行业指数" in lines[1]

    def test_without_data_anchors(self):
        diagnostics = {
            "overall_position": {
                "cycle_stage": "成长期",
                "positioning": "半导体设计",
                "core_judgement": "行业景气度较高",
            },
            "diagnostics": [
                {
                    "title": "技术风险",
                    "current_anchor": "技术节点7nm",
                    "risk_substance": "先进制程受限",
                    "verification_actions": ["核查技术路线"],
                    "missing_items": ["良率"],
                }
            ],
            "data_boundary": "基于公开资料",
        }
        lines = render_industry_diagnostics(diagnostics)
        assert len(lines) > 1
        assert "数据锚点" not in " ".join(lines)
