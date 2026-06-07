# backend/app/engines/rebecca/parsers.py
"""财报文件解析器"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class FinancialData:
    """财务数据结构"""
    income_statement: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cash_flow: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FinancialParser:
    """财报文件解析器"""

    # 利润表关键词
    INCOME_KEYWORDS = [
        "营业收入", "营业成本", "毛利", "营业利润", "净利润",
        "利润表", "损益表", "income statement", "profit and loss",
    ]

    # 资产负债表关键词
    BALANCE_KEYWORDS = [
        "资产总计", "负债合计", "所有者权益", "资产负债表",
        "balance sheet", "资产合计", "负债总计",
    ]

    # 现金流量表关键词
    CASHFLOW_KEYWORDS = [
        "经营活动", "投资活动", "筹资活动", "现金流量表",
        "cash flow", "现金及现金等价物",
    ]

    def __init__(self):
        self.supported_formats = [".xlsx", ".xls", ".pdf"]

    def parse(self, file_path: str) -> FinancialData:
        """
        解析财报文件

        Args:
            file_path: 文件路径

        Returns:
            FinancialData: 解析后的财务数据

        Raises:
            ValueError: 不支持的文件格式
            FileNotFoundError: 文件不存在
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if path.suffix not in self.supported_formats:
            raise ValueError(
                f"不支持的文件格式: {path.suffix}，"
                f"支持的格式: {', '.join(self.supported_formats)}"
            )

        if path.suffix in [".xlsx", ".xls"]:
            return self._parse_excel(path)
        elif path.suffix == ".pdf":
            return self._parse_pdf(path)

    def _parse_excel(self, file_path: Path) -> FinancialData:
        """解析 Excel 文件"""
        try:
            # 读取所有 sheet
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            income_statement = None
            balance_sheet = None
            cash_flow = None

            # 根据 sheet 名称或内容识别表格类型
            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheet_lower = sheet_name.lower()

                # 识别利润表
                if any(kw in sheet_lower for kw in ["利润", "损益", "income", "profit"]):
                    income_statement = df
                # 识别资产负债表
                elif any(kw in sheet_lower for kw in ["资产", "负债", "balance"]):
                    balance_sheet = df
                # 识别现金流量表
                elif any(kw in sheet_lower for kw in ["现金", "cash", "flow"]):
                    cash_flow = df
                # 通过内容识别
                else:
                    table_type = self._identify_table_by_content(df)
                    if table_type == "income":
                        income_statement = df
                    elif table_type == "balance":
                        balance_sheet = df
                    elif table_type == "cashflow":
                        cash_flow = df

            return FinancialData(
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow=cash_flow,
                metadata={
                    "source_file": str(file_path),
                    "sheet_names": sheet_names,
                    "format": "excel",
                },
            )

        except Exception as e:
            raise ValueError(f"Excel 解析失败: {str(e)}")

    def _parse_pdf(self, file_path: Path) -> FinancialData:
        """解析 PDF 文件"""
        try:
            import pdfplumber

            tables = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    tables.extend(page_tables)

            # 将表格转换为 DataFrame 并识别类型
            income_statement = None
            balance_sheet = None
            cash_flow = None

            for table in tables:
                if not table or len(table) < 2:
                    continue

                df = pd.DataFrame(table[1:], columns=table[0])
                table_type = self._identify_table_by_content(df)

                if table_type == "income" and income_statement is None:
                    income_statement = df
                elif table_type == "balance" and balance_sheet is None:
                    balance_sheet = df
                elif table_type == "cashflow" and cash_flow is None:
                    cash_flow = df

            return FinancialData(
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow=cash_flow,
                metadata={
                    "source_file": str(file_path),
                    "pages": len(tables),
                    "format": "pdf",
                },
            )

        except ImportError:
            raise ValueError("PDF 解析需要安装 pdfplumber: pip install pdfplumber")
        except Exception as e:
            raise ValueError(f"PDF 解析失败: {str(e)}")

    def _identify_table_by_content(self, df: pd.DataFrame) -> Optional[str]:
        """通过内容识别表格类型"""
        # 将 DataFrame 转为字符串进行关键词匹配
        content = df.to_string().lower()

        # 计算各类关键词的匹配数量
        income_score = sum(1 for kw in self.INCOME_KEYWORDS if kw in content)
        balance_score = sum(1 for kw in self.BALANCE_KEYWORDS if kw in content)
        cashflow_score = sum(1 for kw in self.CASHFLOW_KEYWORDS if kw in content)

        # 返回得分最高的类型
        max_score = max(income_score, balance_score, cashflow_score)
        if max_score == 0:
            return None

        if max_score == income_score:
            return "income"
        elif max_score == balance_score:
            return "balance"
        else:
            return "cashflow"
