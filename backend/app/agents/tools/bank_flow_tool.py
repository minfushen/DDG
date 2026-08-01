"""银行流水数据模型与解析器。

设计目标：
- 与年报三大表解耦，作为独立的「资金流水」数据源接入。
- 支持 CSV / Excel / JSON 三种入口；当前阶段以 JSON mock 样例为主，
  真实源（客户经理上传 Excel、银企直连 API）后续通过同一接口接入。
- 解析结果统一为 ``BankFlowData``，供 ``flow_reconciliation`` 做交叉核验。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BankFlowTransaction:
    """单笔银行流水。"""

    date: str                      # 交易日期 YYYY-MM-DD
    summary: str = ""             # 摘要 / 备注
    counterparty: str = ""        # 交易对手方
    debit: float = 0.0            # 借方发生额（资金流出）
    credit: float = 0.0           # 贷方发生额（资金流入）
    balance: float = 0.0          # 交易后余额
    is_related_party: bool = False  # 是否关联方往来


@dataclass
class BankFlowAccount:
    """单个银行账户的流水。"""

    account_no: str
    bank_name: str = ""
    currency: str = "CNY"
    period_start: str = ""
    period_end: str = ""
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    transactions: List[BankFlowTransaction] = field(default_factory=list)


@dataclass
class BankFlowData:
    """企业多账户银行流水集合。"""

    enterprise_name: str
    accounts: List[BankFlowAccount] = field(default_factory=list)
    source_file: str = ""
    note: str = ""

    def is_empty(self) -> bool:
        return not self.accounts

    def all_transactions(self) -> List[BankFlowTransaction]:
        txns: List[BankFlowTransaction] = []
        for acc in self.accounts:
            txns.extend(acc.transactions)
        return txns

    def total_closing_balance(self) -> float:
        return sum(acc.closing_balance for acc in self.accounts)

    def total_credit(self) -> float:
        return sum(t.credit for t in self.all_transactions())

    def total_debit(self) -> float:
        return sum(t.debit for t in self.all_transactions())


# 列名别名映射（中文 + 常见英文），用于解析时自动识别字段。
_COLUMN_ALIASES = {
    "date": ["日期", "交易日期", "记账日期", "date", "trade_date", "posting_date"],
    "summary": ["摘要", "备注", "用途", "summary", "remark", "note", "description", "memo"],
    "counterparty": ["交易对手", "对手方", "对方户名", "counterparty", "opposite", "counterparty_name"],
    "debit": ["借方", "借方发生额", "支出", "付出", "debit", "amount_out", "expense"],
    "credit": ["贷方", "贷方发生额", "收入", "存入", "credit", "amount_in", "income"],
    "balance": ["余额", "账户余额", "期末余额", "balance", "ending_balance"],
    "is_related_party": ["关联方", "related_party", "is_related_party", "is_related"],
}

# 经营性销售回款关键词（用于从贷方发生额中识别销售回款）。
_OPERATING_CREDIT_KEYWORDS = [
    "货款", "回款", "销售", "营业收入", "收款", "结算", "应收账款", "销项",
]
# 非经营性贷方关键词（从贷方中剔除）。
_NON_OPERATING_CREDIT_KEYWORDS = [
    "借款", "拆借", "往来", "投资", "理财", "退款", "补贴", "退税", "贴现", "增资", "注资",
]
# 经营性借方关键词（采购/工资/税费/费用）。
_OPERATING_DEBIT_KEYWORDS = [
    "采购", "付款", "工资", "薪酬", "税费", "税金", "社保", "费", "报销", "加工", "原料", "材料",
]
# 非经营性借方关键词（投资/筹资/分红）。
_NON_OPERATING_DEBIT_KEYWORDS = [
    "购建", "投资", "还款", "还本", "分红", "股息", "放贷", "拆借", "购设备", "置办",
]


def _normalize_number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("，", "")
    if not text or text in {"-", "--", "N/A", "nan", "None"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _match_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    lowered = {str(c).strip(): c for c in columns}
    lowered_lower = {k.lower(): v for k, v in lowered.items()}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
        if alias.lower() in lowered_lower:
            return lowered_lower[alias.lower()]
    return None


def _txn_from_row(row: Dict[str, Any], col_map: Dict[str, Optional[str]]) -> BankFlowTransaction:
    def _get(key: str) -> Any:
        col = col_map.get(key)
        return row.get(col) if col else None

    related = _get("is_related_party")
    if isinstance(related, str):
        related = related.strip() in {"1", "true", "True", "是", "Y", "yes"}
    elif related is None:
        related = False

    return BankFlowTransaction(
        date=str(_get("date") or "").strip(),
        summary=str(_get("summary") or "").strip(),
        counterparty=str(_get("counterparty") or "").strip(),
        debit=_normalize_number(_get("debit")),
        credit=_normalize_number(_get("credit")),
        balance=_normalize_number(_get("balance")),
        is_related_party=bool(related),
    )


def _account_from_dict(acc: Dict[str, Any]) -> BankFlowAccount:
    rows = acc.get("transactions") or []
    if rows and isinstance(rows[0], dict):
        columns = list(rows[0].keys())
        col_map = {k: _match_column(columns, aliases) for k, aliases in _COLUMN_ALIASES.items()}
        txns = [_txn_from_row(r, col_map) for r in rows]
    else:
        txns = []
    return BankFlowAccount(
        account_no=str(acc.get("account_no") or acc.get("account") or "").strip(),
        bank_name=str(acc.get("bank_name") or acc.get("bank") or "").strip(),
        currency=str(acc.get("currency") or "CNY").strip(),
        period_start=str(acc.get("period_start") or acc.get("start") or "").strip(),
        period_end=str(acc.get("period_end") or acc.get("end") or "").strip(),
        opening_balance=_normalize_number(acc.get("opening_balance") or acc.get("opening")),
        closing_balance=_normalize_number(acc.get("closing_balance") or acc.get("closing") or acc.get("ending_balance")),
        transactions=txns,
    )


def bank_flow_from_dict(data: Dict[str, Any]) -> BankFlowData:
    """从字典（JSON 结构）构造 ``BankFlowData``。"""
    accounts = [_account_from_dict(a) for a in (data.get("accounts") or [])]
    return BankFlowData(
        enterprise_name=str(data.get("enterprise_name") or "").strip(),
        accounts=accounts,
        source_file=str(data.get("source_file") or ""),
        note=str(data.get("note") or ""),
    )


def load_bank_flow_json(path: str) -> BankFlowData:
    """加载 JSON 格式的银行流水（mock 样例或已落盘结果）。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bfd = bank_flow_from_dict(data)
    bfd.source_file = os.path.basename(path)
    return bfd


def parse_bank_flow_file(path: str) -> BankFlowData:
    """根据扩展名解析 CSV / Excel / JSON 为 ``BankFlowData``。

    当前阶段以 JSON mock 为主；CSV/Excel 解析复用 pandas，缺失依赖时优雅降级。
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return load_bank_flow_json(path)

    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        raise RuntimeError("解析 CSV/Excel 需安装 pandas")

    if ext in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"不支持的流水文件类型：{ext}")

    rows = df.where(df.notna(), None).to_dict(orient="records")
    columns = list(df.columns)
    col_map = {k: _match_column(columns, aliases) for k, aliases in _COLUMN_ALIASES.items()}
    txns = [_txn_from_row(r, col_map) for r in rows]
    # 单账户模式：整张表视为一个账户。
    account = BankFlowAccount(
        account_no=str(df.get("账户", "unknown")),
        transactions=txns,
    )
    bfd = BankFlowData(enterprise_name="", accounts=[account], source_file=os.path.basename(path))
    return bfd


def classify_flow_roles(bfd: BankFlowData) -> Dict[str, float]:
    """将流水分类汇总，供核验引擎使用。

    返回：operating_credit（销售回款贷方）、non_operating_credit（非经营贷方）、
    operating_debit（经营借方）、non_operating_debit（非经营借方）、
    related_party_flow（关联方往来净额）。
    """
    operating_credit = non_operating_credit = 0.0
    operating_debit = non_operating_debit = 0.0
    related_party_flow = 0.0

    for t in bfd.all_transactions():
        summary = t.summary
        is_related = t.is_related_party
        if t.credit > 0:
            if any(k in summary for k in _NON_OPERATING_CREDIT_KEYWORDS) and not is_related:
                non_operating_credit += t.credit
            elif any(k in summary for k in _OPERATING_CREDIT_KEYWORDS) or is_related:
                operating_credit += t.credit
            else:
                # 未明确分类的贷方，默认计入销售回款（保守）。
                operating_credit += t.credit
        if t.debit > 0:
            if any(k in summary for k in _NON_OPERATING_DEBIT_KEYWORDS):
                non_operating_debit += t.debit
            elif any(k in summary for k in _OPERATING_DEBIT_KEYWORDS) or is_related:
                operating_debit += t.debit
            else:
                operating_debit += t.debit
        if is_related:
            related_party_flow += (t.credit - t.debit)

    return {
        "operating_credit": operating_credit,
        "non_operating_credit": non_operating_credit,
        "operating_debit": operating_debit,
        "non_operating_debit": non_operating_debit,
        "related_party_flow": related_party_flow,
    }
