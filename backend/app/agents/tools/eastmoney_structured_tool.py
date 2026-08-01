"""Eastmoney structured data provider (no auth required).

Provides the same output schema as ``cninfo_webapi_tool`` for financial
summary, shareholder profile, company basic info and shareholder table, so
that ``tool_router.py`` can swap the default data source without touching any
downstream consumers (synthesizer / claim_builder).

All requests go to the same Eastmoney F10 datacenter endpoint already used by
``listed_company_tool`` and ``listed_company_public_info_tool`` — no API keys,
no tokens, just ``User-Agent`` + ``Referer`` headers.

Field-name mappings below were validated against live API responses for
stock ``600519.SH`` (贵州茅台) on 2025-06-19.

Endpoints:
- ``RPT_F10_FINANCE_GINCOME``   / ``GBALANCE`` / ``GCASHFLOW`` — 三大表 (already in listed_company_tool)
- ``RPT_F10_FINANCE_MAINFINADATA`` — 财务指标 (ROE, 毛利率, EPS, 资产负债率, 净利率)
- ``RPT_F10_ORG_BASICINFO``    — 公司概况 + 实际控制人
- ``RPT_F10_EH_HOLDERS``       — 十大股东
- ``RPT_F10_EH_EQUITY``        — 股本结构变动
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.agents.tools.listed_company_tool import (
    resolve_listed_company,
    _fetch_eastmoney_report,
    BALANCE_FIELD_MAP,
    CASHFLOW_FIELD_MAP,
    INCOME_FIELD_MAP,
    REPORT_MAP,
    _build_statement,
    _add_gross_profit,
    _add_depreciation_amortization,
    _year_from_report,
)

logger = logging.getLogger(__name__)

EASTMONEY_F10_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://emweb.securities.eastmoney.com/",
}
DEFAULT_TIMEOUT = 20.0

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _fetch_f10(secu_code: str, report_name: str, page_size: int = 10,
               sort_column: str = "", sort_type: str = "-1") -> List[Dict[str, Any]]:
    """Fetch rows from an Eastmoney F10 datacenter endpoint."""
    params: Dict[str, Any] = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECUCODE="{secu_code}")',
        "pageNumber": "1",
        "pageSize": str(page_size),
        "source": "HSF10",
        "client": "PC",
    }
    if sort_column:
        params["sortColumns"] = sort_column
        params["sortTypes"] = sort_type
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.get(EASTMONEY_F10_URL, params=params, headers=HEADERS)
            resp.raise_for_status()
            payload = resp.json()
        result = payload.get("result") or {}
        return result.get("data", []) if isinstance(result, dict) else []
    except Exception as exc:
        logger.warning("eastmoney F10 %s for %s failed: %s", report_name, secu_code, exc)
        return []


def _latest_annual(rows: List[Dict[str, Any]], date_key: str = "REPORT_DATE",
                   type_key: str = "REPORT_TYPE") -> Optional[Dict[str, Any]]:
    """Pick the most recent annual report row (年报 ≥ 12-31)."""
    if not rows:
        return None
    annual = [r for r in rows if "年报" in str(r.get(type_key, ""))]
    if not annual:
        # Fallback: pick rows ending in 12-31 by date string
        annual = [r for r in rows if "12-31" in str(r.get(date_key, ""))]
    if not annual:
        annual = rows
    annual = sorted(annual, key=lambda r: str(r.get(date_key, "")), reverse=True)
    return annual[0] if annual else None


def _latest_date_str(rows: List[Dict[str, Any]], date_key: str = "REPORT_DATE") -> str:
    """Return the most recent report date string from rows."""
    dates = sorted({str(r.get(date_key, "")).strip() for r in rows if r.get(date_key)}, reverse=True)
    return dates[0] if dates else ""


def _secu_code_from(stock_code: str) -> str:
    """Derive SECUCODE (e.g. ``600519.SH``) from a bare stock code."""
    if "." in stock_code:
        return stock_code
    exchange = "SH" if stock_code.startswith("6") else "SZ"
    return f"{stock_code}.{exchange}"


# ──────────────────────────────────────────────────────────────────
# Financial Summary  (schema-compatible with cninfo build_financial_summary)
# ──────────────────────────────────────────────────────────────────

# Eastmoney RPT_F10_FINANCE_MAINFINADATA field mapping.
# Validated: ROEJQ=ROE加权, XSMLL=销售毛利率(%), XSJLL=销售净利率(%),
#   ZCFZL=资产负债率(%), EPSJB=基本每股收益(元), BPS=每股净资产
INDICATOR_FIELD_MAP = {
    "roe": "ROEJQ",
    "gross_margin": "XSMLL",
    "net_margin": "XSJLL",
    "debt_ratio": "ZCFZL",
    "eps": "EPSJB",
}

# Balance sheet field mapping from existing BALANCE_FIELD_MAP (listed_company_tool).
# We reuse it directly via _build_statement, but also need direct key→value
# extraction for the summary dict.
BS_DIRECT_MAP = {
    "total_assets": "TOTAL_ASSETS",
    "total_liabilities": "TOTAL_LIABILITIES",
    "total_equity": "TOTAL_EQUITY",
    "current_assets": "TOTAL_CURRENT_ASSETS",
    "current_liabilities": "TOTAL_CURRENT_LIAB",
    "cash": "MONETARYFUNDS",
    "accounts_receivable": "ACCOUNTS_RECE",
    "inventory": "INVENTORY",
    "fixed_assets": "FIXED_ASSET",
    "short_term_borrowing": "SHORT_LOAN",
    "long_term_borrowing": "LONG_LOAN",
    "retained_earnings": None,  # Eastmoney GBALANCE may not have this; compute or leave None
}

CF_DIRECT_MAP = {
    "operating": "NETCASH_OPERATE",
    "investing": "NETCASH_INVEST",
    "financing": "NETCASH_FINANCE",
}


def eastmoney_build_financial_summary(
    stock_code: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a financial summary from Eastmoney F10 data.

    Output schema is 1:1 compatible with ``cninfo_webapi_tool.build_financial_summary``:
    ``success``, ``stock_code``, ``report_date``, ``balance_sheet``, ``cash_flow``,
    ``indicators`` — all the same key names so downstream code works unchanged.
    """
    secu_code = _secu_code_from(stock_code)

    # Fetch three major statements via listed_company_tool infrastructure.
    try:
        income_rows = _fetch_eastmoney_report(secu_code, REPORT_MAP["income_statement"])
        balance_rows = _fetch_eastmoney_report(secu_code, REPORT_MAP["balance_sheet"])
        cash_rows = _fetch_eastmoney_report(secu_code, REPORT_MAP["cash_flow"])
        indicator_rows = _fetch_f10(secu_code, "RPT_F10_FINANCE_MAINFINADATA", page_size=5,
                                   sort_column="REPORT_DATE", sort_type="-1")
    except Exception as exc:
        return {
            "success": False,
            "error": f"东方财富财报接口调用失败：{type(exc).__name__}: {exc}",
            "stock_code": stock_code,
            "report_date": report_date,
            "balance_sheet": {},
            "cash_flow": {},
            "indicators": {},
        }

    if not income_rows and not balance_rows and not cash_rows and not indicator_rows:
        return {
            "success": False,
            "error": "东方财富未返回有效财报数据",
            "stock_code": stock_code,
            "report_date": report_date,
            "balance_sheet": {},
            "cash_flow": {},
            "indicators": {},
        }

    # Pick latest annual record from each source.
    # For balance/cash, the data is in raw F10 format (one row per year).
    bs_annual = _latest_annual(balance_rows, date_key="REPORT_DATE")
    cf_annual = _latest_annual(cash_rows, date_key="REPORT_DATE")
    ind_annual = _latest_annual(indicator_rows, date_key="REPORT_DATE")

    resolved_date = (
        _date_str_from_row(ind_annual, "REPORT_DATE")
        or _date_str_from_row(bs_annual, "REPORT_DATE")
        or _date_str_from_row(cf_annual, "REPORT_DATE")
        or report_date
        or ""
    )

    # Build balance_sheet dict (same keys as cninfo).
    bs: Dict[str, Optional[float]] = {}
    if bs_annual:
        for key, field in BS_DIRECT_MAP.items():
            if field:
                bs[key] = _to_float(bs_annual.get(field))

    # Build cash_flow dict (same keys as cninfo).
    cf: Dict[str, Optional[float]] = {}
    if cf_annual:
        for key, field in CF_DIRECT_MAP.items():
            cf[key] = _to_float(cf_annual.get(field))

    # Build indicators dict (same keys as cninfo).
    ind: Dict[str, Optional[float]] = {}
    if ind_annual:
        for key, field in INDICATOR_FIELD_MAP.items():
            ind[key] = _to_float(ind_annual.get(field))

    # current_ratio not available in MAINFINADATA directly; compute from BS.
    ind["current_ratio"] = _safe_div(bs.get("current_assets"), bs.get("current_liabilities"))

    return {
        "success": True,
        "stock_code": stock_code,
        "report_date": resolved_date,
        "balance_sheet": bs,
        "cash_flow": cf,
        "indicators": ind,
    }


def _date_str_from_row(row: Optional[Dict], key: str = "REPORT_DATE") -> Optional[str]:
    if not row:
        return None
    val = str(row.get(key, "")).strip()
    return val[:10] if val else None


# ──────────────────────────────────────────────────────────────────
# Company Basic Info  (schema-compatible with cninfo fetch_company_basic_info)
# ──────────────────────────────────────────────────────────────────

def eastmoney_fetch_company_basic_info(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch company basic info + actual controller from Eastmoney F10.

    Output schema is compatible with ``cninfo_webapi_tool.fetch_company_basic_info``:
    ``success``, ``records`` list with ``company_name``, ``stock_name``,
    ``stock_code``, ``actual_controller``, ``controller_type``,
    ``controller_shareholding``.

    The ``actual_controller`` field is populated from ORG_BASICINFO's
    ``REAL_CONTROLER`` column.  The cninfo consumer at ``tool_router.py:468``
    reads ``records[-1].F004V`` — we store the controller name at the same
    logical position so downstream code works without changes.
    """
    secu_code = _secu_code_from(stock_code)
    try:
        basic_rows = _fetch_f10(secu_code, "RPT_F10_ORG_BASICINFO", page_size=3)
    except Exception as exc:
        return {
            "success": False,
            "error": f"东方财富公司概况接口调用失败：{type(exc).__name__}: {exc}",
            "records": [],
        }

    if not basic_rows:
        return {
            "success": False,
            "error": "东方财富未返回公司基础信息",
            "records": [],
        }

    row = basic_rows[0]
    company_name = str(row.get("ORG_NAME") or "")
    stock_name = str(row.get("SECURITY_NAME_ABBR") or "")
    real_controller = str(row.get("REAL_CONTROLER") or "")
    control_holder = str(row.get("CONTROL_HOLDER") or "")

    if not company_name:
        return {
            "success": False,
            "error": "东方财富返回的公司名称为空",
            "records": [],
        }

    return {
        "success": True,
        "error": "",
        "records": [{
            "company_name": company_name,
            "stock_name": stock_name,
            "stock_code": stock_code,
            # F004V compatibility: cninfo tool_router/synthesizer reads
            # records[-1].F004V for actual controller name.
            "F004V": real_controller,
            "actual_controller": real_controller,
            "control_holder": control_holder,
            "controller_type": str(row.get("CONTROL_DIRECT_RATIO") or ""),
            "controller_shareholding": _to_float(row.get("CONTROL_DIRECT_RATIO")),
        }],
    }


# ──────────────────────────────────────────────────────────────────
# Shareholder Profile  (schema-compatible with cninfo build_shareholder_profile)
# ──────────────────────────────────────────────────────────────────

def eastmoney_build_shareholder_profile(stock_code: str) -> Dict[str, Any]:
    """Build a shareholder profile from Eastmoney F10.

    Output schema is compatible with ``cninfo_webapi_tool.build_shareholder_profile``:
    ``stock_code``, ``top_shareholders`` (``{count, records}``),
    ``actual_controller`` (``{count, records}``),
    ``share_capital_changes`` (``{count, records}``).
    """
    secu_code = _secu_code_from(stock_code)
    try:
        holder_rows = _fetch_f10(secu_code, "RPT_F10_EH_HOLDERS", page_size=15,
                                 sort_column="END_DATE", sort_type="-1")
        equity_rows = _fetch_f10(secu_code, "RPT_F10_EH_EQUITY", page_size=10,
                                 sort_column="END_DATE", sort_type="-1")
        basic_rows = _fetch_f10(secu_code, "RPT_F10_ORG_BASICINFO", page_size=1)
    except Exception as exc:
        return {
            "success": False,
            "error": f"东方财富股东接口调用失败：{type(exc).__name__}: {exc}",
            "stock_code": stock_code,
            "top_shareholders": {"count": 0, "records": []},
            "actual_controller": {"count": 0, "records": []},
            "share_capital_changes": {"count": 0, "records": []},
        }

    # top_shareholders: filter latest period, take top 10
    holder_dates = sorted({str(r.get("END_DATE", "")) for r in holder_rows if r.get("END_DATE")}, reverse=True)
    latest_holder_date = holder_dates[0] if holder_dates else ""
    latest_holders = [r for r in holder_rows if str(r.get("END_DATE", "")) == latest_holder_date][:10]

    # Normalize holder records to cninfo-compatible format.
    normalized_holders = []
    for r in latest_holders:
        normalized_holders.append({
            "HOLDER_NAME": r.get("HOLDER_NAME"),
            "HOLD_NUM_RATIO": r.get("HOLD_NUM_RATIO"),
            "HOLD_NUM": r.get("HOLD_NUM"),
            "HOLDER_RANK": r.get("HOLDER_RANK"),
            "HOLDER_STATE": r.get("HOLDER_STATE"),  # 质押/冻结状态
            "END_DATE": r.get("END_DATE"),
        })

    # actual_controller from ORG_BASICINFO
    ctrl_record = {}
    if basic_rows:
        ctrl_record = {
            # F004V compatibility: same field code as cninfo.
            "F004V": basic_rows[0].get("REAL_CONTROLER", ""),
            "controller_name": basic_rows[0].get("REAL_CONTROLER", ""),
            "control_holder": basic_rows[0].get("CONTROL_HOLDER", ""),
            "control_direct_ratio": basic_rows[0].get("CONTROL_DIRECT_RATIO", ""),
            "control_indirect_ratio": basic_rows[0].get("CONTROL_INDIRECT_RATIO", ""),
        }

    # share_capital_changes
    normalized_equity = []
    for r in equity_rows:
        normalized_equity.append({
            "END_DATE": r.get("END_DATE"),
            "CHANGE_REASON": r.get("CHANGE_REASON"),
            "FREE_SHARES": r.get("FREE_SHARES"),
            "LIMITED_A_SHARES": r.get("LIMITED_A_SHARES"),
        })

    return {
        "success": True,
        "stock_code": stock_code,
        "top_shareholders": {
            "count": len(normalized_holders),
            "records": normalized_holders,
        },
        "actual_controller": {
            "count": 1 if ctrl_record.get("F004V") else 0,
            "records": [ctrl_record] if ctrl_record.get("F004V") else [],
        },
        "share_capital_changes": {
            "count": len(normalized_equity),
            "records": normalized_equity,
        },
    }


# ──────────────────────────────────────────────────────────────────
# Shareholder Table  (schema-compatible with cninfo build_shareholder_table)
# ──────────────────────────────────────────────────────────────────

def eastmoney_build_shareholder_table(stock_code: str) -> Dict[str, Any]:
    """Build a structured shareholder table for report rendering.

    Output schema is compatible with ``cninfo_webapi_tool.build_shareholder_table``:
    ``success``, ``stock_code``, ``report_date``, ``columns``, ``rows``.
    Row keys: 股东名称, 股东性质, 持股比例, 持股数量, 质押/冻结.
    """
    secu_code = _secu_code_from(stock_code)
    try:
        holder_rows = _fetch_f10(secu_code, "RPT_F10_EH_HOLDERS", page_size=20,
                                 sort_column="END_DATE", sort_type="-1")
    except Exception as exc:
        return {
            "success": False,
            "stock_code": stock_code,
            "rows": [],
            "error": f"东方财富十大股东接口调用失败：{type(exc).__name__}: {exc}",
        }

    if not holder_rows:
        return {"success": False, "stock_code": stock_code, "rows": []}

    # Find latest reporting period.
    dates = sorted({str(r.get("END_DATE", "")) for r in holder_rows if r.get("END_DATE")}, reverse=True)
    if not dates:
        return {"success": False, "stock_code": stock_code, "rows": []}
    latest_date = dates[0]
    latest = [r for r in holder_rows if str(r.get("END_DATE", "")) == latest_date]

    rows = []
    for r in latest[:10]:
        holder_state = str(r.get("HOLDER_STATE") or "")
        pledge_text = holder_state if holder_state and holder_state not in ("正常", "无", "") else "无"
        hold_ratio = _to_float(r.get("HOLD_NUM_RATIO"))
        hold_num = _to_float(r.get("HOLD_NUM"))

        rows.append({
            "股东名称": str(r.get("HOLDER_NAME") or ""),
            "股东性质": "机构" if r.get("IS_HOLDORG") == "1" else "个人",
            "持股比例": f"{hold_ratio:.2f}%" if hold_ratio is not None else "数据不可用",
            "持股数量": int(hold_num) if hold_num is not None else 0,
            "质押/冻结": pledge_text,
        })

    # Sort by shareholding ratio descending.
    def _sort_key(row: Dict) -> float:
        text = str(row.get("持股比例", "0")).rstrip("%").strip()
        try:
            return float(text)
        except (TypeError, ValueError):
            return 0.0

    rows.sort(key=_sort_key, reverse=True)

    return {
        "success": True,
        "stock_code": stock_code,
        "report_date": latest_date[:10] if latest_date else "",
        "columns": ["股东名称", "股东性质", "持股比例", "持股数量", "质押/冻结"],
        "rows": rows,
    }


# ──────────────────────────────────────────────────────────────────
# Business Narrative (主营构成 + 经营情况讨论与分析)
# 用于在无年报 PDF 解析时替代 PDF 的 main_business_rows 与
# sections.business_review，保证财务深度叙述（主营分部 / 经营讨论 /
# LLM 归因）仍可生成。数据全部来自东方财富 F10 公开接口，无需鉴权。
# ──────────────────────────────────────────────────────────────────

def _format_amount(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 100000000:
        return f"{number / 100000000:.2f}亿元"
    if abs(number) >= 10000:
        return f"{number / 10000:.2f}万元"
    return f"{number:.2f}元"


def _format_percent(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1:
        number *= 100
    return f"{number:.2f}%"


def _eastmoney_main_business(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """主营构成（RPT_F10_FN_MAINOP）：分行业/分产品/分地区收入与毛利率。

    返回 schema 与 PDF main_business_rows / listed_company_public_info_tool
    一致（item_name / income / income_ratio / gross_margin / rank），
    以便下游 _segment_summary 与财务叙述器无缝复用。
    """
    annual = [row for row in rows if "年报" in str(row.get("REPORT_NAME", ""))]
    latest_report = next((row.get("REPORT_NAME") for row in annual), None)
    selected = [row for row in annual if row.get("REPORT_NAME") == latest_report] if latest_report else (annual or rows)[:8]
    business: List[Dict[str, Any]] = []
    for row in selected[:10]:
        item_name = str(row.get("ITEM_NAME") or "").strip()
        if not item_name:
            continue
        business.append({
            "report_name": row.get("REPORT_NAME"),
            "item_name": item_name,
            "income": _format_amount(row.get("MAIN_BUSINESS_INCOME")),
            "income_ratio": _format_percent(row.get("MBI_RATIO")),
            "gross_margin": _format_percent(row.get("GROSS_RPOFIT_RATIO")),
            "rank": row.get("RANK") or row.get("RANKNEW"),
        })
    return business


def _eastmoney_latest_business_review(rows: List[Dict[str, Any]], limit: int = 1800) -> str:
    """经营情况讨论与分析原文（RPT_F10_OP_BUSINESSANALYSIS 年报）。"""
    annual = [row for row in rows if "年报" in str(row.get("REPORT_NAME", ""))]
    row = (annual or rows or [{}])[0]
    text = str(row.get("BUSINESS_REVIEW") or "").strip()
    # 折叠多余空白，保留语义完整性
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def eastmoney_fetch_business_narrative(stock_code: str) -> Dict[str, Any]:
    """从东方财富 F10 获取主营构成 + 经营讨论原文，作为 PDF 管道的替代数据源。

    返回：
        {
            "success": bool,
            "stock_code": str,
            "business_segments": List[Dict],   # 主营构成明细
            "business_review": str,            # 经营情况讨论与分析原文
            "error": str,
        }
    """
    secu_code = _secu_code_from(stock_code)
    try:
        mainop_rows = _fetch_f10(secu_code, "RPT_F10_FN_MAINOP", page_size=60)
        business_rows = _fetch_f10(secu_code, "RPT_F10_OP_BUSINESSANALYSIS", page_size=6)
    except Exception as exc:
        logger.warning("东方财富 F10 主营/经营分析接口失败（%s）：%s", stock_code, exc)
        return {
            "success": False,
            "stock_code": stock_code,
            "business_segments": [],
            "business_review": "",
            "error": f"{type(exc).__name__}: {exc}",
        }

    business_segments = _eastmoney_main_business(mainop_rows)
    business_review = _eastmoney_latest_business_review(business_rows)
    return {
        "success": bool(business_segments or business_review),
        "stock_code": stock_code,
        "business_segments": business_segments,
        "business_review": business_review,
        "error": "",
    }


# ──────────────────────────────────────────────────────────────────
# Composite: Financial + Shareholder + Business (for tool_router fallback)
# ──────────────────────────────────────────────────────────────────

def eastmoney_fetch_business_data(stock_code: str) -> Dict[str, Any]:
    """Combined business data call: basic info + shareholder profile + table.

    Mirrors the cninfo ``_fetch_cninfo_basic`` structure used in tool_router.py.
    """
    basic = eastmoney_fetch_company_basic_info(stock_code)
    shareholders = eastmoney_build_shareholder_profile(stock_code)
    shareholder_table = eastmoney_build_shareholder_table(stock_code)
    return {
        "basic": basic,
        "shareholders": shareholders,
        "shareholder_table": shareholder_table,
    }
