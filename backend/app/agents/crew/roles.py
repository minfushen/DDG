# ========================================
# Agent 角色定义
# ========================================

from crewai import Agent
from typing import Optional

from app.agents.tools.search_tool import (
    search_enterprise_info,
    search_legal_records,
    search_financial_data,
)
from app.agents.tools.rag_tool import search_industry_knowledge
from app.agents.tools.rebecca_tool import rebecca_analyze
from app.agents.tools.plan_tool import (
    read_report_template,
    analyze_template_requirements,
)
from app.config import settings


# ── 注册 Xiaomi Mimo 模型到 Litellm ──────────────────
# 绕过 CrewAI/Litellm 的模型白名单限制

try:
    import litellm
    litellm.register_model({
        "openai/mimo-v2.5-pro": {
            "max_tokens": 8192,
            "max_input_tokens": 128000,
            "max_output_tokens": 8192,
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
            "litellm_provider": "openai",
            "mode": "chat",
        }
    })
except Exception:
    pass


def get_default_llm() -> str:
    """获取默认 LLM 配置（CrewAI 使用字符串格式）"""
    return "openai/mimo-v2.5-pro"


def create_plan_agent(
    llm: Optional[str] = None,
    verbose: bool = True,
) -> Agent:
    """创建 Plan Agent"""
    return Agent(
        role="尽调流程规划专家",
        goal="读取尽调报告模板，分析业务逻辑，动态规划执行流程",
        backstory="""你是一位资深的尽调流程规划专家，擅长理解尽调报告模板的结构和要求，分析模板中的业务逻辑，规划最优的执行流程。

你的工作流程：
1. 首先读取知识库中的尽调报告模板
2. 分析模板需要哪些数据和分析
3. 规划执行步骤
4. 输出完整的执行计划""",
        tools=[read_report_template, analyze_template_requirements],
        llm=llm or get_default_llm(),
        verbose=verbose,
        allow_delegation=False,
        max_iter=3,
        memory=False,
    )


def create_business_agent(
    llm: Optional[str] = None,
    verbose: bool = True,
) -> Agent:
    """创建工商分析 Agent"""
    return Agent(
        role="工商分析专家",
        goal="获取并分析企业工商信息，识别股东结构和关联关系",
        backstory="""你是一位专业的工商分析专家，擅长从工商登记信息中识别企业风险。你总是基于数据说话，关注异常变更和风险信号。""",
        tools=[search_enterprise_info],
        llm=llm or get_default_llm(),
        verbose=verbose,
        allow_delegation=False,
        max_iter=3,
        memory=False,
    )


def create_financial_agent(
    llm: Optional[str] = None,
    verbose: bool = True,
) -> Agent:
    """创建财务分析 Agent"""
    return Agent(
        role="财务分析专家",
        goal="使用 Rebecca 引擎进行深度财务分析，识别财务风险",
        backstory="""你是一位资深的财务分析专家，擅长使用 Rebecca 引擎进行 10 维度财务分析。你总是基于数据说话，引用具体指标进行分析。""",
        tools=[search_financial_data, rebecca_analyze],
        llm=llm or get_default_llm(),
        verbose=verbose,
        allow_delegation=False,
        max_iter=3,
        memory=False,
    )


def create_legal_agent(
    llm: Optional[str] = None,
    verbose: bool = True,
) -> Agent:
    """创建司法分析 Agent"""
    return Agent(
        role="司法风险分析专家",
        goal="获取并分析企业司法风险，识别法律风险",
        backstory="""你是一位司法风险分析专家，擅长从司法公开数据中识别企业风险。你总是基于数据说话，引用具体案例进行分析。""",
        tools=[search_legal_records],
        llm=llm or get_default_llm(),
        verbose=verbose,
        allow_delegation=False,
        max_iter=3,
        memory=False,
    )


def create_industry_agent(
    llm: Optional[str] = None,
    verbose: bool = True,
) -> Agent:
    """创建行业分析 Agent"""
    return Agent(
        role="行业分析专家",
        goal="使用知识库进行行业分析，评估行业风险和机会",
        backstory="""你是一位行业分析专家，擅长使用知识库进行行业研究。你总是基于数据说话，引用行业报告和政策文件进行分析。""",
        tools=[search_industry_knowledge],
        llm=llm or get_default_llm(),
        verbose=verbose,
        allow_delegation=False,
        max_iter=3,
        memory=False,
    )
