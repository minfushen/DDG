"""Research planner.

The Plan-Execute architecture uses an LLM planner first, with the rule planner
kept as a deterministic fallback.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.config import settings
from app.agents.skills import load_due_diligence_blueprint, load_skills_for_task

from .state import ResearchTask


def build_due_diligence_blueprint() -> Dict[str, Any]:
    return load_due_diligence_blueprint()


def _task_from_chapter(chapter: Dict[str, Any], index: int) -> ResearchTask:
    category = str(chapter.get("category") or "general")
    title = str(chapter.get("title") or chapter.get("id") or "尽调章节")
    required_data = [str(item) for item in (chapter.get("required_data") or [])[:6]]
    success = [str(item) for item in (chapter.get("success_criteria") or [])[:3]]
    fallback = str(chapter.get("fallback_language") or "资料不足时输出审慎结论并列为前置核查事项。")
    question_map = {
        "business": "企业主体、工商登记、股权治理和异常事项是否影响授信准入？",
        "financial": "近三年财务趋势、盈利质量、现金流和偿债能力是否支持授信准入？",
        "industry": "主营业务、行业周期、竞争格局和上下游环境是否支撑持续经营？",
        "legal": "是否存在影响授信安全边界的诉讼、执行、失信、处罚或监管问询？",
        "credit": "现有证据下应形成怎样的准入边界、前置条件和贷后监控要求？",
    }
    purpose_map = {
        "business": "确认主体真实性、治理稳定性和关联风险。",
        "financial": "识别财务真实性、还款来源和短期偿债压力。",
        "industry": "判断行业景气、竞争压力和经营韧性。",
        "legal": "判断司法合规事项是否构成准入或额度约束。",
        "credit": "将专项结论转化为授信审查动作。",
    }
    return {
        "id": f"rt_{chapter.get('id') or category}",
        "question": question_map.get(category, f"核查{title}是否支持贷前尽调结论？"),
        "purpose": purpose_map.get(category, f"为{title}章节形成证据和业务判断。"),
        "category": category,
        "required_evidence": required_data,
        "priority": int(chapter.get("display_order") or index),
        "status": "pending",
        "tool_hints": [str(item) for item in (chapter.get("preferred_tools") or [])[:4]],
        "success_criteria": success,
        "chapter_id": chapter.get("id"),
        "chapter_title": title,
        "fallback_language": fallback,
        "credit_action_when_missing": chapter.get("credit_action_when_missing"),
        "planner_source": "blueprint_rule",
    }


def create_default_research_plan(enterprise_name: str, objective: str = "完整贷前尽调") -> List[ResearchTask]:
    blueprint = build_due_diligence_blueprint()
    tasks: List[ResearchTask] = [
        {
            "id": "rt_subject_identity",
            "question": "目标企业主体、简称、上市公司证券代码是否匹配？",
            "purpose": "确认分析对象，避免企业简称、集团主体和上市主体混淆。",
            "category": "business",
            "required_evidence": ["企业主体名称", "统一社会信用代码或证券代码", "基础工商/上市公司信息"],
            "priority": 1,
            "status": "pending",
            "tool_hints": ["listed_company", "business_agent", "bocha_search"],
            "success_criteria": ["确认分析主体", "排除简称或集团主体混淆"],
            "chapter_id": "business",
            "chapter_title": "企业主体与治理结构",
            "fallback_language": "主体存在歧义时必须进入人工确认或以权威来源复核。",
        },
    ]
    for index, chapter in enumerate(blueprint.get("chapters") or [], start=2):
        if not isinstance(chapter, dict) or chapter.get("category") in {"overview", "evidence", "completeness", "risk"}:
            continue
        tasks.append(_task_from_chapter(chapter, index))
    return tasks


def create_research_plan(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    thought_loop_context: str = "",
    skill_context: Dict[str, Any] | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    """Create an executable research plan with LLM-first fallback behavior."""

    default_tasks = create_default_research_plan(enterprise_name, objective)
    runtime_skills = skill_context or load_skills_for_task("loan_due_diligence", objective)
    blueprint = build_due_diligence_blueprint()
    if not settings.ENABLE_LLM_RESEARCH_PLANNER:
        for task in default_tasks:
            task["planner_source"] = "rule_fallback"
        return {
            "success": True,
            "tasks": default_tasks,
            "planner_source": "rule_fallback",
            "metadata": {"reason": "LLM Planner disabled", "runtime_skills": runtime_skills.get("skill_ids", []), "blueprint": blueprint},
            "error": "",
        }

    from .llm_planner import create_llm_research_plan

    llm_result = create_llm_research_plan(
        enterprise_name,
        objective,
        default_tasks,
        max_tasks=settings.RESEARCH_PLANNER_MAX_TASKS,
        thought_loop_context=thought_loop_context,
        skill_context=str(runtime_skills.get("context") or ""),
        session_id=session_id,
        task_id=task_id,
    )
    if llm_result.get("success") and llm_result.get("tasks"):
        metadata = llm_result.get("metadata", {})
        metadata["runtime_skills"] = runtime_skills.get("skill_ids", [])
        metadata["skill_errors"] = runtime_skills.get("errors", [])
        metadata["blueprint"] = blueprint
        return {
            "success": True,
            "tasks": llm_result.get("tasks", []),
            "planner_source": "llm",
            "metadata": metadata,
            "error": "",
        }

    for task in default_tasks:
        task["planner_source"] = "rule_fallback"
    llm_error = llm_result.get("error") or "LLM Planner failed"
    friendly_reason = "LLM 规划器返回结果不符合预期，已降级为规则计划。"
    if "missing tasks array" in str(llm_error):
        friendly_reason = "LLM 规划器返回的任务列表格式不正确，已降级为规则计划。"
    elif "no valid executable tasks" in str(llm_error):
        friendly_reason = "LLM 规划器未生成有效可执行任务，已降级为规则计划。"
    return {
        "success": True,
        "tasks": default_tasks,
        "planner_source": "rule_fallback",
        "metadata": {"reason": friendly_reason, "runtime_skills": runtime_skills.get("skill_ids", []), "skill_errors": runtime_skills.get("errors", []), "blueprint": blueprint, "original_error": llm_error},
        "error": "",
    }
