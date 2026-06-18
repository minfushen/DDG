from app.agents.skills import load_due_diligence_blueprint, load_runtime_skill, load_skills_for_task
from app.agents.research_engine.planner import create_research_plan
from app.agents.research_engine.synthesizer import synthesize_research_report


def test_runtime_skills_load_three_core_methodologies():
    loan = load_runtime_skill("loan_due_diligence")
    deep = load_runtime_skill("deep_research")
    financial = load_runtime_skill("financial_analysis")

    assert loan.name == "loan-due-diligence"
    assert "资料完整度" in loan.body
    assert "default_evidence_blueprint.json" in loan.resources
    assert loan.resources["default_evidence_blueprint.json"]["chapters"][0]["id"] == "business"
    assert "claim-evidence" in deep.body.lower()
    assert "财务" in financial.body


def test_due_diligence_blueprint_is_machine_readable():
    blueprint = load_due_diligence_blueprint()

    assert "资料完整度总览" in blueprint["report_outline"]
    assert {chapter["id"] for chapter in blueprint["chapters"]} >= {"business", "financial", "industry", "legal", "credit"}
    assert blueprint["completeness_matrix"][0]["chapter_id"] == "business"


def test_load_skills_for_due_diligence_includes_context():
    result = load_skills_for_task("loan_due_diligence", "完整贷前尽调")

    assert result["errors"] == []
    assert {"deep-research", "loan-due-diligence", "financial-analysis"}.issubset(set(result["skill_ids"]))
    assert "运行时技能" not in result["context"]
    assert "Report Outline" in result["context"]


def test_rule_planner_metadata_contains_skills_and_blueprint(monkeypatch):
    from app.agents.research_engine import planner

    monkeypatch.setattr(planner.settings, "ENABLE_LLM_RESEARCH_PLANNER", False)
    plan = create_research_plan("测试公司", "完整贷前尽调")

    assert plan["planner_source"] == "rule_fallback"
    assert "loan-due-diligence" in plan["metadata"]["runtime_skills"]
    assert "资料完整度总览" in plan["metadata"]["blueprint"]["report_outline"]
    financial_task = next(task for task in plan["tasks"] if task["id"] == "rt_financial")
    assert financial_task["chapter_id"] == "financial"
    assert financial_task["fallback_language"]
    assert financial_task["credit_action_when_missing"]


def test_synthesizer_outputs_completeness_chapter():
    report = synthesize_research_report({
        "enterprise_name": "测试公司",
        "objective": "完整贷前尽调",
        "tasks": [],
        "claims": [],
        "gaps": [],
        "evidence": [],
        "runtime_skills": {"skill_ids": ["deep-research", "loan-due-diligence", "financial-analysis"]},
        "planner": {"metadata": {"blueprint": load_due_diligence_blueprint()}},
    })

    assert report["report_chapters"][0]["id"] == "completeness"
    assert "资料完整度" in report["report_chapters"][0]["title"]
    assert report["report_chapters"][0]["subsections"][0]["title"] == "主体治理"
    assert report["runtime_skills"]["skill_ids"]
    assert "资料完整度总览" in report["due_diligence_blueprint"]["report_outline"]
