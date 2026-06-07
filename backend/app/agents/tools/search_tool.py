# ========================================
# 联网搜索工具
# 用于工商Agent和司法Agent
# ========================================

from typing import Optional, Dict, Any, List, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json


class SearchEnterpriseInput(BaseModel):
    """搜索企业信息输入"""
    enterprise_name: str = Field(description="企业名称")


class SearchLegalInput(BaseModel):
    """搜索司法信息输入"""
    enterprise_name: str = Field(description="企业名称")


class SearchFinancialInput(BaseModel):
    """搜索财务数据输入"""
    enterprise_name: str = Field(description="企业名称")


class SearchEnterpriseInfoTool(BaseTool):
    """搜索企业工商信息工具"""
    name: str = "search_enterprise_info"
    description: str = "搜索企业工商信息。当需要获取企业基本信息时调用此工具。"
    args_schema: Type[BaseModel] = SearchEnterpriseInput

    def _run(self, enterprise_name: str) -> str:
        """运行工具"""
        # TODO: 接入真实的工商信息API（如天眼查、企查查）
        # 目前返回模拟数据
        mock_data = {
            "企业名称": enterprise_name,
            "统一社会信用代码": "91110108MA0XXXXXX",
            "法定代表人": "张三",
            "注册资本": "5000万元",
            "成立日期": "2017-01-01",
            "经营状态": "存续",
            "经营范围": "技术开发、技术咨询、技术服务；软件开发；计算机系统服务",
            "注册地址": "北京市海淀区中关村大街1号",
            "股东信息": [
                {"股东名称": "张三", "持股比例": "60%"},
                {"股东名称": "李四", "持股比例": "40%"},
            ],
            "高管信息": [
                {"姓名": "张三", "职位": "执行董事"},
                {"姓名": "李四", "职位": "监事"},
            ],
            "对外投资": [
                {"企业名称": "XX科技子公司", "持股比例": "100%"},
                {"企业名称": "XX投资公司", "持股比例": "30%"},
            ],
        }

        return json.dumps(mock_data, ensure_ascii=False, indent=2)


class SearchLegalRecordsTool(BaseTool):
    """搜索企业司法记录工具"""
    name: str = "search_legal_records"
    description: str = "搜索企业司法记录。当需要获取企业司法风险时调用此工具。"
    args_schema: Type[BaseModel] = SearchLegalInput

    def _run(self, enterprise_name: str) -> str:
        """运行工具"""
        # TODO: 接入真实的司法信息API（如中国裁判文书网）
        # 目前返回模拟数据
        mock_data = {
            "企业名称": enterprise_name,
            "裁判文书": [
                {
                    "案号": "(2024)京0108民初12345号",
                    "案由": "合同纠纷",
                    "判决日期": "2024-06-15",
                    "判决结果": "被告承担次要责任",
                    "状态": "已结案",
                },
                {
                    "案号": "(2023)京0108民初67890号",
                    "案由": "买卖合同纠纷",
                    "判决日期": "2023-09-20",
                    "判决结果": "调解结案",
                    "状态": "已结案",
                },
            ],
            "行政处罚": [
                {
                    "处罚文号": "京海市监罚字〔2024〕第123号",
                    "处罚类型": "环保处罚",
                    "处罚金额": "85万元",
                    "处罚日期": "2024-03-15",
                    "处罚机关": "北京市海淀区市场监督管理局",
                },
                {
                    "处罚文号": "京海税罚〔2025〕第456号",
                    "处罚类型": "税务处罚",
                    "处罚金额": "12万元",
                    "处罚日期": "2025-01-20",
                    "处罚机关": "国家税务总局北京市海淀区税务局",
                },
            ],
            "失信被执行人": [],
            "股权出质": [
                {
                    "出质人": "张三",
                    "质权人": "XX银行",
                    "出质金额": "750万元",
                    "出质日期": "2024-01-15",
                    "状态": "有效",
                },
            ],
        }

        return json.dumps(mock_data, ensure_ascii=False, indent=2)


class SearchFinancialDataTool(BaseTool):
    """搜索企业财务数据工具"""
    name: str = "search_financial_data"
    description: str = "搜索企业财务数据。当需要获取企业财务报表时调用此工具。"
    args_schema: Type[BaseModel] = SearchFinancialInput

    def _run(self, enterprise_name: str) -> str:
        """运行工具"""
        # TODO: 接入真实的财务数据API
        # 目前返回模拟数据
        mock_data = {
            "企业名称": enterprise_name,
            "财务报表": {
                "2024": {
                    "营业收入": 820000000,
                    "营业成本": 574000000,
                    "毛利润": 246000000,
                    "净利润": 102500000,
                    "总资产": 1500000000,
                    "总负债": 630000000,
                    "所有者权益": 870000000,
                    "经营活动现金流": 287000000,
                    "投资活动现金流": -120000000,
                    "筹资活动现金流": -50000000,
                },
                "2023": {
                    "营业收入": 680000000,
                    "营业成本": 476000000,
                    "毛利润": 204000000,
                    "净利润": 80240000,
                    "总资产": 1300000000,
                    "总负债": 585000000,
                    "所有者权益": 715000000,
                    "经营活动现金流": 220000000,
                    "投资活动现金流": -100000000,
                    "筹资活动现金流": -40000000,
                },
                "2022": {
                    "营业收入": 520000000,
                    "营业成本": 364000000,
                    "毛利润": 156000000,
                    "净利润": 53040000,
                    "总资产": 1100000000,
                    "总负债": 528000000,
                    "所有者权益": 572000000,
                    "经营活动现金流": 180000000,
                    "投资活动现金流": -80000000,
                    "筹资活动现金流": -30000000,
                },
            },
            "应收账款": {
                "2024": {"余额": 287000000, "周转天数": 45},
                "2023": {"余额": 238000000, "周转天数": 40},
                "2022": {"余额": 182000000, "周转天数": 35},
            },
            "存货": {
                "2024": {"余额": 92000000, "周转率": 6.2},
                "2023": {"余额": 82000000, "周转率": 5.8},
                "2022": {"余额": 66000000, "周转率": 5.5},
            },
        }

        return json.dumps(mock_data, ensure_ascii=False, indent=2)


# 创建工具实例
search_enterprise_info = SearchEnterpriseInfoTool()
search_legal_records = SearchLegalRecordsTool()
search_financial_data = SearchFinancialDataTool()
