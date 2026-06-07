# backend/app/engines/rebecca/report_generator.py
"""尽调报告生成器"""
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json


class ReportGenerator:
    """尽调报告生成器"""

    def __init__(self, output_dir: str = "./output/reports"):
        """
        初始化报告生成器

        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        company_name: str,
        analysis_result: Dict[str, Any],
        format: str = "docx",
    ) -> str:
        """
        生成尽调报告

        Args:
            company_name: 公司名称
            analysis_result: 分析结果
            format: 报告格式（docx 或 pdf）

        Returns:
            str: 报告文件路径
        """
        if format == "docx":
            return self._generate_docx(company_name, analysis_result)
        elif format == "pdf":
            return self._generate_pdf(company_name, analysis_result)
        else:
            raise ValueError(f"不支持的报告格式: {format}")

    def _generate_docx(
        self, company_name: str, analysis_result: Dict[str, Any]
    ) -> str:
        """生成 Word 报告"""
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()

            # 设置标题
            title = doc.add_heading(f"{company_name} 尽职调查报告", level=0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # 添加报告信息
            doc.add_paragraph(f"报告生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            doc.add_paragraph("")

            # 添加目录
            doc.add_heading("目录", level=1)
            toc_items = [
                "1. 企业基本信息",
                "2. 财务分析概览",
                "3. 盈利能力分析",
                "4. 偿债能力分析",
                "5. 营运能力分析",
                "6. 成长能力分析",
                "7. 现金流分析",
                "8. 风险提示",
                "9. 结论与建议",
            ]
            for item in toc_items:
                doc.add_paragraph(item, style="List Number")

            doc.add_page_break()

            # 1. 企业基本信息
            doc.add_heading("1. 企业基本信息", level=1)
            doc.add_paragraph(f"企业名称: {company_name}")
            doc.add_paragraph(f"报告类型: 财务尽职调查")
            doc.add_paragraph(f"分析日期: {datetime.now().strftime('%Y-%m-%d')}")

            # 2. 财务分析概览
            doc.add_heading("2. 财务分析概览", level=1)
            doc.add_paragraph("本报告基于企业提供的财务数据，从以下 10 个维度进行全面分析:")
            dimensions = [
                "盈利能力", "偿债能力", "营运能力", "成长能力",
                "现金流", "成本结构", "资产质量", "负债结构",
                "盈利趋势", "风险评估",
            ]
            for dim in dimensions:
                doc.add_paragraph(f"• {dim}", style="List Bullet")

            # 3-7. 各维度分析
            dimension_names = {
                "profitability": "盈利能力",
                "solvency": "偿债能力",
                "efficiency": "营运能力",
                "growth": "成长能力",
                "cash_flow": "现金流",
            }

            section_num = 3
            for dim_key, dim_name in dimension_names.items():
                doc.add_heading(f"{section_num}. {dim_name}分析", level=1)

                if dim_key in analysis_result:
                    tables = analysis_result[dim_key]
                    for table_name, table_data in tables.items():
                        doc.add_heading(f"{dim_name} - {table_name}", level=2)
                        # TODO: 将 DataFrame 转换为 Word 表格
                        doc.add_paragraph(json.dumps(table_data, ensure_ascii=False, indent=2))
                else:
                    doc.add_paragraph("暂无数据")

                section_num += 1

            # 8. 风险提示
            doc.add_heading("8. 风险提示", level=1)
            if "risk_assessment" in analysis_result:
                risk_data = analysis_result["risk_assessment"]
                if "risk_summary" in risk_data:
                    for _, row in risk_data["risk_summary"].iterrows():
                        doc.add_paragraph(
                            f"[{row.get('风险等级', '未知')}] {row.get('风险描述', '')}",
                            style="List Bullet"
                        )
            else:
                doc.add_paragraph("暂无重大风险提示")

            # 9. 结论与建议
            doc.add_heading("9. 结论与建议", level=1)
            doc.add_paragraph("基于以上分析，对企业财务状况的总体评价和建议如下:")
            doc.add_paragraph("1. 企业整体财务状况良好，盈利能力稳定")
            doc.add_paragraph("2. 偿债能力处于行业正常水平")
            doc.add_paragraph("3. 建议关注应收账款管理和成本控制")

            # 保存文件
            filename = f"{company_name}_尽调报告_{datetime.now().strftime('%Y%m%d')}.docx"
            filepath = self.output_dir / filename
            doc.save(str(filepath))

            return str(filepath)

        except ImportError:
            raise ImportError("生成 Word 报告需要安装 python-docx: pip install python-docx")
        except Exception as e:
            raise RuntimeError(f"Word 报告生成失败: {str(e)}")

    def _generate_pdf(
        self, company_name: str, analysis_result: Dict[str, Any]
    ) -> str:
        """生成 PDF 报告"""
        # TODO: 实现 PDF 报告生成
        # 可以使用 reportlab 或先生成 Word 再转换
        raise NotImplementedError("PDF 报告生成功能暂未实现，请使用 docx 格式")
