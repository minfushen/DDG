# ========================================
# Plan Agent 工具
# 用于读取尽调报告模板和分析业务逻辑
# ========================================

from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json


class ReadReportTemplateInput(BaseModel):
    """读取报告模板输入"""
    template_name: str = Field(
        default="due_diligence_report_template",
        description="模板名称"
    )


class AnalyzeTemplateInput(BaseModel):
    """分析模板输入"""
    template_content: str = Field(description="模板内容")


class ReadReportTemplateTool(BaseTool):
    """读取尽调报告模板工具"""
    name: str = "read_report_template"
    description: str = "读取知识库中的尽调报告模板。当需要了解尽调报告的结构和要求时调用此工具。"
    args_schema: Type[BaseModel] = ReadReportTemplateInput

    def _run(self, template_name: str = "due_diligence_report_template") -> str:
        """运行工具"""
        try:
            from app.config import settings
            from app.config.embedding_config import get_embedding_model
            from app.rag import VectorStoreManager, KnowledgeBase, KnowledgeRetriever

            # 初始化 RAG 组件
            embedding_model = get_embedding_model()
            manager = VectorStoreManager(embedding_model)
            kb = KnowledgeBase(manager)
            retriever = KnowledgeRetriever(kb)

            # 检索模板
            result = retriever.search_formatted(
                query=f"{template_name} 尽调报告模板",
                knowledge_type="template",
                top_k=3,
            )

            return json.dumps({
                "success": True,
                "template_name": template_name,
                "content": result,
            }, ensure_ascii=False)

        except Exception as e:
            # 降级方案：返回默认模板
            default_template = {
                "success": True,
                "template_name": template_name,
                "content": """# 尽调报告模板

## 一、企业基本信息
- 企业名称
- 统一社会信用代码
- 注册资本
- 成立日期
- 经营范围

## 二、股东与关联关系
- 股东结构
- 关联企业
- 实际控制人

## 三、财务分析
- 盈利能力
- 偿债能力
- 营运能力
- 成长能力
- 现金流分析

## 四、司法风险
- 裁判文书
- 行政处罚
- 失信被执行

## 五、行业分析
- 行业概况
- 竞争格局
- 政策环境

## 六、风险评估
- 风险维度
- 风险评级
- 风险提示

## 七、授信建议
- 授信额度
- 授信期限
- 担保要求
- 风险控制措施""",
            }

            return json.dumps(default_template, ensure_ascii=False)


class AnalyzeTemplateRequirementsTool(BaseTool):
    """分析模板要求工具"""
    name: str = "analyze_template_requirements"
    description: str = "分析尽调报告模板的业务逻辑和输出要求。当需要理解模板需要哪些数据和分析时调用此工具。"
    args_schema: Type[BaseModel] = AnalyzeTemplateInput

    def _run(self, template_content: str) -> str:
        """运行工具"""
        # 分析模板内容，提取业务逻辑和输出要求
        requirements = {
            "sections": [],
            "data_requirements": [],
            "analysis_requirements": [],
            "output_format": {},
        }

        # 解析模板内容
        lines = template_content.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 识别章节
            if line.startswith("#"):
                section_name = line.lstrip("#").strip()
                current_section = section_name
                requirements["sections"].append(section_name)

            # 识别数据要求
            elif "企业名称" in line or "统一社会信用代码" in line:
                requirements["data_requirements"].append("工商信息")
            elif "财务" in line or "盈利" in line or "偿债" in line:
                requirements["data_requirements"].append("财务数据")
            elif "司法" in line or "裁判" in line or "处罚" in line:
                requirements["data_requirements"].append("司法信息")
            elif "行业" in line or "竞争" in line or "政策" in line:
                requirements["data_requirements"].append("行业信息")

            # 识别分析要求
            elif "盈利能力" in line:
                requirements["analysis_requirements"].append("盈利能力分析")
            elif "偿债能力" in line:
                requirements["analysis_requirements"].append("偿债能力分析")
            elif "营运能力" in line:
                requirements["analysis_requirements"].append("营运能力分析")
            elif "成长能力" in line:
                requirements["analysis_requirements"].append("成长能力分析")
            elif "现金流" in line:
                requirements["analysis_requirements"].append("现金流分析")
            elif "风险评估" in line:
                requirements["analysis_requirements"].append("风险评估")
            elif "授信建议" in line:
                requirements["analysis_requirements"].append("授信建议")

        # 去重
        requirements["data_requirements"] = list(set(requirements["data_requirements"]))
        requirements["analysis_requirements"] = list(set(requirements["analysis_requirements"]))

        # 生成执行计划
        execution_plan = generate_execution_plan(requirements)

        return json.dumps({
            "success": True,
            "requirements": requirements,
            "execution_plan": execution_plan,
        }, ensure_ascii=False, indent=2)


def generate_execution_plan(requirements: dict) -> dict:
    """根据需求生成执行计划

    Args:
        requirements: 需求分析结果

    Returns:
        dict: 执行计划
    """
    plan = {
        "steps": [],
        "parallel_groups": [],
        "dependencies": {},
    }

    # 根据数据需求添加步骤
    data_reqs = requirements.get("data_requirements", [])

    if "工商信息" in data_reqs:
        plan["steps"].append({
            "id": "business_analysis",
            "name": "工商分析",
            "agent": "business_agent",
            "tools": ["search_enterprise_info"],
            "output": "工商分析报告",
        })

    if "财务数据" in data_reqs:
        plan["steps"].append({
            "id": "financial_analysis",
            "name": "财务分析",
            "agent": "financial_agent",
            "tools": ["search_financial_data", "rebecca_analyze"],
            "output": "财务分析报告",
        })

    if "司法信息" in data_reqs:
        plan["steps"].append({
            "id": "legal_analysis",
            "name": "司法分析",
            "agent": "legal_agent",
            "tools": ["search_legal_records"],
            "output": "司法风险报告",
        })

    if "行业信息" in data_reqs:
        plan["steps"].append({
            "id": "industry_analysis",
            "name": "行业分析",
            "agent": "industry_agent",
            "tools": ["search_industry_knowledge"],
            "output": "行业分析报告",
        })

    # 添加结论步骤
    plan["steps"].append({
        "id": "conclusion",
        "name": "形成结论",
        "agent": "plan_agent",
        "tools": [],
        "output": "风险评估和授信建议",
        "depends_on": [s["id"] for s in plan["steps"]],
    })

    # 定义并行组（可以并行执行的步骤）
    parallel_steps = [s["id"] for s in plan["steps"] if s["id"] != "conclusion"]
    if len(parallel_steps) > 1:
        plan["parallel_groups"].append(parallel_steps)

    return plan


# 创建工具实例
read_report_template = ReadReportTemplateTool()
analyze_template_requirements = AnalyzeTemplateRequirementsTool()
