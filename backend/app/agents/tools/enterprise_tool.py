# ========================================
# 企业类型识别工具
# 用于判断企业是上市公司还是非上市公司
# ========================================

from typing import Type, Optional, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json

from app.agents.tools.listed_company_tool import resolve_listed_company


class IdentifyEnterpriseTypeInput(BaseModel):
    """识别企业类型输入"""
    enterprise_name: str = Field(description="企业名称")


class IdentifyEnterpriseTypeTool(BaseTool):
    """识别企业类型工具"""
    name: str = "identify_enterprise_type"
    description: str = """识别企业是上市公司还是非上市公司。

返回信息：
- enterprise_type: "listed"（上市公司）或 "unlisted"（非上市公司）
- stock_code: 股票代码（上市公司）
- stock_exchange: 上市交易所（上市公司）
- data_strategy: 数据获取策略
"""
    args_schema: Type[BaseModel] = IdentifyEnterpriseTypeInput

    def _run(self, enterprise_name: str) -> str:
        """运行工具"""
        listed_info = resolve_listed_company(enterprise_name)
        is_listed = listed_info is not None
        stock_code = listed_info.get("stock_code") if listed_info else None
        stock_exchange = listed_info.get("stock_exchange") if listed_info else None

        # 根据企业类型确定数据获取策略
        if is_listed:
            data_strategy = {
                "enterprise_type": "listed",
                "stock_code": stock_code,
                "stock_exchange": stock_exchange,
                "data_sources": {
                    "business_info": [
                        {"source": "tavily_search", "description": "Tavily搜索获取工商信息"},
                        {"source": "baidu_search", "description": "百度搜索获取企业信息"},
                    ],
                    "financial_info": [
                        {"source": "cninfo", "description": "巨潮资讯网获取年报/财报"},
                        {"source": "eastmoney", "description": "东方财富获取财务数据"},
                        {"source": "tonghuashun", "description": "同花顺获取财务数据"},
                    ],
                    "industry_info": [
                        {"source": "rag_knowledge", "description": "知识库检索行业信息"},
                    ],
                },
                "auto_fetch": True,
                "need_user_upload": False,
            }
        else:
            data_strategy = {
                "enterprise_type": "unlisted",
                "stock_code": None,
                "stock_exchange": None,
                "data_sources": {
                    "business_info": [
                        {"source": "tavily_search", "description": "Tavily搜索获取工商信息"},
                        {"source": "baidu_search", "description": "百度搜索获取企业信息"},
                    ],
                    "financial_info": [
                        {"source": "user_upload", "description": "用户上传财务报表"},
                    ],
                    "industry_info": [
                        {"source": "rag_knowledge", "description": "知识库检索行业信息"},
                    ],
                },
                "auto_fetch": False,
                "need_user_upload": True,
                "upload_requirements": {
                    "file_types": [".xlsx", ".xls", ".pdf"],
                    "required_documents": [
                        "资产负债表",
                        "利润表",
                        "现金流量表",
                    ],
                    "optional_documents": [
                        "审计报告",
                        "财务报表附注",
                    ],
                },
            }

        return json.dumps(data_strategy, ensure_ascii=False, indent=2)


# 创建工具实例
identify_enterprise_type = IdentifyEnterpriseTypeTool()
