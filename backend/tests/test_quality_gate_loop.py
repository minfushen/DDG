"""报告质量门补证循环测试。"""

import pytest

from app.agents.research_engine.graph_engine import (
    _quality_driven_followups_node,
    _route_synthesize,
    _synthesize_node,
)


def _make_graph_state(quality_passed: bool, quality_rounds: int, quality_issues: list):
    return {
        "enterprise_name": "质量门测试公司",
        "research_state": {
            "enterprise_name": "质量门测试公司",
            "objective": "完整贷前尽调",
            "tasks": [],
            "follow_up_tasks": [],
            "timeline": [],
            "iteration": 0,
            "max_iterations": 6,
            "quality_passed": quality_passed,
            "quality_rounds": quality_rounds,
            "quality_issues": quality_issues,
            "report": {"enterprise_name": "质量门测试公司"},
        },
    }


@pytest.mark.asyncio
async def test_quality_driven_followups_creates_tasks_from_issues():
    state = _make_graph_state(
        quality_passed=False,
        quality_rounds=1,
        quality_issues=[
            {"dimension": "financial_depth", "severity": "P0", "message": "财务深度不足", "recommendation": "补充毛利率趋势分析"},
            {"dimension": "legal_business_coverage", "severity": "P1", "message": "司法覆盖不足", "recommendation": "补充被执行信息"},
        ],
    )
    result = await _quality_driven_followups_node(state)
    research_state = result["research_state"]
    assert len(research_state["follow_up_tasks"]) == 2
    assert research_state["follow_up_tasks"][0]["category"] == "quality_refinement"
    assert "毛利率趋势分析" in research_state["follow_up_tasks"][0]["question"]
    assert research_state["tasks"][-1]["generated_by"] == "quality_gate"


def test_route_synthesize_loops_when_quality_fails():
    state = _make_graph_state(False, 1, [{"dimension": "x", "severity": "P0", "message": "m", "recommendation": "r"}])
    assert _route_synthesize(state) == "quality_followups"


def test_route_synthesize_ends_when_quality_passes():
    state = _make_graph_state(True, 1, [])
    assert _route_synthesize(state) == "end"


def test_route_synthesize_ends_after_max_rounds():
    state = _make_graph_state(False, 2, [{"dimension": "x", "severity": "P0", "message": "m", "recommendation": "r"}])
    assert _route_synthesize(state) == "end"


@pytest.mark.asyncio
async def test_synthesize_node_increments_quality_rounds():
    # 使用一个空但合法的 report，让质量门有内容可评测
    from app.agents.research_engine.state import initial_state

    research_state = initial_state("质量门测试公司")
    research_state["report"] = {
        "enterprise_name": "质量门测试公司",
        "risk_score": 50,
        "risk_rating": "medium",
        "report_chapters": [],
        "evidence": [],
    }
    graph_state = {"research_state": research_state}
    result = await _synthesize_node(graph_state)
    assert result["research_state"]["quality_rounds"] == 1
    assert "quality_passed" in result["research_state"]
    assert "quality_issues" in result["research_state"]
