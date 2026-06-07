# backend/app/agents/tools/report_tool.py
"""报告生成工具"""
from langchain_core.tools import tool
import json


@tool
def generate_due_diligence_report(
    company_name: str,
    analysis_result_json: str,
    report_format: str = "docx",
) -> str:
    """生成专业的尽调报告。

    当用户要求生成报告、导出报告时调用此工具。

    Args:
        company_name: 公司名称
        analysis_result_json: 分析结果 JSON 字符串
        report_format: 报告格式（"docx" 或 "pdf"）
    """
    try:
        from app.engines.rebecca.report_generator import ReportGenerator
        from app.config import settings

        analysis_result = json.loads(analysis_result_json)
        generator = ReportGenerator(
            output_dir=str(settings.OUTPUT_DIR / "reports")
        )

        output_path = generator.generate(
            company_name=company_name,
            analysis_result=analysis_result,
            format=report_format,
        )

        return json.dumps(
            {
                "success": True,
                "report_path": output_path,
                "message": f"报告已生成：{output_path}",
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"报告生成失败：{str(e)}",
            },
            ensure_ascii=False,
        )
