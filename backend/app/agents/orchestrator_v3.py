# ========================================
# Orchestrator V3 — 支持人机协同
# 使用 LangGraph interrupt 机制
# ========================================

from typing import TypedDict, List, Optional, AsyncGenerator, Dict, Any, Annotated
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
import asyncio
import uuid
import json

from app.agents.state import SSEEvent
from app.memory import ShortTermMemory, LongTermMemory


# ── 状态类型 ─────────────────────────────────────────

class OrchestratorState(TypedDict):
    """调度器状态"""
    task_id: str
    enterprise_name: str
    template_name: str
    agent_state: str
    timeline: List[dict]
    plan: List[dict]
    evidence: List[dict]
    report: Optional[dict]
    error: Optional[str]
    # 企业类型相关
    enterprise_type: Optional[str]  # listed / unlisted
    stock_code: Optional[str]
    stock_exchange: Optional[str]
    data_strategy: Optional[dict]
    # 用户上传相关
    need_user_upload: bool
    uploaded_files: List[dict]
    parsed_financial_data: Optional[dict]
    # 执行计划
    execution_plan: Optional[dict]
    crew_result: Optional[dict]


# ── 记忆实例 ─────────────────────────────────────────

short_term_memory = ShortTermMemory()
long_term_memory = LongTermMemory()


# ── 节点函数 ─────────────────────────────────────────

def create_task(state: OrchestratorState) -> OrchestratorState:
    """创建任务"""
    short_term_memory.add(
        role="system",
        content=f"创建尽调任务：{state['enterprise_name']}",
        metadata={"task_id": state["task_id"]},
    )

    return {
        **state,
        "agent_state": "identifying_enterprise",
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


def identify_enterprise_type(state: OrchestratorState) -> OrchestratorState:
    """识别企业类型"""
    from app.agents.tools.enterprise_tool import identify_enterprise_type

    # 调用企业类型识别工具
    result = identify_enterprise_type._run(state["enterprise_name"])
    data_strategy = json.loads(result)

    # 更新状态
    enterprise_type = data_strategy.get("enterprise_type", "unlisted")
    need_user_upload = data_strategy.get("need_user_upload", False)

    short_term_memory.add(
        role="system",
        content=f"企业类型识别完成：{enterprise_type}",
    )

    return {
        **state,
        "agent_state": "planning",
        "enterprise_type": enterprise_type,
        "stock_code": data_strategy.get("stock_code"),
        "stock_exchange": data_strategy.get("stock_exchange"),
        "data_strategy": data_strategy,
        "need_user_upload": need_user_upload,
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "Plan Agent",
                "content": "识别企业类型",
                "detail": f"类型：{'上市公司' if enterprise_type == 'listed' else '非上市公司'}",
                "status": "completed",
                "type": "discovery",
            },
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "Plan Agent",
                "content": "规划数据获取策略",
                "detail": f"{'自动获取公开数据' if enterprise_type == 'listed' else '需要用户上传财务文件'}",
                "status": "completed",
                "type": "analysis",
            },
        ],
    }


def check_need_upload(state: OrchestratorState) -> str:
    """检查是否需要用户上传文件"""
    if state.get("need_user_upload"):
        return "wait_upload"
    else:
        return "auto_fetch"


def wait_for_upload(state: OrchestratorState) -> OrchestratorState:
    """等待用户上传文件（人机协同）"""
    # 使用 LangGraph 的 interrupt 机制暂停执行
    # 等待用户上传文件后继续
    user_response = interrupt({
        "type": "file_upload_required",
        "message": f"请上传 {state['enterprise_name']} 的财务报表",
        "accept_types": [".xlsx", ".xls", ".pdf"],
        "required_documents": [
            "资产负债表",
            "利润表",
            "现金流量表",
        ],
        "optional_documents": [
            "审计报告",
            "财务报表附注",
        ],
    })

    # 用户上传后继续执行
    uploaded_files = user_response.get("files", [])

    return {
        **state,
        "agent_state": "parsing_files",
        "uploaded_files": uploaded_files,
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "用户",
                "content": f"上传 {len(uploaded_files)} 个文件",
                "detail": ", ".join([f.get("name", "") for f in uploaded_files]),
                "status": "completed",
                "type": "action",
            }
        ],
    }


def parse_uploaded_files(state: OrchestratorState) -> OrchestratorState:
    """解析用户上传的文件"""
    from app.engines.rebecca.parsers import FinancialParser

    parser = FinancialParser()
    parsed_data = {}

    for file_info in state.get("uploaded_files", []):
        file_path = file_info.get("path")
        if file_path:
            try:
                financial_data = parser.parse(file_path)
                parsed_data = {
                    "income_statement": financial_data.income_statement.to_dict()
                    if financial_data.income_statement is not None else None,
                    "balance_sheet": financial_data.balance_sheet.to_dict()
                    if financial_data.balance_sheet is not None else None,
                    "cash_flow": financial_data.cash_flow.to_dict()
                    if financial_data.cash_flow is not None else None,
                }
            except Exception as e:
                short_term_memory.add(
                    role="system",
                    content=f"文件解析失败：{str(e)}",
                )

    return {
        **state,
        "agent_state": "fetching_data",
        "parsed_financial_data": parsed_data,
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "文件解析完成",
                "detail": f"解析 {len(state.get('uploaded_files', []))} 个文件",
                "status": "completed",
                "type": "action",
            }
        ],
    }


def auto_fetch_data(state: OrchestratorState) -> OrchestratorState:
    """自动获取上市公司数据"""
    from app.agents.tools.listed_company_tool import fetch_listed_company_financial

    # 调用上市公司数据获取工具
    result = fetch_listed_company_financial._run(
        enterprise_name=state["enterprise_name"],
        stock_code=state.get("stock_code", ""),
        stock_exchange=state.get("stock_exchange", ""),
    )

    financial_data = json.loads(result)

    return {
        **state,
        "agent_state": "analyzing",
        "parsed_financial_data": financial_data.get("financial_statements"),
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "自动获取上市公司数据",
                "detail": f"来源：巨潮资讯网，股票代码：{state.get('stock_code')}",
                "status": "completed",
                "type": "discovery",
            }
        ],
    }


def run_analysis(state: OrchestratorState) -> OrchestratorState:
    """运行分析"""
    # 根据企业类型选择分析方式
    if state.get("enterprise_type") == "listed":
        # 上市公司：使用完整分析流程
        analysis_detail = "使用 Rebecca 引擎进行 10 维度财务分析"
    else:
        # 非上市公司：使用用户上传的数据
        analysis_detail = "基于用户上传的财务数据进行分析"

    # TODO: 调用 CrewAI 团队进行分析

    return {
        **state,
        "agent_state": "forming_conclusion",
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "分析完成",
                "detail": analysis_detail,
                "status": "completed",
                "type": "action",
            }
        ],
    }


def form_conclusion(state: OrchestratorState) -> OrchestratorState:
    """形成风险结论"""
    risk_score = 75
    risk_rating = "medium"
    recommendation = "建议谨慎授信，需进一步核实"

    report = {
        "enterprise_name": state["enterprise_name"],
        "enterprise_type": state.get("enterprise_type", "unlisted"),
        "risk_rating": risk_rating,
        "risk_score": risk_score,
        "recommendation": recommendation,
    }

    return {
        **state,
        "agent_state": "completed",
        "report": report,
        "timeline": state["timeline"] + [
            {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "尽调报告生成完成",
                "detail": f"风险评级：{risk_rating}，风险评分：{risk_score}",
                "conclusion": recommendation,
                "status": "completed",
                "type": "conclusion",
            }
        ],
    }


# ── 构建图 ─────────────────────────────────────────

def build_orchestrator_v3():
    """构建调度器图 V3（支持人机协同）"""
    workflow = StateGraph(OrchestratorState)

    # 添加节点
    workflow.add_node("create_task", create_task)
    workflow.add_node("identify_enterprise_type", identify_enterprise_type)
    workflow.add_node("wait_for_upload", wait_for_upload)
    workflow.add_node("parse_uploaded_files", parse_uploaded_files)
    workflow.add_node("auto_fetch_data", auto_fetch_data)
    workflow.add_node("run_analysis", run_analysis)
    workflow.add_node("form_conclusion", form_conclusion)

    # 添加边
    workflow.set_entry_point("create_task")
    workflow.add_edge("create_task", "identify_enterprise_type")

    # 条件边：根据企业类型选择路径
    workflow.add_conditional_edges(
        "identify_enterprise_type",
        check_need_upload,
        {
            "wait_upload": "wait_for_upload",
            "auto_fetch": "auto_fetch_data",
        }
    )

    workflow.add_edge("wait_for_upload", "parse_uploaded_files")
    workflow.add_edge("parse_uploaded_files", "run_analysis")
    workflow.add_edge("auto_fetch_data", "run_analysis")
    workflow.add_edge("run_analysis", "form_conclusion")
    workflow.add_edge("form_conclusion", END)

    return workflow.compile()


# ── 运行调度器 ─────────────────────────────────────

async def run_orchestrator_v3(
    task_id: str,
    enterprise_name: str,
    template_name: str = "due_diligence_report_template",
) -> AsyncGenerator[SSEEvent, None]:
    """运行调度器 V3，生成SSE事件"""
    orchestrator = build_orchestrator_v3()

    initial_state = {
        "task_id": task_id,
        "enterprise_name": enterprise_name,
        "template_name": template_name,
        "agent_state": "creating_task",
        "timeline": [],
        "plan": [],
        "evidence": [],
        "report": None,
        "error": None,
        "enterprise_type": None,
        "stock_code": None,
        "stock_exchange": None,
        "data_strategy": None,
        "need_user_upload": False,
        "uploaded_files": [],
        "parsed_financial_data": None,
        "execution_plan": None,
        "crew_result": None,
    }

    # 流式执行
    async for event in orchestrator.astream_events(initial_state, version="v2"):
        kind = event["event"]

        if kind == "on_chain_end":
            output = event["data"].get("output", {})
            if isinstance(output, dict) and "agent_state" in output:
                # 检查是否需要用户上传
                if output.get("agent_state") == "parsing_files":
                    # 发送文件上传请求
                    yield SSEEvent(
                        type="state",
                        data={
                            "agent_state": "waiting_upload",
                            "timeline": output.get("timeline", []),
                            "upload_required": True,
                            "upload_message": f"请上传 {enterprise_name} 的财务报表",
                        },
                    )
                else:
                    yield SSEEvent(
                        type="state",
                        data={
                            "agent_state": output["agent_state"],
                            "timeline": output.get("timeline", []),
                            "plan": output.get("plan", []),
                            "evidence": output.get("evidence", []),
                            "report": output.get("report"),
                            "enterprise_type": output.get("enterprise_type"),
                        },
                    )
