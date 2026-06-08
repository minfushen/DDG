# ========================================
# Crew 定义
# ========================================

from crewai import Crew, Process
from typing import Optional, Dict, Any

from .roles import (
    create_plan_agent,
    create_business_agent,
    create_financial_agent,
    create_legal_agent,
    create_industry_agent,
)
from .tasks import (
    create_plan_task,
    create_business_task,
    create_financial_task,
    create_legal_task,
    create_industry_task,
)


def create_due_diligence_crew(
    enterprise_name: str,
    template_name: str = "due_diligence_report_template",
    llm: Optional[str] = None,
    verbose: bool = True,
    memory: bool = True,
    context: str = "",
) -> Crew:
    """创建尽调团队（带 Plan Agent）

    Args:
        enterprise_name: 企业名称
        template_name: 模板名称
        llm: LLM 模型名称
        verbose: 是否显示详细信息
        memory: 是否启用记忆
        context: 历史上下文（用于多轮对话）

    Returns:
        Crew: 尽调团队
    """
    # 创建 Plan Agent
    plan_agent = create_plan_agent(llm=llm, verbose=verbose)

    # 创建其他 Agent
    business_agent = create_business_agent(llm=llm, verbose=verbose)
    financial_agent = create_financial_agent(llm=llm, verbose=verbose)
    legal_agent = create_legal_agent(llm=llm, verbose=verbose)
    industry_agent = create_industry_agent(llm=llm, verbose=verbose)

    # 创建规划任务
    plan_task = create_plan_task(
        agent=plan_agent,
        enterprise_name=enterprise_name,
        template_name=template_name,
        context=context,
    )

    # 创建执行任务（暂时不传入计划，后续会根据计划动态调整）
    business_task = create_business_task(
        agent=business_agent,
        enterprise_name=enterprise_name,
        context=context,
    )
    financial_task = create_financial_task(
        agent=financial_agent,
        enterprise_name=enterprise_name,
        context=context,
    )
    legal_task = create_legal_task(
        agent=legal_agent,
        enterprise_name=enterprise_name,
        context=context,
    )
    industry_task = create_industry_task(
        agent=industry_agent,
        enterprise_name=enterprise_name,
        context=context,
    )

    # 创建团队
    crew = Crew(
        agents=[plan_agent, business_agent, financial_agent, legal_agent, industry_agent],
        tasks=[plan_task, business_task, financial_task, legal_task, industry_task],
        process=Process.sequential,  # 顺序执行：先规划，再执行
        verbose=verbose,
        memory=memory,
        max_rpm=3,  # 完整尽调会连续调用多个 Agent，低速率更不容易触发上游限流
        language="zh",  # 中文
    )

    return crew


def create_dynamic_crew(
    enterprise_name: str,
    execution_plan: Dict[str, Any],
    llm: Optional[str] = None,
    verbose: bool = True,
    memory: bool = True,
    context: str = "",
) -> Crew:
    """根据执行计划创建动态尽调团队

    Args:
        enterprise_name: 企业名称
        execution_plan: 执行计划
        llm: LLM 模型名称
        verbose: 是否显示详细信息
        memory: 是否启用记忆
        context: 历史上下文（用于多轮对话）

    Returns:
        Crew: 动态尽调团队
    """
    # 创建所有 Agent
    business_agent = create_business_agent(llm=llm, verbose=verbose)
    financial_agent = create_financial_agent(llm=llm, verbose=verbose)
    legal_agent = create_legal_agent(llm=llm, verbose=verbose)
    industry_agent = create_industry_agent(llm=llm, verbose=verbose)

    # Agent 映射
    agent_map = {
        "business_agent": business_agent,
        "financial_agent": financial_agent,
        "legal_agent": legal_agent,
        "industry_agent": industry_agent,
    }

    # 根据执行计划创建任务
    tasks = []
    agents = []

    for step in execution_plan.get("steps", []):
        agent_name = step.get("agent")
        if agent_name in agent_map:
            agent = agent_map[agent_name]
            agents.append(agent)

            # 根据步骤类型创建任务
            if step["id"] == "business_analysis":
                task = create_business_task(
                    agent=agent,
                    enterprise_name=enterprise_name,
                    plan=execution_plan,
                    context=context,
                )
            elif step["id"] == "financial_analysis":
                task = create_financial_task(
                    agent=agent,
                    enterprise_name=enterprise_name,
                    plan=execution_plan,
                    context=context,
                )
            elif step["id"] == "legal_analysis":
                task = create_legal_task(
                    agent=agent,
                    enterprise_name=enterprise_name,
                    plan=execution_plan,
                    context=context,
                )
            elif step["id"] == "industry_analysis":
                task = create_industry_task(
                    agent=agent,
                    enterprise_name=enterprise_name,
                    plan=execution_plan,
                    context=context,
                )
            else:
                continue

            tasks.append(task)

    # 去重 Agent
    unique_agents = list({a.role: a for a in agents}.values())

    # 创建团队
    crew = Crew(
        agents=unique_agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
        memory=memory,
        max_rpm=3,
        language="zh",
    )

    return crew
