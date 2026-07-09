"""Cninfo WebAPI structured data provider.

Uses the deep证信 data service platform (webapi.cninfo.com.cn) to fetch
structured financial statements, shareholder info, legal events, and
announcement metadata for A-share listed companies.

Free-tier APIs used:
- p_stock2300: Balance sheet (资产负债表)
- p_stock2302: Cash flow statement (现金流量表)
- p_stock2303: Financial indicators (财务指标表)
- p_stock2210: Top 10 shareholders (十大股东)
- p_stock2213: Actual controller (实际控制人)
- p_stock2215: Share capital changes (股本变动)
- p_stock2245: External guarantees (对外担保)
- p_stock2246: Litigation (公司诉讼)
- p_stock2248: Penalties (受处罚表)
- p_stock2249: Asset freezes (资产冻结)
- p_stock2250: Arbitration (仲裁)
- p_info3015: Announcement metadata (公告基本信息)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings
from app.agents.tools.cninfo_token_manager import (
    get_cninfo_access_token,
    invalidate_cninfo_token,
)

logger = logging.getLogger(__name__)

CNINFO_WEBAPI_BASE = "http://webapi.cninfo.com.cn/api"
DEFAULT_TIMEOUT = 30.0

_TOKEN_NOT_CONFIGURED = {
    "success": False,
    "error_code": "TOKEN_MISSING",
    "error_msg": "CNINFO_ACCESS_TOKEN is not configured in settings/.env",
    "records": [],
}

# Result codes that indicate an expired/invalid token; on these we invalidate
# the cached token so the next call re-fetches via the token manager.
_TOKEN_EXPIRED_CODES = {"401", "403", "token_invalid", "TOKEN_INVALID", "expired"}


def _get_access_token() -> Optional[str]:
    """Get access token via the token manager (auto-refresh) or legacy static.

    Resolution order (see ``cninfo_token_manager``):
    1. Access Key/Secret configured → OAuth2 refresh + cache.
    2. Legacy static ``CNINFO_ACCESS_TOKEN`` → returned as-is.
    3. Nothing configured → None.
    """
    token = get_cninfo_access_token()
    if not token:
        logger.warning(
            "CNINFO token not configured (set CNINFO_ACCESS_KEY/SECRET for auto-refresh "
            "or CNINFO_ACCESS_TOKEN for static fallback); cninfo_webapi calls will be skipped"
        )
        return None
    return token


def _request_api(
    api_path: str,
    params: Dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Call a cninfo webapi endpoint and return the parsed JSON response.

    On token-expiry result codes the cached token is invalidated and the
    request retried once with a freshly refreshed token.
    """
    token = _get_access_token()
    if not token:
        return _TOKEN_NOT_CONFIGURED

    result = _do_request(api_path, params, token, timeout)

    # If the token looks expired, refresh once and retry.
    if not result.get("success") and str(result.get("error_code")) in _TOKEN_EXPIRED_CODES:
        logger.info("cninfo API %s returned token-expiry code %s; refreshing and retrying once",
                    api_path, result.get("error_code"))
        invalidate_cninfo_token()
        new_token = _get_access_token()
        if new_token and new_token != token:
            result = _do_request(api_path, params, new_token, timeout)

    return result


def _do_request(
    api_path: str,
    params: Dict[str, Any],
    token: str,
    timeout: float,
) -> Dict[str, Any]:
    """Single cninfo webapi GET (no retry logic)."""
    query = {**params, "access_token": token, "format": "json"}
    url = f"{CNINFO_WEBAPI_BASE}/{api_path}"

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params=query)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("cninfo API %s returned HTTP %s: %s", api_path, exc.response.status_code, exc.response.text[:200])
        return {"success": False, "error_code": str(exc.response.status_code), "error_msg": str(exc), "records": []}
    except Exception as exc:
        logger.warning("cninfo API %s request failed: %s", api_path, exc)
        return {"success": False, "error_code": "REQUEST_ERROR", "error_msg": str(exc), "records": []}

    result_code = data.get("resultcode")
    if result_code and str(result_code) != "200":
        return {
            "success": False,
            "error_code": result_code,
            "error_msg": data.get("resultmsg", ""),
            "records": [],
        }

    return {
        "success": True,
        "total": data.get("total", 0),
        "records": data.get("records", []),
    }


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


# ──────────────────────────────────────────────────────────────
# Financial Statements
# ──────────────────────────────────────────────────────────────

def fetch_balance_sheet(
    stock_code: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch balance sheet (资产负债表) for a stock.

    Args:
        stock_code: e.g. "600519"
        report_date: e.g. "2024-12-31", omit for all periods
    """
    params: Dict[str, Any] = {"scode": stock_code}
    if report_date:
        params["rdate"] = report_date
    return _request_api("stock/p_stock2300", params)


def fetch_cash_flow(
    stock_code: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch cash flow statement (现金流量表)."""
    params: Dict[str, Any] = {"scode": stock_code}
    if report_date:
        params["rdate"] = report_date
    return _request_api("stock/p_stock2302", params)


def fetch_financial_indicators(
    stock_code: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch financial indicators (财务指标表) — ROE, EPS, margins, etc."""
    params: Dict[str, Any] = {"scode": stock_code}
    if report_date:
        params["rdate"] = report_date
    return _request_api("stock/p_stock2303", params)


# ──────────────────────────────────────────────────────────────
# Shareholder & Equity
# ──────────────────────────────────────────────────────────────

def fetch_top_shareholders(
    stock_code: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch top 10 shareholders (十大股东持股情况)."""
    params: Dict[str, Any] = {"scode": stock_code}
    if report_date:
        params["rdate"] = report_date
    return _request_api("stock/p_stock2210", params)


def fetch_actual_controller(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch actual controller info (公司股东实际控制人)."""
    return _request_api("stock/p_stock2213", {"scode": stock_code})


def fetch_share_capital_changes(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch share capital changes (公司股本变动)."""
    return _request_api("stock/p_stock2215", {"scode": stock_code})


# ──────────────────────────────────────────────────────────────
# Legal & Risk Events
# ──────────────────────────────────────────────────────────────

def fetch_litigation(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch litigation records (公司诉讼)."""
    return _request_api("stock/p_stock2246", {"scode": stock_code})


def fetch_guarantees(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch external guarantees (对外担保)."""
    return _request_api("stock/p_stock2245", {"scode": stock_code})


def fetch_penalties(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch penalty records (公司受处罚表)."""
    return _request_api("stock/p_stock2248", {"scode": stock_code})


def fetch_asset_freezes(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch asset freeze records (公司资产冻结表)."""
    return _request_api("stock/p_stock2249", {"scode": stock_code})


def fetch_arbitration(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch arbitration records (公司仲裁)."""
    return _request_api("stock/p_stock2250", {"scode": stock_code})


# ──────────────────────────────────────────────────────────────
# Announcement Metadata
# ──────────────────────────────────────────────────────────────

def fetch_announcement_info(
    stock_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Fetch announcement metadata (公告基本信息).

    Returns announcement IDs, titles, dates, and category codes.
    Use the cninfo_announcement_tool for full-text search and PDF download.
    """
    params: Dict[str, Any] = {
        "scode": stock_code,
        "pagesize": str(page_size),
    }
    if start_date:
        params["sdate"] = start_date
    if end_date:
        params["edate"] = end_date
    return _request_api("info/p_info3015", params)


# ──────────────────────────────────────────────────────────────
# Company Basic Info
# ──────────────────────────────────────────────────────────────

def fetch_company_basic_info(
    stock_code: str,
) -> Dict[str, Any]:
    """Fetch company basic registration info from multiple cninfo APIs.

    Combines data from financial statements (ORGNAME), top shareholders,
    and actual controller to build a basic company profile.
    Returns fields like: company_name, stock_code, actual_controller, etc.
    """
    # Get company name from balance sheet (always has ORGNAME)
    bs = fetch_balance_sheet(stock_code)
    ctrl = fetch_actual_controller(stock_code)

    if not bs.get("success"):
        return {
            "success": False,
            "error": bs.get("error_msg") or "巨潮工商基础信息接口调用失败",
            "records": [],
        }

    bs_record = (bs.get("records") or [{}])[0] if bs.get("success") else {}
    ctrl_record = (ctrl.get("records") or [{}])[-1] if ctrl.get("success") and ctrl.get("records") else {}

    company_name = bs_record.get("ORGNAME") or ""
    stock_name = bs_record.get("SECNAME") or ""

    return {
        "success": bool(company_name),
        "error": "" if company_name else "巨潮工商基础信息未返回公司名称",
        "records": [{
            "company_name": company_name,
            "stock_name": stock_name,
            "stock_code": stock_code,
            "actual_controller": ctrl_record.get("F004V") or "",
            "controller_type": ctrl_record.get("F008V") or "",
            "controller_shareholding": ctrl_record.get("F006N"),
        }],
    }


# ──────────────────────────────────────────────────────────────
# Composite: Financial Summary
# ──────────────────────────────────────────────────────────────

def build_financial_summary(
    stock_code: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a consolidated financial summary from multiple APIs.

    Returns a dict with keys: balance_sheet, cash_flow, indicators, plus
    ``success``/``error`` so callers can tell a genuine empty result from an
    API failure (e.g. expired token). When ``report_date`` is omitted, the
    latest available consolidated period is used instead of a hard-coded date.
    """
    raw_bs = fetch_balance_sheet(stock_code, report_date)
    raw_cf = fetch_cash_flow(stock_code, report_date)
    raw_ind = fetch_financial_indicators(stock_code, report_date)

    # Surface upstream failures instead of silently returning all-None values.
    failures = [r.get("error_msg") for r in (raw_bs, raw_cf, raw_ind) if not r.get("success")]
    if failures:
        return {
            "success": False,
            "error": "；".join(str(msg) for msg in dict.fromkeys(failures) if msg) or "巨潮财务接口调用失败",
            "stock_code": stock_code,
            "report_date": report_date,
            "balance_sheet": {},
            "cash_flow": {},
            "indicators": {},
        }

    def _latest_annual_record(result: Dict) -> Dict:
        """Pick the most recent *annual* consolidated period (12-31), not arbitrary quarter."""
        records = result.get("records") or []
        if not records:
            return {}
        annual = [r for r in records if str(r.get("ENDDATE") or "").endswith("-12-31")]
        if not annual:
            # Fallback to any latest record when annual is unavailable.
            annual = records
        annual.sort(key=lambda r: str(r.get("ENDDATE")), reverse=True)
        return annual[0]

    bs = _latest_annual_record(raw_bs)
    cf = _latest_annual_record(raw_cf)
    ind = _latest_annual_record(raw_ind)
    resolved_date = bs.get("ENDDATE") or cf.get("ENDDATE") or ind.get("ENDDATE") or report_date

    return {
        "success": True,
        "stock_code": stock_code,
        "report_date": resolved_date,
        "balance_sheet": {
            "total_assets": _to_float(bs.get("F038N")),
            "total_liabilities": _to_float(bs.get("F061N")),
            "total_equity": _to_float(bs.get("F070N")),
            "current_assets": _to_float(bs.get("F019N")),
            "current_liabilities": _to_float(bs.get("F052N")),
            "cash": _to_float(bs.get("F006N")),
            "accounts_receivable": _to_float(bs.get("F009N")),
            "inventory": _to_float(bs.get("F015N")),
            "fixed_assets": _to_float(bs.get("F025N")),
            "short_term_borrowing": _to_float(bs.get("F039N")),
            "long_term_borrowing": _to_float(bs.get("F053N")),
            "retained_earnings": _to_float(bs.get("F065N")),
        },
        "cash_flow": {
            "operating": _to_float(cf.get("F015N")),
            "investing": _to_float(cf.get("F016N")),
            "financing": _to_float(cf.get("F017N")),
        },
        "indicators": {
            # 字段编码经 603259 实测值校正：F078N=销售毛利率、F041N=资产负债率、F005N=基本每股收益。
            # 流动比率指标表无直接可靠字段，按资产负债表计算。
            "roe": _to_float(ind.get("F056N")),
            "gross_margin": _to_float(ind.get("F078N")),
            "net_margin": _to_float(ind.get("F037N")),
            "debt_ratio": _to_float(ind.get("F041N")),
            "current_ratio": _safe_div(
                _to_float(bs.get("F019N")),
                _to_float(bs.get("F052N")),
            ),
            "eps": _to_float(ind.get("F005N")),
        },
    }


# ──────────────────────────────────────────────────────────────
# Composite: Risk Profile
# ──────────────────────────────────────────────────────────────

def build_risk_profile(stock_code: str) -> Dict[str, Any]:
    """Build a risk profile from legal/shareholder APIs.

    Returns litigation, guarantee, penalty, freeze, and arbitration counts
    plus key details. Includes ``success``/``error`` so an API failure is not
    mistaken for a clean "0 risk events" result.
    """
    litigation = fetch_litigation(stock_code)
    guarantees = fetch_guarantees(stock_code)
    penalties = fetch_penalties(stock_code)
    freezes = fetch_asset_freezes(stock_code)
    arbitration = fetch_arbitration(stock_code)

    sources = [litigation, guarantees, penalties, freezes, arbitration]
    # All endpoints failing almost always means an auth/token problem, not
    # genuinely zero events; flag it so the report can show a degraded state.
    if all(not r.get("success") for r in sources):
        failures = [r.get("error_msg") for r in sources if r.get("error_msg")]
        return {
            "success": False,
            "error": (failures[0] if failures else "巨潮司法风险接口调用失败"),
            "stock_code": stock_code,
            "litigation": {"count": 0, "records": []},
            "guarantees": {"count": 0, "records": []},
            "penalties": {"count": 0, "records": []},
            "asset_freezes": {"count": 0, "records": []},
            "arbitration": {"count": 0, "records": []},
        }

    return {
        "success": True,
        "stock_code": stock_code,
        "litigation": {
            "count": litigation.get("total", 0),
            "records": litigation.get("records", []),
        },
        "guarantees": {
            "count": guarantees.get("total", 0),
            "records": guarantees.get("records", []),
        },
        "penalties": {
            "count": penalties.get("total", 0),
            "records": penalties.get("records", []),
        },
        "asset_freezes": {
            "count": freezes.get("total", 0),
            "records": freezes.get("records", []),
        },
        "arbitration": {
            "count": arbitration.get("total", 0),
            "records": arbitration.get("records", []),
        },
    }


# ──────────────────────────────────────────────────────────────
# Composite: Shareholder Profile
# ──────────────────────────────────────────────────────────────

def build_shareholder_profile(stock_code: str) -> Dict[str, Any]:
    """Build a shareholder profile from equity-related APIs."""
    top_holders = fetch_top_shareholders(stock_code)
    controller = fetch_actual_controller(stock_code)
    capital_changes = fetch_share_capital_changes(stock_code)

    return {
        "stock_code": stock_code,
        "top_shareholders": {
            "count": top_holders.get("total", 0),
            "records": top_holders.get("records", []),
        },
        "actual_controller": {
            "count": controller.get("total", 0),
            "records": controller.get("records", []),
        },
        "share_capital_changes": {
            "count": capital_changes.get("total", 0),
            "records": capital_changes.get("records", []),
        },
    }


def build_shareholder_table(stock_code: str) -> Dict[str, Any]:
    """Build a structured shareholder table for report rendering.

    Returns table data with columns: 股东名称, 股东性质, 持股比例, 持股数量, 质押/冻结情况.
    Only includes the latest reporting period's top 10 shareholders.
    """
    result = fetch_top_shareholders(stock_code)
    records = result.get("records") or []
    if not records:
        return {"success": False, "stock_code": stock_code, "rows": []}

    # Find latest reporting period
    dates = [r.get("ENDDATE") for r in records if r.get("ENDDATE")]
    if not dates:
        return {"success": False, "stock_code": stock_code, "rows": []}
    latest_date = sorted(dates)[-1]
    latest = [r for r in records if r.get("ENDDATE") == latest_date]

    rows = []
    for r in latest[:10]:
        pledge = r.get("F007N")
        rows.append({
            "股东名称": r.get("F002V") or "",
            "股东性质": r.get("F004V") or "",
            "持股比例": f"{r.get('F006N', 0):.2f}%",
            "持股数量": int(r.get("F005N") or 0),
            "质押/冻结": f"{int(pledge):,}股" if pledge and pledge > 0 else "无",
        })

    # Sort by shareholding ratio descending
    rows.sort(key=lambda x: float(x["持股比例"].rstrip("%")), reverse=True)

    return {
        "success": True,
        "stock_code": stock_code,
        "report_date": latest_date,
        "columns": ["股东名称", "股东性质", "持股比例", "持股数量", "质押/冻结"],
        "rows": rows,
    }
