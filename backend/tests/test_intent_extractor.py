"""多意图 + 槽位抽取 与 planner 裁剪的单元测试（快速路径，不依赖 LLM/网络）。"""

from app.agents.planning import intent_extractor as ie
from app.agents.research_engine.planner import create_default_research_plan, create_research_plan


def test_multi_intent_detection():
    out = ie.fast_extract_user_intent("分析一下A公司的财务风险和行业竞争格局")
    cats = [i["category"] for i in out["intents"]]
    assert "financial" in cats and "industry" in cats
    assert out["task_type"] == "single"
    assert out["target_agent"] == "financial"
    # 无 full 关键词时不裁剪到全部
    assert len(cats) == 2


def test_full_intent_is_not_restricted():
    out = ie.fast_extract_user_intent("请对欣旺达做一份完整贷前尽调报告")
    assert out["task_type"] == "full"
    assert out["target_agent"] is None
    assert len(out["intents"]) == len(ie.RESEARCH_CATEGORIES)


def test_slot_extraction_and_validation():
    text = "近三年 同业对比 半导体 拟申请5000万授信 期限3年 含现场材料 输出简报"
    slots, issues = ie.validate_slots(ie._extract_slots(text))
    assert slots["time_window"] == "近三年"
    assert slots["comparison"] == "peer"
    assert slots["industry_segment"] == "半导体"
    assert "拟申请5000万授信" in (slots["credit_assumptions"] or "")
    assert "期限3年" in (slots["credit_assumptions"] or "")
    assert slots["has_on_site_materials"] is True
    assert slots["output_format"] == "brief"
    # 缺失槽位补默认
    assert slots["depth"] == "full"
    assert issues == []


def test_slot_validation_rejects_bad_enum():
    clean, issues = ie.validate_slots({"depth": "ultra", "comparison": "peer", "ghost": 1})
    assert clean["depth"] == "full"  # 非法枚举回退默认
    assert clean["comparison"] == "peer"
    assert "ghost" not in clean  # 未知键丢弃
    assert any("depth" in i for i in issues)


def test_ambiguity_sets_needs_clarification():
    out = ie.fast_extract_user_intent("帮我分析一下这家公司的财务风险")
    assert out["needs_clarification"] is True
    assert out["ambiguities"]
    assert out["clarification_prompt"]


def test_backward_compat_fields_present():
    out = ie.fast_extract_user_intent("分析宁德时代的行业情况")
    for key in ("enterprise_name", "task_type", "target_agent", "stock_code", "confidence", "source"):
        assert key in out
    assert out["enterprise_name"] == "宁德时代新能源科技股份有限公司"
    assert out["stock_code"] == "300750"


def test_planner_restricts_by_intent_categories():
    tasks = create_default_research_plan(
        "测试公司", intent_categories=["financial", "industry"],
        slots={"depth": "quick", "time_window": "近三年"},
    )
    cats = {t["category"] for t in tasks}
    assert "financial" in cats and "industry" in cats
    assert "relationship" not in cats and "sentiment" not in cats
    # 主体确认始终保留
    assert any(t["id"] == "rt_subject_identity" for t in tasks)
    # 槽位已挂载
    assert all(t.get("slots", {}).get("depth") == "quick" for t in tasks)


def test_planner_full_keeps_all_when_no_categories():
    tasks = create_default_research_plan("测试公司")
    cats = {t["category"] for t in tasks}
    assert {"business", "financial", "legal", "industry", "relationship", "sentiment", "credit"} <= cats


def test_research_plan_restricts_via_parsed_intent(monkeypatch):
    # 强制规则计划路径，保证离线确定性
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ENABLE_LLM_RESEARCH_PLANNER", False)
    parsed = ie.fast_extract_user_intent("分析比亚迪的财务和司法风险")
    result = create_research_plan("比亚迪", parsed_intent=parsed)
    cats = {t["category"] for t in result["tasks"]}
    assert "financial" in cats and "legal" in cats
    assert "industry" not in cats and "relationship" not in cats
    assert result["metadata"].get("parsed_intent") is parsed
