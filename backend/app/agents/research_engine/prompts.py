"""Prompt templates for the DeepResearch engine."""

from __future__ import annotations

from typing import Any, Dict, List
import json


ALLOWED_RESEARCH_CATEGORIES = ["business", "financial", "legal", "industry", "credit", "general"]
ALLOWED_TOOL_HINTS = [
    "listed_company",
    "business_agent",
    "financial_agent",
    "legal_agent",
    "industry_agent",
    "uploaded_files",
    "bocha_search",
    "rag",
]


def build_research_planner_prompt(
    enterprise_name: str,
    objective: str,
    default_tasks: List[Dict[str, Any]],
    max_tasks: int,
) -> str:
    default_task_summary = [
        {
            "id": task.get("id"),
            "question": task.get("question"),
            "category": task.get("category"),
            "tool_hints": task.get("tool_hints", []),
        }
        for task in default_tasks
    ]
    schema = {
        "plan_summary": "40字以内",
        "planning_assumptions": ["20字以内假设"],
        "tasks": [
            {
                "id": "rt_short_unique_id",
                "question": "60字以内研究问题",
                "purpose": "40字以内任务目的",
                "category": "business|financial|legal|industry|credit|general",
                "priority": 1,
                "required_evidence": ["证据1", "证据2", "证据3"],
                "tool_hints": ["listed_company", "bocha_search"],
                "success_criteria": ["标准1"],
            }
        ],
        "data_boundary": "50字以内",
    }
    return f"""你是银行贷前尽调 DeepResearch 的快速 Plan 节点。把用户目标拆成紧凑、可执行、可路由的研究任务。

企业：{enterprise_name}
研究目标：{objective}

可用任务类别：{', '.join(ALLOWED_RESEARCH_CATEGORIES)}
可用工具提示：{', '.join(ALLOWED_TOOL_HINTS)}
最大任务数：{max_tasks}

规则版基础任务仅供参考，可以重排或小幅补充，但不得编造不可用工具：
{json.dumps(default_task_summary, ensure_ascii=False)}

必须遵守：
1. 只输出 JSON，不输出 Markdown，不输出解释，不输出推理过程。
2. JSON 必须符合这个结构：{json.dumps(schema, ensure_ascii=False)}
3. 每个任务必须包含 question、purpose、category、priority、required_evidence、tool_hints、success_criteria。
4. question 必须能被工具执行，禁止“分析风险”“了解情况”这类空泛表述。
5. category 只能从可用任务类别中选择。
6. tool_hints 只能从可用工具提示中选择。
7. 优先覆盖主体、财务、司法、行业、授信边界；每类最多1个任务。
8. required_evidence 最多3项，tool_hints 最多3项，success_criteria 最多2项。
9. 所有字符串保持短句，总输出控制在 900 个中文字符以内。
"""
