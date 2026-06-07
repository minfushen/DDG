# backend/app/api/analysis.py
"""分析相关 API 路由"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional
import json
import tempfile
from pathlib import Path

from app.models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    ReportRequest,
    ReportResponse,
    ParseResponse,
    FinancialDataInput,
)
from app.config import settings
from app.engines.rebecca.parsers import FinancialParser
from app.engines.rebecca.analyzers import FinancialDDAnalyzer
from app.engines.rebecca.adapter import AnalyzerAdapter
from app.engines.rebecca.report_generator import ReportGenerator

router = APIRouter()

# 初始化 Rebecca 引擎组件
parser = FinancialParser()
report_generator = ReportGenerator(
    output_dir=str(settings.OUTPUT_DIR / "reports")
)


@router.post("/analysis/parse", response_model=ParseResponse)
async def parse_financial_report(file: UploadFile = File(...)):
    """
    解析财报文件

    支持 Excel (.xlsx, .xls) 和 PDF 格式的财报文件
    """
    try:
        # 验证文件类型
        allowed_extensions = [".xlsx", ".xls", ".pdf"]
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}，支持的格式: {', '.join(allowed_extensions)}"
            )

        # 读取文件内容
        content = await file.read()

        # 保存到临时文件进行处理
        with tempfile.NamedTemporaryFile(
            suffix=file_ext, delete=False
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 调用 Rebecca 引擎解析
        financial_data = parser.parse(tmp_path)

        # 转换为 API 响应格式
        result_data = FinancialDataInput(
            income_statement=financial_data.income_statement.to_dict()
            if financial_data.income_statement is not None
            else None,
            balance_sheet=financial_data.balance_sheet.to_dict()
            if financial_data.balance_sheet is not None
            else None,
            cash_flow=financial_data.cash_flow.to_dict()
            if financial_data.cash_flow is not None
            else None,
        )

        # 清理临时文件
        Path(tmp_path).unlink(missing_ok=True)

        return ParseResponse(
            status=AnalysisStatus.COMPLETED,
            financial_data=result_data,
            message=f"文件 {file.filename} 解析成功",
        )

    except HTTPException:
        raise
    except Exception as e:
        return ParseResponse(
            status=AnalysisStatus.FAILED,
            error=str(e),
            message="文件解析失败",
        )


@router.post("/analysis/analyze", response_model=AnalysisResponse)
async def analyze_financial_data(request: AnalysisRequest):
    """
    执行财务分析

    对企业财务数据进行 10 维度全面分析，返回 31 张分析表格和风险识别结果
    """
    try:
        # 将输入数据转换为 DataFrame
        import pandas as pd

        financial_data = {}
        if request.financial_data.income_statement:
            # 将字典转换为 DataFrame，使用 orient='index' 使键成为行索引
            financial_data["income_statement"] = pd.DataFrame(
                request.financial_data.income_statement, index=[0]
            ).T
        if request.financial_data.balance_sheet:
            financial_data["balance_sheet"] = pd.DataFrame(
                request.financial_data.balance_sheet, index=[0]
            ).T
        if request.financial_data.cash_flow:
            financial_data["cash_flow"] = pd.DataFrame(
                request.financial_data.cash_flow, index=[0]
            ).T

        # 调用 Rebecca 引擎进行分析
        analyzer = FinancialDDAnalyzer(
            financial_data=financial_data,
            supplementary_data=request.financial_data.supplementary_data,
        )

        # 执行 10 维度分析
        analysis_result = analyzer.generate_full_analysis()

        # 识别风险
        risks = analyzer.identify_risks()

        # 转换为 JSON 可序列化格式
        json_analysis = AnalyzerAdapter.analysis_to_json(analysis_result)
        json_risks = AnalyzerAdapter.risks_to_dict(risks)

        return AnalysisResponse(
            status=AnalysisStatus.COMPLETED,
            enterprise_name=request.enterprise_name,
            analysis_result=json_analysis,
            risks=json_risks,
            message=f"{request.enterprise_name} 财务分析完成",
        )

    except Exception as e:
        return AnalysisResponse(
            status=AnalysisStatus.FAILED,
            enterprise_name=request.enterprise_name,
            error=str(e),
            message="财务分析失败",
        )


@router.post("/analysis/report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    生成尽调报告

    基于分析结果生成专业的 Word/PDF 报告
    """
    try:
        # 调用报告生成器
        report_path = report_generator.generate(
            company_name=request.enterprise_name,
            analysis_result=request.analysis_result,
            format=request.report_format,
        )

        # 生成下载链接
        report_filename = Path(report_path).name
        download_url = f"/api/v1/reports/{report_filename}"

        return ReportResponse(
            status=AnalysisStatus.COMPLETED,
            enterprise_name=request.enterprise_name,
            report_path=report_path,
            download_url=download_url,
            message=f"报告已生成: {report_filename}",
        )

    except Exception as e:
        return ReportResponse(
            status=AnalysisStatus.FAILED,
            enterprise_name=request.enterprise_name,
            error=str(e),
            message="报告生成失败",
        )


@router.get("/reports/{filename}")
async def download_report(filename: str):
    """下载报告文件"""
    report_path = settings.OUTPUT_DIR / "reports" / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        path=str(report_path),
        filename=filename,
        media_type="application/octet-stream",
    )
