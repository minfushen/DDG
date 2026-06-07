# ========================================
# 企业类型识别工具
# 用于判断企业是上市公司还是非上市公司
# ========================================

from typing import Type, Optional, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json


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
        # TODO: 接入真实的上市公司查询API
        # 目前通过关键词判断

        # 上市公司关键词（常见上市公司）
        listed_companies = {
            "腾讯": {"stock_code": "0700.HK", "stock_exchange": "港交所"},
            "阿里巴巴": {"stock_code": "BABA", "stock_exchange": "纽交所"},
            "百度": {"stock_code": "BIDU", "stock_exchange": "纳斯达克"},
            "京东": {"stock_code": "JD", "stock_exchange": "纳斯达克"},
            "美团": {"stock_code": "3690.HK", "stock_exchange": "港交所"},
            "小米": {"stock_code": "1810.HK", "stock_exchange": "港交所"},
            "华为": {"stock_code": None, "stock_exchange": None},  # 非上市
            "字节跳动": {"stock_code": None, "stock_exchange": None},  # 非上市
        }

        # 判断是否为上市公司
        is_listed = False
        stock_code = None
        stock_exchange = None

        for company, info in listed_companies.items():
            if company in enterprise_name:
                if info["stock_code"]:
                    is_listed = True
                    stock_code = info["stock_code"]
                    stock_exchange = info["stock_exchange"]
                break

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
