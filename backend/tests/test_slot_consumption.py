"""槽位深层消费测试：验证多意图 slots 在检索参数、行业对比章节与报告配置中的真实生效。"""
import pytest

from app.agents.research_engine import tool_router as tr
from app.agents.sub_agents.industry_report_builder import _comparison_section
from app.agents.research_engine.synthesizer import synthesize_research_report


# ── 1. 槽位 → 检索参数映射 helpers ─────────────────────────────────────
def test_years_back_for_time_window():
    assert tr._years_back_for_time_window("latest") == 1
    assert tr._years_back_for_time_window("近一年") == 1
    assert tr._years_back_for_time_window("近三年") == 3
    assert tr._years_back_for_time_window("近五年") == 5
    # 缺省回退到 3
    assert tr._years_back_for_time_window(None) == 3
    assert tr._years_back_for_time_window("未知") == 3


def test_max_results_for_depth():
    assert tr._max_results_for_depth("quick") == 3
    assert tr._max_results_for_depth("standard") == 5
    assert tr._max_results_for_depth("full") == 8
    assert tr._max_results_for_depth(None) == 5


def test_year_clause_for_time_window():
    assert "2024 2023 2022 2021 2020" in tr._year_clause_for_time_window("近五年")
    assert "最近一年" in tr._year_clause_for_time_window("近一年")
    assert "2024 2023 2022" in tr._year_clause_for_time_window(None)


# ── 2. _bocha_query 按 time_window 生成财报年份从句 ─────────────────────
def test_bocha_query_financial_year_clause_from_slot():
    task = {"category": "financial", "slots": {"time_window": "近五年"}}
    query, freshness, _include = tr._bocha_query("测试公司", task)
    assert "2024 2023 2022 2021 2020" in query

    task2 = {"category": "financial", "slots": {"time_window": "近一年"}}
    query2, _, _ = tr._bocha_query("测试公司", task2)
    assert "最近一年" in query2

    # 缺省 time_window → 近三年年份从句
    task3 = {"category": "financial"}
    query3, _, _ = tr._bocha_query("测试公司", task3)
    assert "2024 2023 2022" in query3


# ── 3. 行业对比章节 _comparison_section ────────────────────────────────
def _fake_classification():
    return {"semantic_industry_name": "半导体", "industry_name": "计算机、通信和其他电子设备制造业"}


def test_comparison_section_peer():
    data_anchors = {"index_data": {"success": True, "symbol": "886063", "latest_close": "3200", "year_change_pct": "12%"}}
    sec = _comparison_section("peer", data_anchors, _fake_classification())
    assert sec is not None
    assert sec["title"] == "同业对比分析"
    assert any("886063" in line for line in sec["analysis"])
    assert any("半导体" in line for line in sec["analysis"])


def test_comparison_section_self():
    sec = _comparison_section("self", {}, _fake_classification())
    assert sec is not None
    assert sec["title"] == "自身纵向对比"


def test_comparison_section_none_and_default():
    assert _comparison_section("none", {}, _fake_classification()) is None
    assert _comparison_section(None, {}, _fake_classification()) is None


# ── 4. 报告层 research_config 落盘 ─────────────────────────────────────
def test_synthesizer_research_config_from_slots():
    slots = {
        "depth": "quick",
        "time_window": "近一年",
        "comparison": "peer",
        "industry_segment": "半导体",
        "credit_assumptions": "拟申请5000万授信，期限3年",
        "has_on_site_materials": True,
        "output_format": "brief",
    }
    state = {
        "enterprise_name": "测试公司",
        "objective": "完整贷前尽调",
        "tasks": [], "claims": [], "gaps": [], "evidence": [],
        "slots": slots,
        "research_rounds": [], "follow_up_tasks": [], "tool_traces": [],
    }
    result = synthesize_research_report(state)
    assert result["research_config"] == slots


def test_synthesizer_research_config_absent_slots():
    state = {
        "enterprise_name": "测试公司",
        "objective": "完整贷前尽调",
        "tasks": [], "claims": [], "gaps": [], "evidence": [],
        "research_rounds": [], "follow_up_tasks": [], "tool_traces": [],
    }
    result = synthesize_research_report(state)
    # 缺省 slots 时所有字段为 None
    assert result["research_config"] == {
        "depth": None, "time_window": None, "comparison": None,
        "industry_segment": None, "credit_assumptions": None,
        "has_on_site_materials": None, "output_format": None,
    }
