"""Build bounded follow-up research tasks from gaps and claims.

Sequential Thinking MCP records the reflection checkpoint. This module turns the
resulting evidence gaps into executable second-round tasks with conservative
rules, so the research engine can actively补证 without unbounded recursion.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

from .state import ResearchGap, ResearchTask, stable_id


FOLLOW_UP_LIMIT = 3


def _clean(text: Any, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value[:limit]


def _task(
    enterprise_name: str,
    parent_task_id: str,
    category: str,
    question: str,
    purpose: str,
    required_evidence: List[str],
    search_query: str,
    priority: int,
) -> ResearchTask:
    return {
        "id": stable_id("rt_follow", enterprise_name, parent_task_id, question),
        "question": question,
        "purpose": purpose,
        "category": category,
        "required_evidence": required_evidence[:8],
        "priority": priority,
        "status": "pending",
        "tool_hints": ["bocha_search", "rag"],
        "planner_source": "sequential_thinking_follow_up",
        "generated_by": "sequential_thinking_mcp",
        "parent_task_id": parent_task_id,
        "round": 2,
        "search_query": search_query,
    }


def _from_gap(enterprise_name: str, gap: ResearchGap, priority: int) -> ResearchTask | None:
    task_id = gap.get("task_id", "")
    description = _clean(gap.get("description"))
    actions = [str(item) for item in gap.get("suggested_next_actions", []) if str(item).strip()]

    if "financial" in task_id or "财务" in description or "三大表" in description:
        return _task(
            enterprise_name,
            task_id,
            "financial",
            f"补充核查{enterprise_name}财务专项缺口：{description}",
            "围绕财报真实性、现金流质量和偿债能力缺口进行二轮公开资料补证。",
            actions or ["业绩预告/年报公告", "审计意见", "扣非净利润", "经营现金流说明"],
            f"{enterprise_name} 年报 审计意见 扣非净利润 经营现金流 应收账款 业绩说明 巨潮资讯 东方财富",
            priority,
        )

    if "legal" in task_id or "司法" in description or "行政处罚" in description or "执行" in description:
        return _task(
            enterprise_name,
            task_id,
            "legal",
            f"补充核查{enterprise_name}司法合规缺口：{description}",
            "优先查找交易所公告、信用中国、法院执行和行政处罚等权威或准权威线索。",
            actions or ["重大诉讼公告", "被执行/失信", "行政处罚", "监管函件"],
            f"{enterprise_name} 重大诉讼 被执行 失信 行政处罚 监管函 交易所公告 信用中国",
            priority,
        )

    if "industry" in task_id or "行业" in description or "竞争" in description:
        return _task(
            enterprise_name,
            task_id,
            "industry",
            f"补充核查{enterprise_name}行业专项缺口：{description}",
            "围绕细分赛道、主营构成、行业地位、竞争格局和行业KPI进行二轮补证。",
            actions or ["主营构成", "行业地位", "研报摘要", "同业对标", "行业KPI"],
            f"{enterprise_name} 主营构成 行业地位 研报 同业对标 竞争格局 年报 产能利用率",
            priority,
        )

    if "business" in task_id or "identity" in task_id or "工商" in description or "主体" in description:
        return _task(
            enterprise_name,
            task_id,
            "business",
            f"补充核查{enterprise_name}主体治理缺口：{description}",
            "围绕主体一致性、股权治理、实控人和工商异常线索进行二轮补证。",
            actions or ["工商登记", "实控人", "股权质押", "异常经营", "对外投资"],
            f"{enterprise_name} 工商登记 实控人 股权质押 异常经营 对外投资",
            priority,
        )
    return None


def _from_claim_missing(enterprise_name: str, claim: Dict[str, Any], priority: int) -> ResearchTask | None:
    text = _clean(claim.get("text"), 600)
    task_id = str(claim.get("task_id") or "")
    missing = claim.get("missing_evidence") if isinstance(claim.get("missing_evidence"), list) else []
    missing_text = " ".join(str(item) for item in missing) or " ".join(re.findall(r"\[需补充[:：]([^\]]+)\]", text)[:4])
    if not missing_text:
        return None

    if "financial" in task_id or any(keyword in missing_text for keyword in ["应收", "现金流", "审计", "净利润", "毛利"]):
        return _task(
            enterprise_name,
            task_id,
            "financial",
            f"二轮补证财务待补充项：{_clean(missing_text, 120)}",
            "针对财务诊断中的待补充项追加公开公告和知识库检索。",
            [missing_text],
            f"{enterprise_name} {_clean(missing_text, 120)} 年报 公告 东方财富 巨潮资讯",
            priority,
        )

    if "industry" in task_id or any(keyword in missing_text for keyword in ["行业", "产能", "良率", "同业", "主营"]):
        return _task(
            enterprise_name,
            task_id,
            "industry",
            f"二轮补证行业待补充项：{_clean(missing_text, 120)}",
            "针对行业诊断中的待补充项追加研报、年报和行业知识库检索。",
            [missing_text],
            f"{enterprise_name} {_clean(missing_text, 120)} 研报 年报 行业地位 同业对标",
            priority,
        )
    return None


def build_follow_up_tasks(
    enterprise_name: str,
    tasks: List[ResearchTask],
    gaps: List[ResearchGap],
    claims: List[Dict[str, Any]],
    limit: int = FOLLOW_UP_LIMIT,
) -> List[ResearchTask]:
    """Create at most ``limit`` executable second-round tasks."""
    candidates: List[ResearchTask] = []
    seen_ids = {task.get("id") for task in tasks}

    sorted_gaps = sorted(
        gaps,
        key=lambda item: 0 if item.get("severity") == "high" else 1 if item.get("severity") == "medium" else 2,
    )
    for index, gap in enumerate(sorted_gaps, start=1):
        task = _from_gap(enterprise_name, gap, priority=100 + index)
        if task and task.get("id") not in seen_ids:
            candidates.append(task)
            seen_ids.add(task.get("id"))
        if len(candidates) >= limit:
            return candidates

    for index, claim in enumerate(claims, start=1):
        task = _from_claim_missing(enterprise_name, claim, priority=130 + index)
        if task and task.get("id") not in seen_ids:
            candidates.append(task)
            seen_ids.add(task.get("id"))
        if len(candidates) >= limit:
            return candidates

    return candidates[:limit]
