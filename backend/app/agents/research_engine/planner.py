"""Research planner.

The Plan-Execute architecture uses an LLM planner first, with the rule planner
kept as a deterministic fallback.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.config import settings

from .state import ResearchTask


def create_default_research_plan(enterprise_name: str, objective: str = "完整贷前尽调") -> List[ResearchTask]:
    return [
        {
            "id": "rt_subject_identity",
            "question": "目标企业主体、简称、上市公司证券代码是否匹配？",
            "purpose": "确认分析对象，避免企业简称、集团主体和上市主体混淆。",
            "category": "business",
            "required_evidence": ["企业主体名称", "统一社会信用代码或证券代码", "基础工商/上市公司信息"],
            "priority": 1,
            "status": "pending",
            "tool_hints": ["listed_company", "business_agent", "bocha_search"],
        },
        {
            "id": "rt_business_governance",
            "question": "企业工商登记、经营状态、股权治理是否存在影响准入的异常？",
            "purpose": "确认主体真实性、经营稳定性和治理风险。",
            "category": "business",
            "required_evidence": ["工商登记", "经营状态", "注册资本", "股权/实控人", "异常经营线索"],
            "priority": 2,
            "status": "pending",
            "tool_hints": ["business_agent", "bocha_search"],
        },
        {
            "id": "rt_financial_trend",
            "question": "近三年财务趋势、盈利质量、现金流和偿债能力是否支持授信准入？",
            "purpose": "识别财务真实性、还款来源和短期偿债压力。",
            "category": "financial",
            "required_evidence": ["近三年三大表", "营业收入", "净利润", "资产负债率", "经营现金流", "应收账款"],
            "priority": 3,
            "status": "pending",
            "tool_hints": ["financial_agent", "listed_company", "uploaded_files"],
        },
        {
            "id": "rt_legal_compliance",
            "question": "是否存在重大诉讼、被执行、失信、行政处罚或公告风险？",
            "purpose": "判断司法和合规事项是否影响授信安全边界。",
            "category": "legal",
            "required_evidence": ["裁判/诉讼", "被执行", "失信", "行政处罚", "重大公告"],
            "priority": 4,
            "status": "pending",
            "tool_hints": ["legal_agent", "bocha_search"],
        },
        {
            "id": "rt_industry_position",
            "question": "主营业务、行业分类、行业周期和竞争格局是否支撑企业持续经营？",
            "purpose": "判断企业所在行业的景气度、竞争压力和授信审查重点。",
            "category": "industry",
            "required_evidence": ["行业分类", "主营构成", "行业地位", "行业规则", "研报/年报经营讨论"],
            "priority": 5,
            "status": "pending",
            "tool_hints": ["industry_agent", "rag", "bocha_search"],
        },
        {
            "id": "rt_credit_policy",
            "question": "现有证据下应形成怎样的准入边界、补充材料和贷后监控要求？",
            "purpose": "将专项事实转化为授信审查动作和客户经理访谈清单。",
            "category": "credit",
            "required_evidence": ["授信政策", "贷后监控要求", "专项风险结论", "证据缺口"],
            "priority": 6,
            "status": "pending",
            "tool_hints": ["rag"],
        },
    ]


def create_research_plan(enterprise_name: str, objective: str = "完整贷前尽调") -> Dict[str, Any]:
    """Create an executable research plan with LLM-first fallback behavior."""

    default_tasks = create_default_research_plan(enterprise_name, objective)
    if not settings.ENABLE_LLM_RESEARCH_PLANNER:
        for task in default_tasks:
            task["planner_source"] = "rule_fallback"
        return {
            "success": True,
            "tasks": default_tasks,
            "planner_source": "rule_fallback",
            "metadata": {"reason": "LLM Planner disabled"},
            "error": "",
        }

    from .llm_planner import create_llm_research_plan

    llm_result = create_llm_research_plan(enterprise_name, objective, default_tasks, max_tasks=settings.RESEARCH_PLANNER_MAX_TASKS)
    if llm_result.get("success") and llm_result.get("tasks"):
        return {
            "success": True,
            "tasks": llm_result.get("tasks", []),
            "planner_source": "llm",
            "metadata": llm_result.get("metadata", {}),
            "error": "",
        }

    for task in default_tasks:
        task["planner_source"] = "rule_fallback"
    return {
        "success": True,
        "tasks": default_tasks,
        "planner_source": "rule_fallback",
        "metadata": {"reason": "LLM Planner failed; using default plan"},
        "error": llm_result.get("error") or "LLM Planner failed",
    }
