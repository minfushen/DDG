# ========================================
# Orchestrator V2 — CrewAI + LangGraph 混合架构
# ========================================

from typing import TypedDict, List, Optional, AsyncGenerator, Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
import asyncio
import uuid
import json

from app.agents.state import SSEEvent
from app.memory import ShortTermMemory, LongTermMemory


class Intent(TypedDict):
    type: str  # "full" | "single"
    target: Optional[str]  # None | "business" | "financial" | "legal" | "industry"


class OrchestratorState(TypedDict):
    task_id: str
    enterprise_name: str
    template_name: str
    agent_state: str
    timeline: List[dict]
    plan: List[dict]
    evidence: List[dict]
    report: Optional[dict]
    error: Optional[str]
    execution_plan: Optional[dict]
    crew_result: Optional[dict]
    context: Optional[str]  # 历史上下文（用于多轮对话）
    intent: Optional[Intent]  # 用户意图（用于路由）
    full_due_diligence_context: Optional[dict]  # 完整尽调阶段性上下文


short_term_memory = ShortTermMemory()
long_term_memory = LongTermMemory()


RATE_LIMIT_RETRY_DELAYS = (8, 20, 45)


def is_rate_limit_error(error: Exception) -> bool:
    """判断是否为上游模型限流错误。"""
    error_text = str(error).lower()
    return (
        "ratelimit" in error_text
        or "rate limit" in error_text
        or "too many requests" in error_text
        or "429" in error_text
    )


async def run_node_with_rate_limit_retry(
    node_func,
    state: OrchestratorState,
    label: str,
) -> OrchestratorState:
    """在线程中执行阻塞节点，并对模型限流做退避重试。"""
    last_error: Optional[Exception] = None

    for attempt, delay in enumerate((0, *RATE_LIMIT_RETRY_DELAYS), start=1):
        if delay:
            await asyncio.sleep(delay)

        try:
            return await asyncio.to_thread(node_func, state)
        except Exception as e:
            last_error = e
            if not is_rate_limit_error(e):
                raise
            if attempt > len(RATE_LIMIT_RETRY_DELAYS):
                break

    detail = str(last_error) if last_error else "未知限流错误"
    return {
        **state,
        "agent_state": "forming_conclusion",
        "error": f"{label} 请求过于频繁，已自动重试但仍被上游限流。请稍后重试。",
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": f"{label} 被上游模型限流",
                "detail": detail,
                "status": "completed",
                "type": "risk",
            }
        ],
    }


def create_task(state: OrchestratorState) -> OrchestratorState:
    """创建任务并解析用户意图"""
    intent = parse_intent(state["enterprise_name"])

    short_term_memory.add(
        role="system",
        content=f"创建尽调任务：{state['enterprise_name']}（意图：{intent['type']}）",
        metadata={"task_id": state["task_id"]},
    )

    # 根据意图设置初始状态
    if intent["type"] == "single":
        agent_state = f"calling_{intent['target']}"
        content = f"创建单个任务：{state['enterprise_name']} → {intent['target']}分析"
    else:
        agent_state = "planning"
        content = f"创建尽调任务：{state['enterprise_name']}"

    return {
        **state,
        "agent_state": agent_state,
        "intent": intent,
        "timeline": [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": content,
                "status": "completed",
                "type": "action",
            }
        ],
    }


def parse_intent(enterprise_name: str) -> Intent:
    """解析用户意图，判断是完整尽调还是单个任务

    Args:
        enterprise_name: 用户输入（可能包含意图关键词）

    Returns:
        Intent: {"type": "full" | "single", "target": agent_type | None}
    """
    text = enterprise_name.lower()

    # 关键词映射：agent_type -> 触发关键词列表
    keyword_map = {
        "industry": ["行业风险", "行业情况", "行业分析", "所属行业", "产业", "竞争", "市场", "政策", "景气", "格局", "赛道"],
        "financial": ["财务", "盈利", "现金流", "偿债", "资产负债", "营收", "利润", "毛利率", "roe", "流动比率", "速动比率"],
        "legal": ["司法", "法律", "诉讼", "裁判", "失信", "处罚", "风险", "被执行", "立案"],
        "business": ["工商", "股东", "注册", "法人", "高管", "经营", "变更", "对外投资"],
    }

    for agent_type, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            return {"type": "single", "target": agent_type}

    # 默认：完整尽调
    return {"type": "full", "target": None}


def is_likely_listed_company(enterprise_name: str) -> bool:
    """保守判断是否为已知上市公司。

    真实股票代码解析器接入前，未命中即视为非上市/未知，财务分析需上传。
    """
    from app.agents.tools.listed_company_tool import resolve_listed_company

    return resolve_listed_company(enterprise_name) is not None


def make_upload_required_state(state: OrchestratorState) -> OrchestratorState:
    """生成等待上传近三年财报的状态。"""
    return {
        **state,
        "agent_state": "waiting_upload",
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "等待上传近三年财务报表",
                "detail": "非上市企业财务分析需上传利润表、资产负债表、现金流量表，支持 Excel/CSV",
                "status": "running",
                "type": "action",
            }
        ],
        "error": None,
    }


def run_plan_agent(state: OrchestratorState) -> OrchestratorState:
    try:
        from app.agents.crew.roles import create_plan_agent
        from app.agents.crew.tasks import create_plan_task
        from crewai import Crew, Process

        plan_agent = create_plan_agent(verbose=True)
        plan_task = create_plan_task(
            agent=plan_agent,
            enterprise_name=state["enterprise_name"],
            template_name=state.get("template_name", "due_diligence_report_template"),
        )
        plan_crew = Crew(
            agents=[plan_agent],
            tasks=[plan_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
            max_rpm=3,
        )
        result = plan_crew.kickoff(inputs={
            "enterprise_name": state["enterprise_name"],
            "template_name": state.get("template_name", "due_diligence_report_template"),
            "context": state.get("context", ""),
        })
        execution_plan = parse_execution_plan(str(result))
        short_term_memory.add(
            role="plan_agent",
            content=f"执行计划：{json.dumps(execution_plan, ensure_ascii=False)}",
        )
        return {
            **state,
            "agent_state": "calling_tools",
            "execution_plan": execution_plan,
            "timeline": state["timeline"] + [
                {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "Plan Agent",
                    "content": "读取尽调报告模板",
                    "detail": f"模板：{state.get('template_name', 'due_diligence_report_template')}",
                    "status": "completed",
                    "type": "discovery",
                },
                {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "Plan Agent",
                    "content": "分析业务逻辑",
                    "detail": f"识别到 {len(execution_plan.get('steps', []))} 个执行步骤",
                    "status": "completed",
                    "type": "analysis",
                },
                {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "Plan Agent",
                    "content": "生成执行计划",
                    "detail": f"数据需求：{', '.join(execution_plan.get('data_requirements', []))}",
                    "status": "completed",
                    "type": "action",
                },
            ],
        }
    except Exception as e:
        if is_rate_limit_error(e):
            raise

        default_plan = {
            "steps": [
                {"id": "business_analysis", "name": "工商分析", "agent": "business_agent", "tools": ["search_enterprise_info"], "output": "工商分析报告"},
                {"id": "financial_analysis", "name": "财务分析", "agent": "financial_agent", "tools": ["search_financial_data", "rebecca_analyze"], "output": "财务分析报告"},
                {"id": "legal_analysis", "name": "司法分析", "agent": "legal_agent", "tools": ["search_legal_records"], "output": "司法风险报告"},
                {"id": "industry_analysis", "name": "行业分析", "agent": "industry_agent", "tools": ["search_industry_knowledge"], "output": "行业分析报告"},
            ],
            "data_requirements": ["工商信息", "财务数据", "司法信息", "行业信息"],
            "analysis_requirements": ["盈利能力", "偿债能力", "营运能力", "成长能力", "现金流", "风险评估"],
        }
        return {
            **state,
            "agent_state": "calling_tools",
            "execution_plan": default_plan,
            "error": f"Plan Agent 失败，使用默认计划: {str(e)}",
            "timeline": state["timeline"] + [
                {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "Plan Agent",
                    "content": "规划失败，使用默认计划",
                    "detail": str(e),
                    "status": "completed",
                    "type": "risk",
                }
            ],
        }


def parse_execution_plan(result: str) -> dict:
    default_plan = {
        "steps": [
            {"id": "business_analysis", "name": "工商分析", "agent": "business_agent", "tools": ["search_enterprise_info"], "output": "工商分析报告"},
            {"id": "financial_analysis", "name": "财务分析", "agent": "financial_agent", "tools": ["search_financial_data", "rebecca_analyze"], "output": "财务分析报告"},
            {"id": "legal_analysis", "name": "司法分析", "agent": "legal_agent", "tools": ["search_legal_records"], "output": "司法风险报告"},
            {"id": "industry_analysis", "name": "行业分析", "agent": "industry_agent", "tools": ["search_industry_knowledge"], "output": "行业分析报告"},
        ],
        "data_requirements": ["工商信息", "财务数据", "司法信息", "行业信息"],
        "analysis_requirements": ["盈利能力", "偿债能力", "营运能力", "成长能力", "现金流", "风险评估"],
    }
    try:
        if "{" in result and "}" in result:
            start = result.find("{")
            end = result.rfind("}") + 1
            json_str = result[start:end]
            parsed = json.loads(json_str)
            if "execution_plan" in parsed:
                return parsed["execution_plan"]
            elif "steps" in parsed:
                return parsed
    except:
        pass
    return default_plan


def run_crew(state: OrchestratorState) -> OrchestratorState:
    try:
        from app.agents.crew.full_due_diligence_runner import run_full_due_diligence_sync

        result = run_full_due_diligence_sync(state["enterprise_name"])
        timeline = state["timeline"].copy() + result.get("timeline", [])
        evidence = state["evidence"].copy() + result.get("evidence", [])

        if result.get("fallback_to_upload"):
            return {
                **state,
                "agent_state": "waiting_upload",
                "timeline": timeline,
                "evidence": evidence,
                "report": result.get("report"),
                "error": result.get("error"),
                "full_due_diligence_context": result.get("full_due_diligence_context"),
                "crew_result": {"raw": json.dumps(result.get("report"), ensure_ascii=False)},
            }

        long_term_memory.add(
            category="enterprise",
            title=f"{state['enterprise_name']} 尽调分析",
            content=json.dumps(result.get("report"), ensure_ascii=False),
            metadata={"task_id": state["task_id"]},
        )
        return {
            **state,
            "agent_state": "forming_conclusion",
            "timeline": timeline,
            "evidence": evidence,
            "report": result.get("report"),
            "full_due_diligence_context": result.get("full_due_diligence_context"),
            "crew_result": {"raw": json.dumps(result.get("report"), ensure_ascii=False)},
        }
    except Exception as e:
        if is_rate_limit_error(e):
            raise

        return {
            **state,
            "agent_state": "forming_conclusion",
            "error": f"CrewAI 执行失败: {str(e)}",
            "timeline": state["timeline"] + [
                {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "系统",
                    "content": "CrewAI 执行失败",
                    "detail": str(e),
                    "status": "completed",
                    "type": "risk",
                }
            ],
        }


def run_single_agent(state: OrchestratorState) -> OrchestratorState:
    """执行单个 Agent 任务（用于单个任务模式）。

    单点分析走轻量子 Agent，避免为了一个明确意图启动 CrewAI/LiteLLM 编排。
    """
    from app.agents.sub_agents.business_agent import run_business_agent
    from app.agents.sub_agents.financial_agent import run_financial_agent
    from app.agents.sub_agents.legal_agent import run_legal_agent
    from app.agents.sub_agents.industry_agent import run_industry_agent

    intent = state.get("intent", {})
    target = intent.get("target", "financial")

    agent_runner_map = {
        "business": run_business_agent,
        "financial": run_financial_agent,
        "legal": run_legal_agent,
        "industry": run_industry_agent,
    }
    runner = agent_runner_map.get(target, run_financial_agent)

    result = asyncio.run(runner(state["enterprise_name"]))
    timeline = state["timeline"] + result.get("timeline", [])
    evidence = state["evidence"] + result.get("evidence", [])

    if not result.get("success"):
        if target == "financial" and result.get("fallback_to_upload"):
            return make_upload_required_state({
                **state,
                "timeline": timeline,
                "evidence": evidence,
                "error": result.get("error"),
            })
        return {
            **state,
            "agent_state": "forming_conclusion",
            "error": result.get("error", "单个 Agent 执行失败"),
            "timeline": timeline,
            "evidence": evidence,
        }

    long_term_memory.add(
        category="enterprise",
        title=f"{state['enterprise_name']} {target}分析",
        content=json.dumps(result, ensure_ascii=False),
        metadata={"task_id": state["task_id"]},
    )

    structured_report = (
        result.get("financial_analysis_report")
        or result.get("business_analysis_report")
        or result.get("industry_analysis_report")
        or result.get("legal_analysis_report")
        or state.get("report")
    )

    return {
        **state,
        "agent_state": "forming_conclusion",
        "timeline": timeline,
        "evidence": evidence,
        "report": structured_report,
        "crew_result": {"raw": json.dumps(result, ensure_ascii=False)},
    }


def form_conclusion(state: OrchestratorState) -> OrchestratorState:
    if (state.get("report") or {}).get("report_type") in {"financial_analysis", "business_analysis", "industry_analysis", "legal_analysis", "full_due_diligence"}:
        report = state["report"]
        report_type = report.get("report_type")
        is_financial_report = report_type == "financial_analysis"
        if report_type == "full_due_diligence":
            content = "形成完整尽调综合结论"
            detail = f"风险评级：{report.get('risk_rating')}，评分：{report.get('risk_score')}，维度：{len(report.get('risk_dimensions', []))}个"
            conclusion = report.get("recommendation")
        elif report_type == "business_analysis":
            content = "形成工商分析报告结论"
            detail = f"已抽取 {len(report.get('basic_info', {}))} 个工商字段，来源：{report.get('generated_from', '公开数据')}"
            conclusion = report.get("recommendation") or "工商基础信息已形成字段级来源和置信度说明"
        elif report_type == "industry_analysis":
            industry = report.get("industry", {})
            content = "形成行业分析报告结论"
            detail = f"行业：{industry.get('semantic_industry_name') or industry.get('name')}，置信度：{round((industry.get('confidence') or 0) * 100)}%"
            conclusion = "行业识别、尽调重点、指标阈值和风险提示已由知识库生成"
        elif report_type == "legal_analysis":
            content = "形成司法分析报告结论"
            detail = f"风险评级：{report.get('risk_rating')}，评分：{report.get('risk_score')}，线索：{len(report.get('legal_items', []))}条"
            conclusion = report.get("recommendation")
        else:
            content = "形成财务分析专报结论"
            detail = f"风险评级：{report.get('risk_rating')}，评分：{report.get('risk_score')}"
            conclusion = report.get("recommendation")
        return {
            **state,
            "agent_state": "generating_report",
            "timeline": state["timeline"] + [
                {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "系统",
                    "content": content,
                    "detail": detail,
                    "conclusion": conclusion,
                    "status": "completed",
                    "type": "conclusion",
                }
            ],
        }

    risk_factors = []
    for ev in state["evidence"]:
        if "风险" in ev.get("label", "") or "处罚" in ev.get("label", ""):
            risk_factors.append(ev["label"])
    risk_score = max(0, 100 - len(risk_factors) * 10)
    risk_rating = "low" if risk_score >= 80 else "medium" if risk_score >= 60 else "high"
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
    }
    short_term_memory.add(
        role="system",
        content=f"形成风险结论：{risk_rating}，评分：{risk_score}",
    )
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


def build_orchestrator_v2():
    workflow = StateGraph(OrchestratorState)
    workflow.add_node("create_task", create_task)
    workflow.add_node("run_plan_agent", run_plan_agent)
    workflow.add_node("run_crew", run_crew)
    workflow.add_node("form_conclusion", form_conclusion)
    workflow.add_node("generate_report", generate_report)
    workflow.set_entry_point("create_task")
    workflow.add_edge("create_task", "run_plan_agent")
    workflow.add_edge("run_plan_agent", "run_crew")
    workflow.add_edge("run_crew", "form_conclusion")
    workflow.add_edge("form_conclusion", "generate_report")
    workflow.add_edge("generate_report", END)
    return workflow.compile()


async def run_orchestrator_v2(
    task_id: str,
    enterprise_name: str,
    template_name: str = "due_diligence_report_template",
) -> AsyncGenerator[SSEEvent, None]:
    """运行调度器 V2，实时生成SSE事件

    修复：改为手动逐步执行每个节点，在节点执行前后主动 yield SSE 事件，
    避免 CrewAI 同步阻塞调用导致前端五六分钟收不到任何数据。
    """

    # ── 初始状态 ──
    state: OrchestratorState = {
        "task_id": task_id,
        "enterprise_name": enterprise_name,
        "template_name": template_name,
        "agent_state": "creating_task",
        "timeline": [],
        "plan": [],
        "evidence": [],
        "report": None,
        "error": None,
        "execution_plan": None,
        "crew_result": None,
        "context": None,
        "full_due_diligence_context": None,
    }

    def _make_state_payload(s: OrchestratorState) -> dict:
        """将状态转换为 SSE payload"""
        return {
            "agent_state": s.get("agent_state"),
            "timeline": s.get("timeline", []),
            "plan": s.get("plan", []),
            "evidence": s.get("evidence", []),
            "report": s.get("report"),
            "error": s.get("error"),
            "full_due_diligence_context": s.get("full_due_diligence_context"),
        }

    # ── 步骤1: 创建任务（快速同步节点）──
    yield SSEEvent(type="state", data=_make_state_payload(state))

    state = create_task(state)
    yield SSEEvent(type="state", data=_make_state_payload(state))

    # ── 步骤2 & 3: 根据意图选择执行路径 ──
    intent = state.get("intent", {"type": "full"})

    # 注入历史上下文（支持多轮对话）
    state["context"] = short_term_memory.get_context(max_tokens=2000)

    if intent["type"] == "full":
        # 完整尽调：Plan Agent → 全 Crew
        yield SSEEvent(
            type="state",
            data={
                **_make_state_payload(state),
                "timeline": state.get("timeline", [])
                + [
                    {
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "Plan Agent",
                        "content": "正在读取尽调模板并规划分析步骤...",
                        "status": "running",
                        "type": "action",
                    }
                ],
            },
        )
        state = await run_node_with_rate_limit_retry(run_plan_agent, state, "Plan Agent")
        yield SSEEvent(type="state", data=_make_state_payload(state))

        yield SSEEvent(
            type="state",
            data={
                **_make_state_payload(state),
                "timeline": state.get("timeline", [])
                + [
                    {
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "系统",
                        "content": "启动 CrewAI 分析团队，执行工商/财务/司法/行业分析...",
                        "status": "running",
                        "type": "action",
                    }
                ],
            },
        )
        state = await run_node_with_rate_limit_retry(run_crew, state, "CrewAI 团队执行")
        yield SSEEvent(type="state", data=_make_state_payload(state))

        if state.get("agent_state") == "waiting_upload":
            return

    else:
        # 单个任务：直接执行目标 Agent
        target = intent.get("target", "financial")
        if target == "financial" and not is_likely_listed_company(state["enterprise_name"]):
            state = make_upload_required_state(state)
            yield SSEEvent(type="state", data=_make_state_payload(state))
            return

        yield SSEEvent(
            type="state",
            data={
                **_make_state_payload(state),
                "timeline": state.get("timeline", [])
                + [
                    {
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "系统",
                        "content": f"执行单个任务：{target}分析",
                        "detail": f"跳过完整流程，直接分析 {state['enterprise_name']} 的{target}信息",
                        "status": "running",
                        "type": "action",
                    }
                ],
            },
        )
        state = await run_node_with_rate_limit_retry(run_single_agent, state, "单个 Agent 执行")
        yield SSEEvent(type="state", data=_make_state_payload(state))

    # ── 步骤4: 形成结论（快速同步节点）──
    state = form_conclusion(state)
    yield SSEEvent(type="state", data=_make_state_payload(state))

    # ── 步骤5: 生成报告（快速同步节点）──
    state = generate_report(state)
    yield SSEEvent(type="state", data=_make_state_payload(state))

    # ── 完成 ──
    yield SSEEvent(type="state", data={"agent_state": "completed"})
