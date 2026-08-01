"""上市公司年报 PDF 四阶段解析管道。

Pipeline:
    Stage 1: MinerU 版面分析 → markdown + content_list
    Stage 2: MiniCPM-V / 规则转录 → 行列网格 JSON（只抄不算）
    Stage 3: 会计恒等式引擎 → 23 条规则勾稽校验，红黄绿分级
    Stage 4: qwen3.7 视觉兜底 → 跨页/宽表/图表

输出：标准化三大表（income_statement / balance_sheet / cash_flow），
      可直接输入 Rebecca 规则引擎。
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd

from app.config import settings
from app.engines.rebecca.parsers.pdf_image_utils import estimate_pages_for_statement
from app.engines.rebecca.parsers.vision_transcriber import get_vision_transcriber
from app.services.mineru_client import MinerUError, extract_pdf_bytes


logger = logging.getLogger(__name__)


@dataclass
class ParsedTable:
    """从 PDF 中识别出的候选表格。"""

    rows: List[List[str]]
    page: Optional[int] = None
    pages: List[int] = field(default_factory=list)
    source: str = "unknown"  # mineru_markdown / mineru_content_list / minicpmv / vision
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass
class FinancialStatementData:
    """标准化后的三大表数据。"""

    income_statement: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cash_flow: Optional[pd.DataFrame] = None
    unit: str = "yuan"  # yuan / wan_yuan / yi_yuan
    scope: Literal["consolidated", "parent"] = "consolidated"
    periods: List[int] = field(default_factory=list)
    source_documents: List[Dict[str, Any]] = field(default_factory=list)
    quality: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """四阶段管道输出。"""

    success: bool
    enterprise_name: str = ""
    stock_code: str = ""
    report_year: Optional[int] = None
    pdf_url: str = ""
    statements: FinancialStatementData = field(default_factory=FinancialStatementData)
    extraction_result: Dict[str, Any] = field(default_factory=dict)
    digital_reach_rate: float = 0.0
    auto_judgment_rate: float = 0.0
    main_table_coverage: str = "0/6"
    rule_family_coverage: str = "0/23"
    issues: List[str] = field(default_factory=list)
    needs_human_review: bool = True
    error: str = ""


# ── 标准科目映射 ───────────────────────────────────────────────

INCOME_STATEMENT_FIELDS = {
    "营业收入": "revenue",
    "营业成本": "operating_cost",
    "税金及附加": "taxes_and_surcharges",
    "销售费用": "selling_expenses",
    "管理费用": "administrative_expenses",
    "研发费用": "rd_expenses",
    "财务费用": "financial_expenses",
    "营业利润": "operating_profit",
    "利润总额": "total_profit",
    "净利润": "net_profit",
    "归属于母公司股东的净利润": "net_profit_attributable_to_parent",
    "扣除非经常性损益后的净利润": "deducted_non_recurring_net_profit",
}

BALANCE_SHEET_FIELDS = {
    "货币资金": "cash_and_equivalents",
    "应收账款": "accounts_receivable",
    "存货": "inventory",
    "流动资产合计": "current_assets",
    "固定资产": "fixed_assets",
    "无形资产": "intangible_assets",
    "非流动资产合计": "non_current_assets",
    "资产总计": "total_assets",
    "短期借款": "short_term_borrowings",
    "应付账款": "accounts_payable",
    "流动负债合计": "current_liabilities",
    "长期借款": "long_term_borrowings",
    "非流动负债合计": "non_current_liabilities",
    "负债合计": "total_liabilities",
    "归属于母公司所有者权益合计": "equity_attributable_to_parent",
    "所有者权益合计": "total_equity",
    "股东权益合计": "total_equity",
}

CASH_FLOW_FIELDS = {
    "销售商品、提供劳务收到的现金": "cash_from_sales",
    "经营活动现金流入小计": "operating_cash_inflow",
    "经营活动现金流出小计": "operating_cash_outflow",
    "经营活动产生的现金流量净额": "net_operating_cash_flow",
    "投资活动产生的现金流量净额": "net_investing_cash_flow",
    "筹资活动产生的现金流量净额": "net_financing_cash_flow",
    "现金及现金等价物净增加额": "net_increase_in_cash",
}


# ── Stage 1: MinerU 版面分析 ───────────────────────────────────

class MinerUParser:
    """调用 MinerU 解析 PDF，获取 markdown 文本和表格候选。"""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout

    def parse(self, pdf_bytes: bytes) -> Dict[str, Any]:
        try:
            result = extract_pdf_bytes(pdf_bytes)
        except MinerUError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            return {"success": False, "error": f"unexpected: {exc}"}

        text = result.get("text", "")
        tables = result.get("tables", [])
        content_list = result.get("content_list", [])
        metadata = result.get("metadata", {})

        # 如果 markdown 表格为空，尝试从 content_list 恢复
        if not tables and content_list:
            tables = self._tables_from_content_list(content_list)
            logger.info("从 MinerU content_list 恢复 %d 张表格", len(tables))

        # MinerU 有时把财务三大表以 HTML <table> 形式嵌入 markdown text，
        # 而 tables/content_list 中缺失。这里兜底从 text 中提取。
        if not self._has_financial_statement_tables(tables):
            tables_from_text = self._tables_from_markdown_text(text)
            if tables_from_text:
                logger.info("从 markdown text 恢复 %d 张表格", len(tables_from_text))
                tables.extend(tables_from_text)

        return {
            "success": True,
            "text": text,
            "tables": tables,
            "content_list": content_list,
            "metadata": metadata,
        }

    @staticmethod
    def _has_financial_statement_tables(tables: List[List[List[str]]]) -> bool:
        """检查已提取表格中是否包含真正的三大表（不仅有表名关键词，还要有核心科目）。"""
        required_fields = {
            "利润表": ["营业收入", "净利润"],
            "资产负债表": ["资产总计", "负债合计"],
            "现金流量表": ["经营活动", "现金"],
        }
        found_kinds = set()
        for table in tables:
            if not table:
                continue
            sample = " ".join(" ".join(str(cell) for cell in row) for row in table[:10])
            for kind, fields in required_fields.items():
                if kind in sample and all(f in sample for f in fields):
                    found_kinds.add(kind)
        return len(found_kinds) >= 3

    @staticmethod
    def _tables_from_markdown_text(text: str) -> List[List[List[str]]]:
        """从 markdown text 中的 HTML <table> 块提取表格，优先根据三大表关键词定位。"""
        import re

        tables: List[List[List[str]]] = []
        all_table_matches = list(
            re.finditer(r"<table[^>]*>.*?</table>", text, flags=re.DOTALL | re.IGNORECASE)
        )

        # 根据三大表关键词定位最近的 table，并把关键词作为表头行插入，
        # 便于 Stage 2 的 StatementTableDetector 识别。
        financial_keywords = {
            "balance_sheet": ["## 合并资产负债表", "合并资产负债表"],
            "income_statement": ["## 合并利润表", "合并利润表"],
            "cash_flow": ["## 合并现金流量表", "合并现金流量表"],
        }
        for statement_type, keywords in financial_keywords.items():
            for keyword in keywords:
                idx = text.find(keyword)
                if idx == -1:
                    continue
                # 找到 keyword 之后最近的 table
                for match in all_table_matches:
                    if match.start() > idx:
                        html = match.group()
                        try:
                            dfs = pd.read_html(io.StringIO(html))
                            for df in dfs:
                                table = [[keyword]]
                                for _, row in df.iterrows():
                                    table.append(
                                        [str(cell) if pd.notna(cell) else "" for cell in row]
                                    )
                                if len(table) >= 2:
                                    tables.append(table)
                        except Exception:
                            continue
                        break

        # 兜底：解析所有 table
        if not tables:
            for match in all_table_matches:
                try:
                    dfs = pd.read_html(io.StringIO(match.group()))
                    for df in dfs:
                        table = []
                        for _, row in df.iterrows():
                            table.append(
                                [str(cell) if pd.notna(cell) else "" for cell in row]
                            )
                        if len(table) >= 2:
                            tables.append(table)
                except Exception:
                    continue
        return tables

    @staticmethod
    def _tables_from_content_list(content_list: List[Dict[str, Any]]) -> List[List[List[str]]]:
        """从 MinerU content_list 的 table 类型块中提取表格。

        MinerU content_list 中 table block 的表格内容放在 ``table_body`` 字段的 HTML 中。
        """
        tables: List[List[List[str]]] = []
        for block in content_list:
            if block.get("type") != "table":
                continue
            html = block.get("table_body") or ""
            if not html.strip().startswith("<table"):
                continue
            try:
                dfs = pd.read_html(io.StringIO(html))
                for df in dfs:
                    table = []
                    for _, row in df.iterrows():
                        table.append([str(cell) if pd.notna(cell) else "" for cell in row])
                    if len(table) >= 2:
                        tables.append(table)
            except Exception:
                continue
        return tables


# ── Stage 2: 表格识别与标准化 ──────────────────────────────────

class StatementTableDetector:
    """从候选表格中识别三大表。"""

    STATEMENT_KEYWORDS = {
        "income_statement": ["利润表", "合并利润表", "母公司利润表", "损益表"],
        "balance_sheet": ["资产负债表", "合并资产负债表", "母公司资产负债表"],
        "cash_flow": ["现金流量表", "合并现金流量表", "母公司现金流量表"],
    }

    FIELD_KEYWORDS = {
        "income_statement": ["营业收入", "营业成本", "净利润", "利润总额", "营业利润"],
        "balance_sheet": ["资产总计", "负债合计", "所有者权益", "流动资产", "货币资金"],
        "cash_flow": ["经营活动", "投资活动", "筹资活动", "现金", "现金流量"],
    }

    def detect(self, tables: List[List[List[str]]], text: str = "") -> Dict[str, ParsedTable]:
        """返回每个 statement_type 最匹配的表格。

        评分规则：
        - 精确包含“合并X表” > 仅包含“X表”
        - 年份列（20xx）越多越优
        - 包含的标准科目关键词越多越优（至少 2 个才视为候选）
        - 表格行/列规模适中（过滤释义表、季度表等噪声）
        """
        candidates: Dict[str, List[ParsedTable]] = {t: [] for t in self.STATEMENT_KEYWORDS}

        for table in tables:
            if not table or len(table) < 2:
                continue
            header_sample = " ".join(
                " ".join(str(cell) for cell in row)
                for row in table[:3]
            )
            for statement_type, keywords in self.STATEMENT_KEYWORDS.items():
                score = self._score_table(table, header_sample, statement_type, keywords)
                if score > 0:
                    candidates[statement_type].append(ParsedTable(
                        rows=table,
                        source="mineru_markdown",
                        confidence=min(0.95, 0.5 + score * 0.1),
                    ))

        results: Dict[str, ParsedTable] = {}
        for statement_type, pts in candidates.items():
            if not pts:
                continue
            # 按置信度降序，取最佳候选
            pts.sort(key=lambda p: p.confidence, reverse=True)
            results[statement_type] = pts[0]
        return results

    def _score_table(
        self,
        table: List[List[str]],
        header_sample: str,
        statement_type: str,
        keywords: List[str],
    ) -> float:
        """返回表格与目标三大表的匹配分数；0 表示不匹配。"""
        has_keyword = False
        exact_merge = False
        for kw in keywords:
            if kw in header_sample:
                has_keyword = True
                if kw.startswith("合并"):
                    exact_merge = True
        if not has_keyword:
            return 0.0

        score = 2.0 if exact_merge else 1.0

        # 年份列数量
        year_cols = set()
        for row in table[:5]:
            for cell in row:
                if re.search(r"20\d{2}", str(cell)):
                    year_cols.add(str(cell).strip())
        score += len(year_cols) * 1.5

        # 标准科目命中数
        full_text = " ".join(" ".join(str(cell) for cell in row) for row in table)
        field_hits = sum(1 for fk in self.FIELD_KEYWORDS.get(statement_type, []) if fk in full_text)
        if field_hits < 2:
            return 0.0
        score += field_hits * 0.5

        # 规模：行数适中（过滤释义表、季度表），列数适中
        num_rows = len(table)
        num_cols = max(len(row) for row in table) if table else 0
        if num_rows < 5 or num_cols < 3:
            score -= 2.0
        if num_rows > 80:
            score += 1.0  # 完整年报通常很长

        # 过滤明显是释义表/摘要表/季度表的噪声
        if "释义" in header_sample or "股票简称" in header_sample:
            score -= 3.0
        if "第一季度" in header_sample or "季度" in header_sample:
            score -= 2.0

        return max(0.0, score)


class StatementNormalizer:
    """把识别出的表格标准化为 DataFrame。"""

    def __init__(self):
        self.field_maps = {
            "income_statement": INCOME_STATEMENT_FIELDS,
            "balance_sheet": BALANCE_SHEET_FIELDS,
            "cash_flow": CASH_FLOW_FIELDS,
        }

    def normalize(
        self,
        table: ParsedTable,
        statement_type: str,
        report_year: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        rows = table.rows
        if len(rows) < 2:
            return None

        # 找到包含 20xx 年份列的真实表头行；允许前 5 行内存在表名/说明行。
        header: List[str] = []
        header_idx = 0
        year_cols: List[int] = []
        for idx, row in enumerate(rows[:5]):
            candidates = [
                i for i, h in enumerate(row)
                if re.search(r"20\d{2}", str(h).strip())
            ]
            if candidates:
                header = row
                header_idx = idx
                year_cols = candidates
                break

        # 兜底：处理只有“期末余额/期初余额”或“本期数/上期数”的表头
        if not year_cols and report_year:
            for idx, row in enumerate(rows[:5]):
                period_headers = [(i, str(h).strip()) for i, h in enumerate(row)
                                  if str(h).strip() in {"期末余额", "期初余额", "本期数", "上期数"}]
                if period_headers:
                    header = row
                    header_idx = idx
                    year_cols = [i for i, _ in period_headers]
                    break

        if not year_cols:
            table.notes.append("未识别到 20xx 年份列")
            return None

        label_col = 0  # 假设第一列为科目
        field_map = self.field_maps.get(statement_type, {})

        records = []
        for row in rows[header_idx + 1:]:
            if len(row) <= max(year_cols):
                continue
            label = str(row[label_col]).strip().replace(" ", "").replace("\n", "")
            std_field = field_map.get(label)
            if not std_field:
                # fuzzy match: 子串包含
                for cn, en in field_map.items():
                    if cn in label or label in cn:
                        std_field = en
                        break
            if not std_field:
                continue

            record = {"field": std_field, "label": label}
            for idx, year_idx in enumerate(year_cols):
                header_text = str(header[year_idx]).strip()
                year_match = re.search(r"20\d{2}", header_text)
                if year_match:
                    year = year_match.group()
                elif header_text in {"期末余额", "本期数"}:
                    year = str(report_year) if report_year else header_text
                elif header_text in {"期初余额", "上期数"}:
                    year = str(report_year - 1) if report_year else header_text
                else:
                    year = header_text
                value = self._parse_number(row[year_idx])
                record[str(year)] = value
            records.append(record)

        if not records:
            return None

        df = pd.DataFrame(records)
        return df

    @staticmethod
    def _parse_number(value: Any) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip()
        if text in ("—", "-", "", "None", "nan"):
            return None
        # 去掉千分位逗号、括号负数
        negative = text.startswith("(") and text.endswith(")")
        text = text.replace(",", "").replace("(", "").replace(")", "").replace(" ", "")
        try:
            num = float(text)
            return -num if negative else num
        except (TypeError, ValueError):
            return None


# ── Stage 3: 会计恒等式校验 ────────────────────────────────────

class AccountingValidator:
    """确定性勾稽引擎：23 条会计恒等式规则 + 红黄绿分级。"""

    def __init__(self, tolerance: Optional[float] = None):
        self.tolerance = tolerance or settings.ACCOUNTING_VALIDATION_TOLERANCE
        self.rules = self._build_rules()

    def validate(self, data: FinancialStatementData) -> Dict[str, Any]:
        findings: List[str] = []
        rule_results: List[Dict[str, Any]] = []
        passed = 0
        failed = 0
        uncertain = 0

        for rule in self.rules:
            status, detail = rule["check"](data)
            result = {
                "name": rule["name"],
                "category": rule["category"],
                "severity": rule["severity"],
                "status": status,
                "detail": detail,
            }
            rule_results.append(result)
            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
                findings.append(f"[{rule['severity'].upper()}] {rule['name']}：{detail}")
            else:  # uncertain
                uncertain += 1
                findings.append(f"[UNCERTAIN] {rule['name']}：{detail}")

        total = passed + failed + uncertain
        auto_judgment_rate = (passed / total) if total else 0.0

        # 红黄绿分级：按规则族统计
        categories = {}
        for r in rule_results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "uncertain": 0, "total": 0}
            categories[cat]["total"] += 1
            categories[cat][r["status"]] += 1

        return {
            "passed": passed,
            "failed": failed,
            "uncertain": uncertain,
            "total": total,
            "auto_judgment_rate": auto_judgment_rate,
            "rule_results": rule_results,
            "findings": findings,
            "categories": categories,
        }

    def _build_rules(self) -> List[Dict[str, Any]]:
        """定义 23 条勾稽规则。"""
        return [
            # ── 资产负债表（6 条）──────────────────────────────
            {"name": "资产总计 = 流动 + 非流动资产", "category": "balance_sheet", "severity": "red", "check": self._rule_assets_decomposition},
            {"name": "负债总计 = 流动 + 非流动负债", "category": "balance_sheet", "severity": "red", "check": self._rule_liabilities_decomposition},
            {"name": "资产负债表平衡", "category": "balance_sheet", "severity": "red", "check": self._rule_balance_sheet_balance},
            {"name": "流动资产 ≥ 货币资金", "category": "balance_sheet", "severity": "yellow", "check": self._rule_current_assets_ge_cash},
            {"name": "流动资产 ≥ 应收账款", "category": "balance_sheet", "severity": "yellow", "check": self._rule_current_assets_ge_receivable},
            {"name": "流动资产 ≥ 存货", "category": "balance_sheet", "severity": "yellow", "check": self._rule_current_assets_ge_inventory},

            # ── 利润表（5 条）──────────────────────────────────
            {"name": "营业利润 ≈ 收入 - 成本 - 费用", "category": "income_statement", "severity": "yellow", "check": self._rule_operating_profit_approx},
            {"name": "利润总额 ≈ 营业利润 + 营业外收支", "category": "income_statement", "severity": "yellow", "check": self._rule_total_profit_approx},
            {"name": "净利润 ≈ 利润总额 - 所得税", "category": "income_statement", "severity": "yellow", "check": self._rule_net_profit_approx},
            {"name": "归母净利润 ≤ 净利润", "category": "income_statement", "severity": "red", "check": self._rule_attributable_le_net_profit},
            {"name": "营业收入 ≥ 营业成本", "category": "income_statement", "severity": "yellow", "check": self._rule_revenue_ge_cost},

            # ── 现金流量表（5 条）──────────────────────────────
            {"name": "经营活动净额 = 流入 - 流出", "category": "cash_flow", "severity": "red", "check": self._rule_operating_cflow},
            {"name": "投资活动净额 = 流入 - 流出", "category": "cash_flow", "severity": "red", "check": self._rule_investing_cflow},
            {"name": "筹资活动净额 = 流入 - 流出", "category": "cash_flow", "severity": "red", "check": self._rule_financing_cflow},
            {"name": "现金净增加额 = 经营 + 投资 + 筹资", "category": "cash_flow", "severity": "red", "check": self._rule_cash_increase_sum},
            {"name": "经营现金流与净利润方向一致", "category": "cash_flow", "severity": "yellow", "check": self._rule_op_cash_direction},

            # ── 跨表勾稽（4 条）──────────────────────────────
            {"name": "货币资金与现金等价物逻辑一致", "category": "cross", "severity": "yellow", "check": self._rule_cash_cross_consistency},
            {"name": "未分配利润变动 ≈ 净利润 - 分红", "category": "cross", "severity": "yellow", "check": self._rule_retained_earnings_approx},
            {"name": "固定资产变动与投资和折旧方向一致", "category": "cross", "severity": "yellow", "check": self._rule_fixed_assets_approx},
            {"name": "借款变动与筹资现金流一致", "category": "cross", "severity": "yellow", "check": self._rule_borrowings_cashflow},

            # ── 合理性检查（3 条）──────────────────────────────
            {"name": "资产总计 > 0", "category": "sanity", "severity": "red", "check": self._rule_total_assets_positive},
            {"name": "负债合计 ≥ 0", "category": "sanity", "severity": "red", "check": self._rule_total_liabilities_nonnegative},
            {"name": "所有者权益 ≥ 0", "category": "sanity", "severity": "yellow", "check": self._rule_total_equity_nonnegative},
        ]

    # ── 工具方法 ─────────────────────────────────────────────

    def _years(self, df: Optional[pd.DataFrame]) -> List[str]:
        if df is None or df.empty:
            return []
        return [str(c) for c in df.columns if re.match(r"^20\d{2}$", str(c))]

    @staticmethod
    def _get(df: Optional[pd.DataFrame], field: str, year: Any) -> Optional[float]:
        if df is None or df.empty:
            return None
        row = df[df["field"] == field]
        if row.empty:
            return None
        return row.iloc[0].get(str(year))

    def _relative_diff(self, a: Optional[float], b: Optional[float]) -> Optional[float]:
        """相对差异；当基准为 0 时退回到绝对差异。"""
        if a is None or b is None:
            return None
        base = max(abs(a), abs(b), 1.0)
        return abs(a - b) / base

    def _check_equal(self, a: Optional[float], b: Optional[float]) -> bool:
        diff = self._relative_diff(a, b)
        return diff is not None and diff <= self.tolerance

    def _check_sum(self, target: Optional[float], parts: List[Optional[float]]) -> bool:
        if target is None or any(p is None for p in parts):
            return False
        return self._check_equal(target, sum(parts))  # type: ignore[arg-type]

    # ── 资产负债表规则 ───────────────────────────────────────

    def _rule_assets_decomposition(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.balance_sheet,
            ["current_assets", "non_current_assets"],
            "total_assets",
            "流动资产 {current_assets} + 非流动资产 {non_current_assets} ≠ 资产总计 {total_assets}",
        )

    def _rule_liabilities_decomposition(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.balance_sheet,
            ["current_liabilities", "non_current_liabilities"],
            "total_liabilities",
            "流动负债 {current_liabilities} + 非流动负债 {non_current_liabilities} ≠ 负债合计 {total_liabilities}",
        )

    def _rule_balance_sheet_balance(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.balance_sheet,
            ["total_liabilities", "total_equity"],
            "total_assets",
            "负债 {total_liabilities} + 权益 {total_equity} ≠ 资产 {total_assets}",
        )

    def _rule_current_assets_ge_cash(self, data: FinancialStatementData) -> tuple:
        return self._apply_component_check(data.balance_sheet, "current_assets", "cash_and_equivalents")

    def _rule_current_assets_ge_receivable(self, data: FinancialStatementData) -> tuple:
        return self._apply_component_check(data.balance_sheet, "current_assets", "accounts_receivable")

    def _rule_current_assets_ge_inventory(self, data: FinancialStatementData) -> tuple:
        return self._apply_component_check(data.balance_sheet, "current_assets", "inventory")

    # ── 利润表规则 ───────────────────────────────────────────

    def _rule_operating_profit_approx(self, data: FinancialStatementData) -> tuple:
        # 真实年报营业利润还包含其他收益、投资收益、公允价值变动、减值损失等，
        # 这里用收入和成本费用的方向/量级做宽松校验，避免缺失字段导致误判。
        years = self._years(data.income_statement)
        if not years:
            return "uncertain", "缺少利润表"
        mismatches = []
        for year in years:
            revenue = self._get(data.income_statement, "revenue", year)
            cost = self._get(data.income_statement, "operating_cost", year)
            op = self._get(data.income_statement, "operating_profit", year)
            if revenue is None or cost is None or op is None:
                continue
            # 毛利应能覆盖费用并产生营业利润；异常方向才报警
            gross = revenue - cost
            if gross == 0:
                continue
            if (gross > 0 and op < -abs(gross) * 0.5) or (gross < 0 and op > abs(gross) * 0.5):
                mismatches.append(f"{year}: 毛利 {gross} 与营业利润 {op} 方向/量级异常")
        if mismatches:
            return "failed", "；".join(mismatches)
        return "passed", ""

    def _rule_total_profit_approx(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.income_statement,
            ["operating_profit"],
            "total_profit",
            "营业利润 {operating_profit} 与利润总额 {total_profit} 方向/量级异常",
            formula=lambda op, tp: op,
            tolerance_factor=0.30,
        )

    def _rule_net_profit_approx(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.income_statement,
            ["total_profit"],
            "net_profit",
            "利润总额 {total_profit} 与净利润 {net_profit} 方向/量级异常",
            formula=lambda tp, np: tp,
            tolerance_factor=0.40,
        )

    def _rule_attributable_le_net_profit(self, data: FinancialStatementData) -> tuple:
        return self._apply_component_check(
            data.income_statement,
            "net_profit",
            "net_profit_attributable_to_parent",
            lhs_ge_rhs=True,
        )

    def _rule_revenue_ge_cost(self, data: FinancialStatementData) -> tuple:
        return self._apply_component_check(
            data.income_statement,
            "revenue",
            "operating_cost",
            lhs_ge_rhs=True,
        )

    # ── 现金流量表规则 ───────────────────────────────────────

    def _rule_operating_cflow(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.cash_flow,
            ["operating_cash_inflow", "operating_cash_outflow"],
            "net_operating_cash_flow",
            "经营流入 {operating_cash_inflow} - 流出 {operating_cash_outflow} ≠ 净额 {net_operating_cash_flow}",
            formula=lambda inf, outf, net: inf - outf,
        )

    def _rule_investing_cflow(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.cash_flow,
            ["investing_cash_inflow", "investing_cash_outflow"],
            "net_investing_cash_flow",
            "投资流入 - 流出 ≠ 净额",
            formula=lambda inf, outf, net: inf - outf,
        )

    def _rule_financing_cflow(self, data: FinancialStatementData) -> tuple:
        return self._apply_yearly_check(
            data.cash_flow,
            ["financing_cash_inflow", "financing_cash_outflow"],
            "net_financing_cash_flow",
            "筹资流入 - 流出 ≠ 净额",
            formula=lambda inf, outf, net: inf - outf,
        )

    def _rule_cash_increase_sum(self, data: FinancialStatementData) -> tuple:
        # 真实现金流量表还受汇率变动影响，放宽容差避免误判
        return self._apply_yearly_check(
            data.cash_flow,
            ["net_operating_cash_flow", "net_investing_cash_flow", "net_financing_cash_flow"],
            "net_increase_in_cash",
            "经营 {net_operating_cash_flow} + 投资 {net_investing_cash_flow} + 筹资 {net_financing_cash_flow} ≠ 净增 {net_increase_in_cash}",
            tolerance_factor=0.15,
        )

    def _rule_op_cash_direction(self, data: FinancialStatementData) -> tuple:
        years = self._years(data.income_statement) or self._years(data.cash_flow)
        if not years:
            return "uncertain", "利润表/现金流量表均缺失"
        mismatches = []
        for year in years:
            np = self._get(data.income_statement, "net_profit", year)
            op = self._get(data.cash_flow, "net_operating_cash_flow", year)
            if np is None or op is None:
                continue
            if np > 0 and op < 0:
                mismatches.append(f"{year} 净利润 {np} 为正但经营现金流 {op} 为负")
        if mismatches:
            return "failed", "；".join(mismatches)
        return "passed", ""

    # ── 跨表规则 ─────────────────────────────────────────────

    def _rule_cash_cross_consistency(self, data: FinancialStatementData) -> tuple:
        years = self._years(data.balance_sheet) or self._years(data.cash_flow)
        if not years:
            return "uncertain", "缺少资产负债表或现金流量表"
        mismatches = []
        for year in years:
            bs_cash = self._get(data.balance_sheet, "cash_and_equivalents", year)
            cf_cash = self._get(data.cash_flow, "net_increase_in_cash", year)
            if bs_cash is None or cf_cash is None:
                continue
            # 允许符号方向一致即可：资产端现金增加通常对应现金流净增为正
            if (bs_cash > 0 and cf_cash < -abs(bs_cash)) or (bs_cash < 0):
                mismatches.append(f"{year} 货币资金 {bs_cash} 与现金净增加额 {cf_cash} 方向/量级异常")
        if mismatches:
            return "failed", "；".join(mismatches)
        return "passed", ""

    def _rule_retained_earnings_approx(self, data: FinancialStatementData) -> tuple:
        # 因当前标准化字段未含未分配利润与分红，暂标记为不确定
        return "uncertain", "缺少未分配利润与分红字段"

    def _rule_fixed_assets_approx(self, data: FinancialStatementData) -> tuple:
        return "uncertain", "缺少固定资产购置/折旧/处置明细"

    def _rule_borrowings_cashflow(self, data: FinancialStatementData) -> tuple:
        return "uncertain", "缺少短期/长期借款期初期末明细与筹资现金流细项"

    # ── 合理性检查 ───────────────────────────────────────────

    def _rule_total_assets_positive(self, data: FinancialStatementData) -> tuple:
        return self._apply_positive_check(data.balance_sheet, "total_assets", strict=True)

    def _rule_total_liabilities_nonnegative(self, data: FinancialStatementData) -> tuple:
        return self._apply_positive_check(data.balance_sheet, "total_liabilities", strict=False)

    def _rule_total_equity_nonnegative(self, data: FinancialStatementData) -> tuple:
        return self._apply_positive_check(data.balance_sheet, "total_equity", strict=False)

    # ── 通用检查模板 ─────────────────────────────────────────

    def _apply_yearly_check(
        self,
        df: Optional[pd.DataFrame],
        part_fields: List[str],
        target_field: str,
        message_template: str,
        formula: Optional[Any] = None,
        tolerance_factor: float = 1.0,
    ) -> tuple:
        years = self._years(df)
        if not years:
            return "uncertain", f"缺少 {target_field} 相关报表"

        mismatches = []
        for year in years:
            target = self._get(df, target_field, year)
            parts = [self._get(df, f, year) for f in part_fields]
            if target is None or any(p is None for p in parts):
                continue

            if formula is not None:
                expected = formula(*parts, target)
            else:
                expected = sum(parts)  # type: ignore[assignment]

            base = max(abs(target), abs(expected), 1.0)
            if abs(target - expected) / base > self.tolerance * tolerance_factor:
                ctx = {target_field: target}
                for f, p in zip(part_fields, parts):
                    ctx[f] = p
                mismatches.append(f"{year}: " + message_template.format(**ctx))

        if mismatches:
            return "failed", "；".join(mismatches)
        return "passed", ""

    def _apply_component_check(
        self,
        df: Optional[pd.DataFrame],
        lhs_field: str,
        rhs_field: str,
        lhs_ge_rhs: bool = True,
    ) -> tuple:
        years = self._years(df)
        if not years:
            return "uncertain", f"缺少 {lhs_field}/{rhs_field} 相关报表"
        mismatches = []
        for year in years:
            lhs = self._get(df, lhs_field, year)
            rhs = self._get(df, rhs_field, year)
            if lhs is None or rhs is None:
                continue
            if lhs_ge_rhs and lhs < rhs - 1e-6:
                mismatches.append(f"{year}: {lhs_field} {lhs} < {rhs_field} {rhs}")
            elif not lhs_ge_rhs and lhs > rhs + 1e-6:
                mismatches.append(f"{year}: {lhs_field} {lhs} > {rhs_field} {rhs}")
        if mismatches:
            return "failed", "；".join(mismatches)
        return "passed", ""

    def _apply_positive_check(
        self,
        df: Optional[pd.DataFrame],
        field: str,
        strict: bool = True,
    ) -> tuple:
        years = self._years(df)
        if not years:
            return "uncertain", f"缺少 {field} 相关报表"
        mismatches = []
        for year in years:
            value = self._get(df, field, year)
            if value is None:
                continue
            if strict and value <= 0:
                mismatches.append(f"{year}: {field} = {value} 非正")
            elif not strict and value < 0:
                mismatches.append(f"{year}: {field} = {value} 为负")
        if mismatches:
            return "failed", "；".join(mismatches)
        return "passed", ""


# ── Stage 4: 视觉兜底（占位） ───────────────────────────────────

class VisionFallback:
    """跨页 / 宽表 / 图表 / 勾稽失败的视觉兜底。"""

    def __init__(self, transcriber: Optional[Any] = None):
        self.transcriber = transcriber or get_vision_transcriber()

    def fallback(
        self,
        pdf_bytes: bytes,
        table: ParsedTable,
        statement_type: Literal["income_statement", "balance_sheet", "cash_flow"],
    ) -> ParsedTable:
        """对表格所在页面区域重新截图并调用视觉模型读回。

        触发场景：
        - 跨页表格（pages 数量 > 1）
        - 超宽表（列数 > 阈值）
        - Stage 3 勾稽失败
        """
        pages = table.pages or ([table.page] if table.page else [])
        if not pages:
            table.notes.append("Stage4 视觉兜底跳过：未提供页码")
            return table

        try:
            transcribed = self.transcriber.transcribe_table(pdf_bytes, table, statement_type)
        except Exception as exc:
            logger.warning("Stage4 视觉兜底调用失败: %s", exc)
            table.notes.append(f"Stage4 视觉兜底调用失败: {exc}")
            return table

        vision_sources = ("vision_openai", "vision_minicpmv")
        if transcribed.source in vision_sources and transcribed.rows and len(transcribed.rows) >= 2:
            transcribed.notes.append(f"Stage4 视觉兜底成功：pages={pages}")
            return transcribed

        table.notes.append("Stage4 视觉兜底未返回有效表格")
        return table


# ── 主入口 ─────────────────────────────────────────────────────

class FinancialPdfPipeline:
    """上市公司年报 PDF 四阶段解析管道。"""

    def __init__(self):
        self.mineru = MinerUParser()
        self.detector = StatementTableDetector()
        self.normalizer = StatementNormalizer()
        self.validator = AccountingValidator()
        self.transcriber = get_vision_transcriber()
        self.vision = VisionFallback(self.transcriber)

    def parse_annual_report(
        self,
        pdf_bytes: bytes,
        enterprise_name: str = "",
        stock_code: str = "",
        report_year: Optional[int] = None,
        pdf_url: str = "",
    ) -> PipelineResult:
        # Stage 1
        mineru_result = self.mineru.parse(pdf_bytes)
        extraction_result = {
            "text": mineru_result.get("text", ""),
            "tables": mineru_result.get("tables", []),
            "content_list": mineru_result.get("content_list", []),
            "metadata": {
                **mineru_result.get("metadata", {}),
                "parser_used": "mineru",
                "report_year": report_year,
            },
            "error": mineru_result.get("error", ""),
        }
        if not mineru_result["success"]:
            return PipelineResult(
                success=False,
                enterprise_name=enterprise_name,
                stock_code=stock_code,
                report_year=report_year,
                pdf_url=pdf_url,
                extraction_result=extraction_result,
                error=f"MinerU 解析失败: {mineru_result.get('error')}",
            )

        text = mineru_result["text"]
        tables = mineru_result["tables"]

        # Stage 2：识别三大表，并在开启视觉转录时重新照抄
        detected = self.detector.detect(tables, text)
        total_pages = mineru_result.get("metadata", {}).get("page_count", 0)
        if settings.ENABLE_VISION_STAGE2:
            detected = self._transcribe_detected_tables(
                pdf_bytes,
                detected,
                text,
                total_pages,
            )

        statements = FinancialStatementData(
            source_documents=[{
                "source": "巨潮资讯网",
                "title": f"{enterprise_name} {report_year} 年度报告",
                "url": pdf_url,
                "report_year": report_year,
            }],
        )

        missing_tables = []
        for statement_type in ["balance_sheet", "income_statement", "cash_flow"]:
            table = detected.get(statement_type)
            if table is None:
                missing_tables.append(statement_type)
                continue
            df = self.normalizer.normalize(table, statement_type, report_year=report_year)
            if df is None or df.empty:
                missing_tables.append(statement_type)
                continue
            setattr(statements, statement_type, df)

        # Stage 3
        validation = self.validator.validate(statements)

        # Stage 4：对勾稽失败/跨页/宽表做视觉兜底
        stage4_applied = False
        if settings.ENABLE_VISION_STAGE4 and validation["failed"] > 0:
            statements, validation, stage4_applied = self._run_vision_fallback(
                pdf_bytes,
                statements,
                detected,
                validation,
                text,
                total_pages,
                report_year=report_year,
            )

        main_table_coverage = f"{sum(getattr(statements, t) is not None for t in ['balance_sheet', 'income_statement', 'cash_flow'])}/3"
        rule_family_coverage = self._rule_family_coverage(validation)

        return PipelineResult(
            success=statements.income_statement is not None or statements.balance_sheet is not None,
            enterprise_name=enterprise_name,
            stock_code=stock_code,
            report_year=report_year,
            pdf_url=pdf_url,
            statements=statements,
            extraction_result=extraction_result,
            auto_judgment_rate=validation["auto_judgment_rate"],
            main_table_coverage=main_table_coverage,
            rule_family_coverage=rule_family_coverage,
            issues=missing_tables + validation["findings"],
            needs_human_review=validation["failed"] > 0 or bool(missing_tables),
            digital_reach_rate=self._digital_reach_rate(statements),
        )

    def _transcribe_detected_tables(
        self,
        pdf_bytes: bytes,
        detected: Dict[str, ParsedTable],
        text: str,
        total_pages: int,
    ) -> Dict[str, ParsedTable]:
        """使用 MiniCPM-V 对检测到的三大表候选重新照抄。

        仅当能估算出有效页码时才调用视觉模型；转录失败或结果为空时
        保持 MinerU 原始表格作为降级。
        """
        statement_keywords = {
            "income_statement": "合并利润表",
            "balance_sheet": "合并资产负债表",
            "cash_flow": "合并现金流量表",
        }
        for statement_type, table in detected.items():
            keyword = statement_keywords.get(statement_type, "")
            pages = estimate_pages_for_statement(text, keyword, total_pages)
            if not pages:
                table.notes.append(f"Stage2 视觉转录跳过：无法估算 {statement_type} 页码")
                continue

            table.pages = pages
            transcribed = self.transcriber.transcribe_table(
                pdf_bytes,
                table,
                statement_type,  # type: ignore[arg-type]
            )
            # 视觉转录器失败时通常直接返回原 table，需通过 source 区分是否真正发生转录
            vision_sources = ("vision_openai", "vision_minicpmv")
            if (
                transcribed.source in vision_sources
                and transcribed.rows
                and len(transcribed.rows) >= 2
            ):
                detected[statement_type] = transcribed
                logger.info(
                    "Stage2 MiniCPM-V 转录 %s 成功，原 %d 行 -> 新 %d 行",
                    statement_type,
                    len(table.rows),
                    len(transcribed.rows),
                )
            else:
                table.notes.append(
                    f"Stage2 视觉转录 {statement_type} 未返回有效表格，保持 MinerU 结果"
                )
        return detected

    def _run_vision_fallback(
        self,
        pdf_bytes: bytes,
        statements: FinancialStatementData,
        detected: Dict[str, ParsedTable],
        validation: Dict[str, Any],
        text: str,
        total_pages: int,
        report_year: Optional[int] = None,
    ) -> tuple:
        """Stage 4：对校验失败的三大表调用视觉兜底，重新转录并再校验。"""
        statement_types = ["balance_sheet", "income_statement", "cash_flow"]
        statement_keywords = {
            "income_statement": "合并利润表",
            "balance_sheet": "合并资产负债表",
            "cash_flow": "合并现金流量表",
        }
        categories = validation.get("categories", {})
        applied = False

        for statement_type in statement_types:
            cat = categories.get(statement_type, {})
            if cat.get("failed", 0) == 0:
                continue
            table = detected.get(statement_type)
            if table is None:
                continue

            # Stage 4 需要页码；若 Stage 2 未提供，则根据文本估算
            if not table.pages and not table.page:
                keyword = statement_keywords.get(statement_type, "")
                pages = estimate_pages_for_statement(text, keyword, total_pages)
                if not pages:
                    table.notes.append(f"Stage4 视觉兜底跳过：无法估算 {statement_type} 页码")
                    continue
                table.pages = pages

            transcribed = self.vision.fallback(pdf_bytes, table, statement_type)  # type: ignore[arg-type]
            if transcribed.source in ("vision_openai", "vision_minicpmv"):
                applied = True
                df = self.normalizer.normalize(transcribed, statement_type, report_year=report_year)
                if df is not None and not df.empty:
                    setattr(statements, statement_type, df)

        if applied:
            validation = self.validator.validate(statements)
        return statements, validation, applied

    @staticmethod
    def _rule_family_coverage(validation: Dict[str, Any]) -> str:
        """规则族覆盖率：已判定（通过 + 失败）/ 总规则数。"""
        total = validation.get("total", 0)
        decided = validation.get("passed", 0) + validation.get("failed", 0)
        return f"{decided}/{total}"

    @staticmethod
    def _digital_reach_rate(statements: FinancialStatementData) -> float:
        """数字触达率：三大表非空字段占比的粗略估计。"""
        counts = []
        for st in ["balance_sheet", "income_statement", "cash_flow"]:
            df = getattr(statements, st)
            if df is None or df.empty:
                counts.append(0.0)
                continue
            numeric_cols = [c for c in df.columns if re.match(r"^20\d{2}$", str(c))]
            if not numeric_cols:
                counts.append(0.0)
                continue
            total_cells = len(df) * len(numeric_cols)
            filled_cells = df[numeric_cols].notna().sum().sum()
            counts.append(filled_cells / total_cells if total_cells else 0.0)
        return sum(counts) / len(counts) if counts else 0.0


def parse_annual_report_pdf(
    pdf_bytes: bytes,
    enterprise_name: str = "",
    stock_code: str = "",
    report_year: Optional[int] = None,
    pdf_url: str = "",
) -> PipelineResult:
    """便捷入口。"""
    pipeline = FinancialPdfPipeline()
    return pipeline.parse_annual_report(
        pdf_bytes=pdf_bytes,
        enterprise_name=enterprise_name,
        stock_code=stock_code,
        report_year=report_year,
        pdf_url=pdf_url,
    )


# ── 下游兼容 helper ─────────────────────────────────────────────

FIELD_TO_CHINESE_LABEL = {
    **{v: k for k, v in INCOME_STATEMENT_FIELDS.items()},
    **{v: k for k, v in BALANCE_SHEET_FIELDS.items()},
    **{v: k for k, v in CASH_FLOW_FIELDS.items()},
}


def _statement_to_standard_dataframe(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """把 pipeline 内部 DataFrame（field/label/year）转成 Rebecca 认识的中文科目表。"""
    if df is None or df.empty:
        return None
    if "field" not in df.columns or "label" not in df.columns:
        return None
    year_cols = [c for c in df.columns if re.match(r"^20\d{2}$", str(c))]
    if not year_cols:
        return None
    records = []
    for _, row in df.iterrows():
        label = str(row.get("label") or FIELD_TO_CHINESE_LABEL.get(str(row.get("field")), ""))
        if not label:
            continue
        record = {"项目": label}
        for year in year_cols:
            record[str(year)] = row.get(year)
        records.append(record)
    if not records:
        return None
    return pd.DataFrame(records)


def pipeline_statements_to_standard_dataframes(
    statements: FinancialStatementData,
) -> Dict[str, Optional[pd.DataFrame]]:
    """把 pipeline 输出的 statements 转成标准中文科目 DataFrame 字典。"""
    return {
        "income_statement": _statement_to_standard_dataframe(statements.income_statement),
        "balance_sheet": _statement_to_standard_dataframe(statements.balance_sheet),
        "cash_flow": _statement_to_standard_dataframe(statements.cash_flow),
    }
