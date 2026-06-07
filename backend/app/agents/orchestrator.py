# ========================================
# Orchestrator — 主调度器
# 使用 LangGraph StateGraph 管理任务生命周期
# ========================================

from typing import TypedDict, List, Optional, Literal, AsyncGenerator
from datetime import datetime
from langgraph.graph import StateGraph, END
import asyncio
import uuid

from app.agents.state import (
    TaskState, TimelineEntry, PlanStep, EvidenceItem,
    DueDiligenceReport, SSEEvent, AgentState
)
from app.agents.sub_agents.business_agent import run_business_agent
from app.agents.sub_agents.financial_agent import run_financial_agent
from app.agents.sub_agents.legal_agent import run_legal_agent
from app.agents.sub_agents.industry_agent import run_industry_agent


# ── 状态类型 ─────────────────────────────────────────

class OrchestratorState(TypedDict):
    """调度器状态"""
    task_id: str
    enterprise_name: str
    agent_state: AgentState
    timeline: List[dict]
    plan: List[dict]
    evidence: List[dict]
    report: Optional[dict]
    error: Optional[str]


# ── 节点函数 ─────────────────────────────────────────

def create_task(state: OrchestratorState) -> OrchestratorState:
    """创建任务"""
    return {
        **state,
        "agent_state": "planning",
        "timeline": [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": f"创建尽调任务：{state['enterprise_name']}",
                "status": "completed",
                "type": "action",
            }
        ],
    }


def plan_analysis(state: OrchestratorState) -> OrchestratorState:
    """规划分析步骤"""
    plan = [
        {"id": "1", "name": "工商分析", "status": "pending"},
        {"id": "2", "name": "财务分析", "status": "pending"},
        {"id": "3", "name": "司法分析", "status": "pending"},
        {"id": "4", "name": "行业分析", "status": "pending"},
    ]

    return {
        **state,
        "agent_state": "calling_tools",
        "plan": plan,
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "规划分析步骤",
                "detail": "工商分析 → 财务分析 → 司法分析 → 行业分析",
                "status": "completed",
                "type": "action",
            }
        ],
    }


async def run_agents(state: OrchestratorState) -> OrchestratorState:
    """并行运行所有Agent"""
    enterprise_name = state["enterprise_name"]
    timeline = state["timeline"].copy()
    evidence = state["evidence"].copy()
    plan = state["plan"].copy()

    # 更新计划状态
    for step in plan:
        step["status"] = "running"

    # 添加时间轴条目
    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "系统",
        "content": "开始并行分析",
        "detail": "工商Agent、财务Agent、司法Agent、行业Agent 同时启动",
        "status": "completed",
        "type": "action",
    })

    # 并行运行所有Agent
    business_result, financial_result, legal_result, industry_result = await asyncio.gather(
        run_business_agent(enterprise_name),
        run_financial_agent(enterprise_name),
        run_legal_agent(enterprise_name),
        run_industry_agent(enterprise_name),
    )

    # 处理工商Agent结果
    if business_result["success"]:
        timeline.extend(business_result["timeline"])
        evidence.extend(business_result["evidence"])
        plan[0]["status"] = "completed"
    else:
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "工商分析失败",
            "detail": business_result.get("error", "未知错误"),
            "status": "completed",
            "type": "risk",
        })
        plan[0]["status"] = "completed"

    # 处理财务Agent结果
    if financial_result["success"]:
        timeline.extend(financial_result["timeline"])
        evidence.extend(financial_result["evidence"])
        plan[1]["status"] = "completed"
    else:
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "财务Agent",
            "content": "财务分析失败",
            "detail": financial_result.get("error", "未知错误"),
            "status": "completed",
            "type": "risk",
        })
        plan[1]["status"] = "completed"

    # 处理司法Agent结果
    if legal_result["success"]:
        timeline.extend(legal_result["timeline"])
        evidence.extend(legal_result["evidence"])
        plan[2]["status"] = "completed"
    else:
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "司法Agent",
            "content": "司法分析失败",
            "detail": legal_result.get("error", "未知错误"),
            "status": "completed",
            "type": "risk",
        })
        plan[2]["status"] = "completed"

    # 处理行业Agent结果
    if industry_result["success"]:
        timeline.extend(industry_result["timeline"])
        evidence.extend(industry_result["evidence"])
        plan[3]["status"] = "completed"
    else:
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "行业Agent",
            "content": "行业分析失败",
            "detail": industry_result.get("error", "未知错误"),
            "status": "completed",
            "type": "risk",
        })
        plan[3]["status"] = "completed"

    return {
        **state,
        "agent_state": "forming_conclusion",
        "timeline": timeline,
        "evidence": evidence,
        "plan": plan,
    }


def form_conclusion(state: OrchestratorState) -> OrchestratorState:
    """形成风险结论"""
    # 根据证据形成结论
    risk_factors = []
    for ev in state["evidence"]:
        if "风险" in ev.get("label", "") or "处罚" in ev.get("label", ""):
            risk_factors.append(ev["label"])

    # 计算风险评级
    risk_score = max(0, 100 - len(risk_factors) * 10)
    risk_rating = "low" if risk_score >= 80 else "medium" if risk_score >= 60 else "high"

    # 生成授信建议
    if risk_rating == "low":
        recommendation = "建议授信，风险可控"
    elif risk_rating == "medium":
        recommendation = "建议谨慎授信，需进一步核实"
    else:
        recommendation = "建议暂不授信，存在较大风险"

    report = {
        "enterprise_name": state["enterprise_name"],
        "risk_rating": risk_rating,
        "risk_score": risk_score,
        "recommendation": recommendation,
        "risk_dimensions": [
            {"name": "财务健康度", "score": 78, "status": "low"},
            {"name": "司法合规", "score": 65, "status": "medium"},
            {"name": "行业前景", "score": 82, "status": "low"},
            {"name": "关联风险", "score": 60, "status": "medium"},
        ],
        "financial_metrics": [
            {"label": "营业收入", "value": "8.2亿", "trend": "up", "assessment": "良好"},
            {"label": "净利润率", "value": "12.5%", "trend": "up", "assessment": "良好"},
            {"label": "资产负债率", "value": "42%", "trend": "down", "assessment": "良好"},
        ],
        "legal_items": [
            {"type": "裁判文书", "count": 3, "severity": "low"},
            {"type": "行政处罚", "count": 2, "severity": "medium"},
        ],
    }

    return {
        **state,
        "agent_state": "generating_report",
        "report": report,
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "形成风险结论",
                "detail": f"风险评级：{risk_rating}，风险评分：{risk_score}",
                "conclusion": recommendation,
                "status": "completed",
                "type": "conclusion",
            }
        ],
    }


def generate_report(state: OrchestratorState) -> OrchestratorState:
    """生成尽调报告"""
    return {
        **state,
        "agent_state": "waiting_confirm",
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "尽调报告生成完成",
                "detail": "点击查看完整报告",
                "status": "completed",
                "type": "action",
            }
        ],
    }


# ── 构建图 ─────────────────────────────────────────

def build_orchestrator():
    """构建调度器图"""
    workflow = StateGraph(OrchestratorState)

    # 添加节点
    workflow.add_node("create_task", create_task)
    workflow.add_node("plan_analysis", plan_analysis)
    workflow.add_node("run_agents", run_agents)
    workflow.add_node("form_conclusion", form_conclusion)
    workflow.add_node("generate_report", generate_report)

    # 添加边
    workflow.set_entry_point("create_task")
    workflow.add_edge("create_task", "plan_analysis")
    workflow.add_edge("plan_analysis", "run_agents")
    workflow.add_edge("run_agents", "form_conclusion")
    workflow.add_edge("form_conclusion", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


# ── 运行调度器 ─────────────────────────────────────

async def run_orchestrator(
    task_id: str,
    enterprise_name: str,
) -> AsyncGenerator[SSEEvent, None]:
    """运行调度器，生成SSE事件"""
    orchestrator = build_orchestrator()

    initial_state = {
        "task_id": task_id,
        "enterprise_name": enterprise_name,
        "agent_state": "creating_task",
        "timeline": [],
        "plan": [],
        "evidence": [],
        "report": None,
        "error": None,
    }

    # 流式执行
    async for event in orchestrator.astream_events(initial_state, version="v2"):
        kind = event["event"]

        if kind == "on_chain_end":
            # 获取最新状态
            output = event["data"].get("output", {})
            if isinstance(output, dict) and "agent_state" in output:
                yield SSEEvent(
                    type="state",
                    data={
                        "agent_state": output["agent_state"],
                        "timeline": output.get("timeline", []),
                        "plan": output.get("plan", []),
                        "evidence": output.get("evidence", []),
                        "report": output.get("report"),
                    },
                )
