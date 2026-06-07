# ========================================
# 任务定义
# ========================================

from crewai import Task, Agent
from typing import Optional


def create_plan_task(
    agent: Agent,
    enterprise_name: str,
    template_name: str = "due_diligence_report_template",
    context: Optional[str] = None,
) -> Task:
    """创建规划任务

    Args:
        agent: Plan Agent
        enterprise_name: 企业名称
        template_name: 模板名称
        context: 历史上下文（用于多轮对话）

    Returns:
        Task: 规划任务
    """
    desc = f"""分析 {enterprise_name} 的尽调报告模板，规划执行流程。

任务步骤：
1. 使用 read_report_template 工具读取尽调报告模板
2. 分析模板的结构和要求
3. 识别需要的数据和分析类型
4. 使用 analyze_template_requirements 工具分析业务逻辑
5. 输出完整的执行计划

输出要求：
- 列出所有需要的数据类型
- 列出所有需要的分析类型
- 定义执行步骤和依赖关系
- 指定每个步骤的Agent和工具"""

    if context:
        desc += f"\n\n【历史上下文】\n{context}"

    return Task(
        description=desc,
        expected_output="""执行计划，包含：
1. 数据需求列表（工商、财务、司法、行业）
2. 分析需求列表（盈利能力、偿债能力等）
3. 执行步骤和依赖关系
4. 每个步骤的Agent和工具分配""",
        agent=agent,
        output_file="execution_plan.md",
    )


def create_business_task(
    agent: Agent,
    enterprise_name: str,
    plan: Optional[dict] = None,
    context: Optional[str] = None,
) -> Task:
    """创建工商分析任务

    Args:
        agent: 工商分析 Agent
        enterprise_name: 企业名称
        plan: 执行计划（可选）
        context: 历史上下文（用于多轮对话）

    Returns:
        Task: 工商分析任务
    """
    # 根据计划调整任务描述
    plan_desc = ""
    if plan:
        business_step = next(
            (s for s in plan.get("steps", []) if s["id"] == "business_analysis"),
            None
        )
        if business_step:
            plan_desc = f"\n\n根据执行计划，需要输出：{business_step.get('output', '工商分析报告')}"

    desc = f"""获取并分析 {enterprise_name} 的工商信息。

分析维度：
1. 基本信息（统一社会信用代码、注册资本、成立日期）
2. 股东结构（股东信息、持股比例）
3. 高管信息（法定代表人、主要高管）
4. 经营范围（主营业务、资质许可）
5. 对外投资（关联企业、投资关系）
6. 风险提示（异常变更、行政处罚）

请使用 search_enterprise_info 工具获取工商信息，并进行详细分析。{plan_desc}"""

    if context:
        desc += f"\n\n【历史上下文】\n{context}"

    return Task(
        description=desc,
        expected_output="""工商分析报告，包含：
1. 基本信息摘要
2. 股东结构分析
3. 高管信息分析
4. 经营范围分析
5. 关联企业分析
6. 风险提示""",
        agent=agent,
        output_file="business_analysis.md",
    )


def create_financial_task(
    agent: Agent,
    enterprise_name: str,
    plan: Optional[dict] = None,
    context: Optional[str] = None,
) -> Task:
    """创建财务分析任务

    Args:
        agent: 财务分析 Agent
        enterprise_name: 企业名称
        plan: 执行计划（可选）
        context: 历史上下文（用于多轮对话）

    Returns:
        Task: 财务分析任务
    """
    # 根据计划调整任务描述
    plan_desc = ""
    if plan:
        financial_step = next(
            (s for s in plan.get("steps", []) if s["id"] == "financial_analysis"),
            None
        )
        if financial_step:
            plan_desc = f"\n\n根据执行计划，需要输出：{financial_step.get('output', '财务分析报告')}"

    desc = f"""使用 Rebecca 引擎对 {enterprise_name} 进行 10 维度财务分析。

分析维度：
1. 盈利能力（毛利率、净利率、ROE）
2. 偿债能力（流动比率、速动比率、资产负债率）
3. 营运能力（应收账款周转、存货周转）
4. 成长能力（营收增长率、利润增长率）
5. 现金流分析（经营现金流、投资现金流）
6. 成本结构（成本构成、费用控制）
7. 资产质量（资产构成、减值风险）
8. 负债结构（负债构成、偿债压力）
9. 盈利趋势（盈利稳定性、可持续性）
10. 风险评估（综合风险评级）

请使用 search_financial_data 工具获取财务数据，然后使用 rebecca_analyze 工具进行深度分析。{plan_desc}"""

    if context:
        desc += f"\n\n【历史上下文】\n{context}"

    return Task(
        description=desc,
        expected_output="""财务分析报告，包含：
1. 10维度分析结果
2. 关键指标解读
3. 风险识别
4. 趋势分析
5. 综合评价""",
        agent=agent,
        output_file="financial_analysis.md",
    )


def create_legal_task(
    agent: Agent,
    enterprise_name: str,
    plan: Optional[dict] = None,
    context: Optional[str] = None,
) -> Task:
    """创建司法分析任务

    Args:
        agent: 司法分析 Agent
        enterprise_name: 企业名称
        plan: 执行计划（可选）
        context: 历史上下文（用于多轮对话）

    Returns:
        Task: 司法分析任务
    """
    # 根据计划调整任务描述
    plan_desc = ""
    if plan:
        legal_step = next(
            (s for s in plan.get("steps", []) if s["id"] == "legal_analysis"),
            None
        )
        if legal_step:
            plan_desc = f"\n\n根据执行计划，需要输出：{legal_step.get('output', '司法风险报告')}"

    desc = f"""分析 {enterprise_name} 的司法风险。

分析维度：
1. 裁判文书（涉诉情况）
2. 行政处罚（处罚记录）
3. 失信被执行人（执行情况）
4. 股权出质（质押情况）

请使用 search_legal_records 工具获取司法信息，并进行详细分析。{plan_desc}"""

    if context:
        desc += f"\n\n【历史上下文】\n{context}"

    return Task(
        description=desc,
        expected_output="""司法风险分析报告，包含：
1. 裁判文书分析
2. 行政处罚分析
3. 失信被执行人分析
4. 股权出质分析
5. 风险评级""",
        agent=agent,
        output_file="legal_analysis.md",
    )


def create_industry_task(
    agent: Agent,
    enterprise_name: str,
    plan: Optional[dict] = None,
    context: Optional[str] = None,
) -> Task:
    """创建行业分析任务

    Args:
        agent: 行业分析 Agent
        enterprise_name: 企业名称
        plan: 执行计划（可选）
        context: 历史上下文（用于多轮对话）

    Returns:
        Task: 行业分析任务
    """
    # 根据计划调整任务描述
    plan_desc = ""
    if plan:
        industry_step = next(
            (s for s in plan.get("steps", []) if s["id"] == "industry_analysis"),
            None
        )
        if industry_step:
            plan_desc = f"\n\n根据执行计划，需要输出：{industry_step.get('output', '行业分析报告')}"

    desc = f"""使用知识库对 {enterprise_name} 所在行业进行分析。

分析维度：
1. 行业概况（规模、增长率）
2. 行业景气度（周期、趋势）
3. 竞争格局（主要玩家、市场份额）
4. 政策环境（支持政策、监管趋势）
5. 风险提示（行业风险、技术风险）

请使用 search_industry_knowledge 工具检索行业知识，并进行详细分析。{plan_desc}"""

    if context:
        desc += f"\n\n【历史上下文】\n{context}"

    return Task(
        description=desc,
        expected_output="""行业分析报告，包含：
1. 行业概况
2. 行业景气度分析
3. 竞争格局分析
4. 政策环境分析
5. 风险提示""",
        agent=agent,
        output_file="industry_analysis.md",
    )
