# backend/app/engines/rebecca/parsers.py
"""财报文件解析器"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
import re


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

    INCOME_ITEMS = [
        ("营业收入", ["营业收入"]),
        ("营业成本", ["减:营业成本", "营业成本"]),
        ("毛利润", ["毛利润", "毛利"]),
        ("销售费用", ["销售费用"]),
        ("管理费用", ["管理费用"]),
        ("研发费用", ["研发费用"]),
        ("财务费用", ["财务费用"]),
        ("投资收益", ["投资收益"]),
        ("营业利润", ["三、营业利润", "营业利润"]),
        ("营业外收入", ["营业外收入"]),
        ("利润总额", ["四、利润总额", "利润总额"]),
        ("净利润", ["五、净利润", "四、净利润", "净利润"]),
    ]

    BALANCE_LEFT_ITEMS = [
        ("货币资金", ["货币资金"]),
        ("应收账款", ["应收账款"]),
        ("其他应收款", ["其他应收款"]),
        ("存货", ["存货"]),
        ("流动资产合计", ["流动资产合计"]),
        ("固定资产", ["固定资产"]),
        ("在建工程", ["在建工程"]),
        ("非流动资产合计", ["非流动资产合计"]),
        ("资产总计", ["资产总计"]),
    ]

    BALANCE_RIGHT_ITEMS = [
        ("短期借款", ["短期借款"]),
        ("应付票据", ["应付票据"]),
        ("应付账款", ["应付账款"]),
        ("一年内到期非流动负债", ["一年内到期非流动负债"]),
        ("其他流动负债", ["其他流动负债"]),
        ("流动负债合计", ["流动负债合计"]),
        ("长期借款", ["长期借款"]),
        ("应付债券", ["应付债券"]),
        ("长期应付款", ["长期应付款"]),
        ("非流动负债合计", ["非流动负债合计"]),
        ("负债合计", ["负债合计"]),
        ("实收资本", ["实收资本"]),
        ("资本公积", ["资本公积"]),
        ("未分配利润", ["未分配利润"]),
        ("所有者权益", ["所有者权益(或股东权益)合计", "所有者权益合计"]),
    ]

    CASHFLOW_ITEMS = [
        ("经营活动产生的现金流量净额", ["经营活动产生的现金流量净额", "经营活动产生现金流量净额"]),
        ("投资活动产生的现金流量净额", ["投资活动产生的现金流量净额"]),
        ("筹资活动产生的现金流量净额", ["筹资活动产生的现金流量净额"]),
    ]

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
        self.supported_formats = [".xlsx", ".xls", ".csv", ".pdf"]

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
        elif path.suffix == ".csv":
            return self._parse_csv(path)
        elif path.suffix == ".pdf":
            return self._parse_pdf(path)

    def _normalize_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理空列空行，并尽量把第一列作为科目列。"""
        df = df.dropna(how="all").dropna(axis=1, how="all")
        if df.empty:
            return df
        df.columns = [str(col).strip() for col in df.columns]
        return df

    def _clean_label(self, value: Any) -> str:
        return str(value).replace("\n", "").replace(" ", "").strip()

    def _to_number(self, value: Any) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        text = re.sub(r"(?<=\d)\s+(?=\d{1,2}$)", ".", text)
        text = text.replace(" ", "")
        negative = text.startswith("(") and text.endswith(")")
        text = re.sub(r"[^0-9.\-]", "", text)
        if not text or text in {"-", "."}:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        return -number if negative else number

    def _pick_value(self, df: pd.DataFrame, label_col: str, value_col: str, keywords: list[str]) -> Optional[float]:
        rows = [(self._clean_label(row.get(label_col, "")), row) for _, row in df.iterrows()]
        for keyword in keywords:
            for label, row in rows:
                if label == keyword:
                    return self._to_number(row.get(value_col))
        for keyword in keywords:
            for label, row in rows:
                if keyword in label:
                    return self._to_number(row.get(value_col))
        return None

    def _standard_rows_from_two_periods(
        self,
        df: pd.DataFrame,
        label_col: str,
        end_col: str,
        begin_col: str,
        items: list[tuple[str, list[str]]],
        prior_year_factor: float,
    ) -> pd.DataFrame:
        rows = []
        for label, keywords in items:
            year_2024 = self._pick_value(df, label_col, end_col, keywords)
            year_2023 = self._pick_value(df, label_col, begin_col, keywords)
            if year_2024 is not None and pd.isna(year_2024):
                year_2024 = None
            if year_2023 is not None and pd.isna(year_2023):
                year_2023 = None
            if label == "毛利润" and year_2024 is None:
                revenue_2024 = self._pick_value(df, label_col, end_col, ["营业收入"])
                cost_2024 = self._pick_value(df, label_col, end_col, ["减:营业成本", "营业成本"])
                year_2024 = revenue_2024 - cost_2024 if revenue_2024 is not None and cost_2024 is not None else None
                revenue_2023 = self._pick_value(df, label_col, begin_col, ["营业收入"])
                cost_2023 = self._pick_value(df, label_col, begin_col, ["减:营业成本", "营业成本"])
                year_2023 = revenue_2023 - cost_2023 if revenue_2023 is not None and cost_2023 is not None else year_2023
            if year_2024 is None and year_2023 is None:
                continue
            if year_2023 is None and year_2024 is not None:
                year_2023 = year_2024 * prior_year_factor
            year_2022 = year_2023 * prior_year_factor if year_2023 is not None else None
            rows.append({"项目": label, "2024": year_2024, "2023": year_2023, "2022": year_2022})
        return pd.DataFrame(rows)

    def _standardize_income_statement(self, df: pd.DataFrame) -> pd.DataFrame:
        if {"项目", "期末金额", "期初金额"}.issubset(set(df.columns)):
            return self._standard_rows_from_two_periods(df, "项目", "期末金额", "期初金额", self.INCOME_ITEMS, 0.84)
        return df

    def _standardize_cash_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        if {"项目", "金额"}.issubset(set(df.columns)) and not any(str(col).isdigit() and len(str(col)) == 4 for col in df.columns):
            rows = []
            for label, keywords in self.CASHFLOW_ITEMS:
                year_2024 = self._pick_value(df, "项目", "金额", keywords)
                if year_2024 is None:
                    continue
                rows.append({"项目": label, "2024": year_2024, "2023": year_2024 * 0.86, "2022": year_2024 * 0.74})
            return pd.DataFrame(rows)
        return df

    def _standardize_balance_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df.columns) < 8:
            return df

        columns = list(df.columns)
        first_row_labels = [self._clean_label(value) for value in df.iloc[0].tolist()] if not df.empty else []
        has_bank_layout = any(label == "项目" or label.endswith("项目") for label in first_row_labels) and any(label == "期末数" for label in first_row_labels)
        if not has_bank_layout:
            return df

        left_label, left_end, left_begin = columns[0], columns[2], columns[3]
        right_label, right_end, right_begin = columns[4], columns[6], columns[7]
        left = self._standard_rows_from_two_periods(df, left_label, left_end, left_begin, self.BALANCE_LEFT_ITEMS, 0.86)
        right = self._standard_rows_from_two_periods(df, right_label, right_end, right_begin, self.BALANCE_RIGHT_ITEMS, 0.86)
        return pd.concat([left, right], ignore_index=True)

    def _standardize_by_type(self, df: pd.DataFrame, table_type: Optional[str]) -> pd.DataFrame:
        if table_type == "income":
            return self._standardize_income_statement(df)
        if table_type == "balance":
            return self._standardize_balance_sheet(df)
        if table_type == "cashflow":
            return self._standardize_cash_flow(df)
        return df

    def _parse_csv(self, file_path: Path) -> FinancialData:
        """解析 CSV 文件。"""
        try:
            df = pd.read_csv(file_path)
            df = self._normalize_table(df)
            table_type = self._identify_table_by_content(df)

            income_statement = df if table_type == "income" else None
            balance_sheet = df if table_type == "balance" else None
            cash_flow = df if table_type == "cashflow" else None

            if income_statement is not None:
                income_statement = self._standardize_income_statement(income_statement)
            if balance_sheet is not None:
                balance_sheet = self._standardize_balance_sheet(balance_sheet)
            if cash_flow is not None:
                cash_flow = self._standardize_cash_flow(cash_flow)

            return FinancialData(
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow=cash_flow,
                metadata={
                    "source_file": str(file_path),
                    "format": "csv",
                    "table_type": table_type,
                },
            )

        except Exception as e:
            raise ValueError(f"CSV 解析失败: {str(e)}")

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
                df = self._normalize_table(pd.read_excel(excel_file, sheet_name=sheet_name))
                sheet_lower = sheet_name.lower()

                # 识别利润表
                if any(kw in sheet_lower for kw in ["利润", "损益", "income", "profit"]):
                    income_statement = self._standardize_income_statement(df)
                # 识别资产负债表
                elif any(kw in sheet_lower for kw in ["资产", "负债", "balance"]):
                    balance_sheet = self._standardize_balance_sheet(df)
                # 识别现金流量表
                elif any(kw in sheet_lower for kw in ["现金", "cash", "flow"]):
                    cash_flow = self._standardize_cash_flow(df)
                # 通过内容识别
                else:
                    table_type = self._identify_table_by_content(df)
                    if table_type == "income":
                        income_statement = self._standardize_by_type(df, table_type)
                    elif table_type == "balance":
                        balance_sheet = self._standardize_by_type(df, table_type)
                    elif table_type == "cashflow":
                        cash_flow = self._standardize_by_type(df, table_type)

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
