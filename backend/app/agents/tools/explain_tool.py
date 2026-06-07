# backend/app/agents/tools/explain_tool.py
"""指标解读工具"""
from langchain_core.tools import tool


@tool
def explain_analysis_result(
    indicator_name: str,
    indicator_value: float,
    industry_average: float,
    trend: str,
) -> str:
    """对财务分析指标进行专业解读。

    当用户询问某个指标含义、为什么变化时调用此工具。

    Args:
        indicator_name: 指标名称（如"毛利率"、"流动比率"）
        indicator_value: 当前指标值
        industry_average: 行业平均值
        trend: 趋势描述（如"上升"、"下降"、"稳定"）
    """
    # 此工具实际上是让 LLM 基于知识库进行解读
    # 返回提示词，让 Agent 结合 RAG 检索结果生成解读
    return f"""请基于以下信息对 {indicator_name} 进行专业解读：
- 当前值：{indicator_value}
- 行业平均：{industry_average}
- 趋势：{trend}

请从以下角度分析：
1. 该指标的含义和计算方法
2. 当前值与行业水平的对比
3. 趋势变化的可能原因
4. 对企业经营的影响
5. 风险提示或建议"""
