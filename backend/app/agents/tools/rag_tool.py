# ========================================
# RAG 检索工具
# 用于行业Agent检索知识库
# ========================================

from typing import Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json


class SearchIndustryInput(BaseModel):
    """搜索行业知识输入"""
    query: str = Field(description="检索查询")
    knowledge_type: str = Field(default="all", description="知识类型（guide/case/regulation/all）")


class SearchIndustryKnowledgeTool(BaseTool):
    """检索行业知识库工具"""
    name: str = "search_industry_knowledge"
    description: str = "检索行业知识库。当需要获取行业信息时调用此工具。"
    args_schema: Type[BaseModel] = SearchIndustryInput

    def _run(self, query: str, knowledge_type: str = "all") -> str:
        """运行工具"""
        try:
            from app.rag.knowledge_retrieval_service import retrieve_knowledge

            domain = "industry" if knowledge_type in {"guide", "industry"} else "all"
            result = retrieve_knowledge(query=query, domain=domain, top_k=5)

            return json.dumps({
                "success": True,
                "results": result.get("results", []),
                "mode": result.get("mode"),
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "results": []}, ensure_ascii=False)


# 创建工具实例
search_industry_knowledge = SearchIndustryKnowledgeTool()
