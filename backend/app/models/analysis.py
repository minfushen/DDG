# backend/app/models/analysis.py
"""分析相关数据模型"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum


class AnalysisStatus(str, Enum):
    """分析状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FinancialDataInput(BaseModel):
    """财务数据输入"""
    income_statement: Optional[Dict[str, Any]] = Field(
        None, description="利润表数据"
    )
    balance_sheet: Optional[Dict[str, Any]] = Field(
        None, description="资产负债表数据"
    )
    cash_flow: Optional[Dict[str, Any]] = Field(
        None, description="现金流量表数据"
    )
    supplementary_data: Optional[Dict[str, Any]] = Field(
        None, description="补充数据"
    )


class AnalysisRequest(BaseModel):
    """分析请求"""
    enterprise_name: str = Field(..., description="企业名称")
    financial_data: FinancialDataInput = Field(..., description="财务数据")
    analysis_dimensions: Optional[List[str]] = Field(
        None, description="指定分析维度（可选，默认分析全部 10 维度）"
    )


class AnalysisResponse(BaseModel):
    """分析响应"""
    status: AnalysisStatus = Field(..., description="分析状态")
    enterprise_name: str = Field(..., description="企业名称")
    analysis_result: Optional[Dict[str, Any]] = Field(
        None, description="分析结果"
    )
    risks: Optional[Dict[str, List[str]]] = Field(
        None, description="风险识别结果"
    )
    message: Optional[str] = Field(None, description="状态消息")
    error: Optional[str] = Field(None, description="错误信息")


class ReportRequest(BaseModel):
    """报告生成请求"""
    enterprise_name: str = Field(..., description="企业名称")
    analysis_result: Dict[str, Any] = Field(..., description="分析结果")
    report_format: str = Field("docx", description="报告格式（docx 或 pdf）")


class ReportResponse(BaseModel):
    """报告生成响应"""
    status: AnalysisStatus = Field(..., description="生成状态")
    enterprise_name: str = Field(..., description="企业名称")
    report_path: Optional[str] = Field(None, description="报告文件路径")
    download_url: Optional[str] = Field(None, description="下载链接")
    message: Optional[str] = Field(None, description="状态消息")
    error: Optional[str] = Field(None, description="错误信息")


class ParseRequest(BaseModel):
    """财报解析请求"""
    file_path: Optional[str] = Field(None, description="文件路径")
    file_content: Optional[bytes] = Field(None, description="文件内容（base64 编码）")


class ParseResponse(BaseModel):
    """财报解析响应"""
    status: AnalysisStatus = Field(..., description="解析状态")
    financial_data: Optional[FinancialDataInput] = Field(
        None, description="解析后的财务数据"
    )
    message: Optional[str] = Field(None, description="状态消息")
    error: Optional[str] = Field(None, description="错误信息")
