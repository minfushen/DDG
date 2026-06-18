"""Cross-check structured financial statements from multiple public providers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import hashlib
import math


DEFAULT_AMOUNT_RELATIVE_THRESHOLD = 0.01
DEFAULT_AMOUNT_ABSOLUTE_THRESHOLD = 1_000_000.0


METRIC_SPECS = {
    "revenue": ("income_statement", "营业收入", "营业收入"),
    "cost": ("income_statement", "营业成本", "营业成本"),
    "net_profit": ("income_statement", "净利润", "净利润"),
    "deducted_net_profit": ("income_statement", "扣非净利润", "扣非净利润"),
    "investment_income": ("income_statement", "投资收益", "投资收益"),
    "asset_impairment": ("income_statement", "资产减值损失", "资产减值损失"),
    "credit_impairment": ("income_statement", "信用减值损失", "信用减值损失"),
    "total_assets": ("balance_sheet", "资产总计", "资产总计"),
    "cash": ("balance_sheet", "货币资金", "货币资金"),
    "receivable": ("balance_sheet", "应收账款", "应收账款"),
    "inventory": ("balance_sheet", "存货", "存货"),
    "short_loan": ("balance_sheet", "短期借款", "短期借款"),
    "total_liabilities": ("balance_sheet", "负债合计", "负债合计"),
    "equity": ("balance_sheet", "所有者权益", "所有者权益"),
    "operating_cash_flow": ("cash_flow", "经营活动产生的现金流量净额", "经营活动现金流量净额"),
    "investing_cash_flow": ("cash_flow", "投资活动产生的现金流量净额", "投资活动现金流量净额"),
    "financing_cash_flow": ("cash_flow", "筹资活动产生的现金流量净额", "筹资活动现金流量净额"),
}


def _to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    try:
        number = float(str(value).replace(",", ""))
        return number if math.isfinite(number) else None
    except ValueError:
        return None


def _value(statement: Dict[str, Any], table: str, item: str, year: str) -> Optional[float]:
    for row in statement.get(table) or []:
        if str(row.get("项目")) == item:
            return _to_number(row.get(year))
    return None


def _years(*statements: Dict[str, Any]) -> List[str]:
    years = set()
    for statement in statements:
        for table_rows in statement.values():
            if not isinstance(table_rows, list):
                continue
            for row in table_rows:
                years.update(str(key) for key in row.keys() if str(key).isdigit() and len(str(key)) == 4)
    return sorted(years, reverse=True)


def reconcile_financial_providers(
    primary_provider: str,
    primary_statements: Dict[str, Any],
    secondary_provider: str,
    secondary_statements: Dict[str, Any],
    relative_threshold: float = DEFAULT_AMOUNT_RELATIVE_THRESHOLD,
    absolute_threshold: float = DEFAULT_AMOUNT_ABSOLUTE_THRESHOLD,
) -> Dict[str, Any]:
    years = _years(primary_statements, secondary_statements)[:3]
    checks: List[Dict[str, Any]] = []
    mismatches: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []

    for year in years:
        for metric_key, (table, item, label) in METRIC_SPECS.items():
            primary_value = _value(primary_statements, table, item, year)
            secondary_value = _value(secondary_statements, table, item, year)
            if primary_value is None or secondary_value is None:
                if primary_value is not None or secondary_value is not None:
                    missing.append({
                        "year": year,
                        "metric_key": metric_key,
                        "label": label,
                        primary_provider: primary_value,
                        secondary_provider: secondary_value,
                    })
                continue
            diff = primary_value - secondary_value
            base = max(abs(primary_value), abs(secondary_value), 1.0)
            relative_diff = abs(diff) / base
            threshold_value = max(absolute_threshold, base * relative_threshold)
            status = "matched" if abs(diff) <= threshold_value else "mismatch"
            row = {
                "year": year,
                "metric_key": metric_key,
                "label": label,
                "primary_provider": primary_provider,
                "secondary_provider": secondary_provider,
                "primary_value": primary_value,
                "secondary_value": secondary_value,
                "absolute_diff": diff,
                "relative_diff": relative_diff,
                "threshold_value": threshold_value,
                "status": status,
            }
            checks.append(row)
            if status == "mismatch":
                mismatches.append(row)

    return {
        "success": True,
        "primary_provider": primary_provider,
        "secondary_provider": secondary_provider,
        "years": years,
        "checked_count": len(checks),
        "mismatch_count": len(mismatches),
        "missing_count": len(missing),
        "relative_threshold": relative_threshold,
        "absolute_threshold": absolute_threshold,
        "passed": not mismatches,
        "checks": checks,
        "mismatches": mismatches,
        "missing": missing,
    }


def _evidence_id(enterprise_name: str, mismatch: Dict[str, Any]) -> str:
    raw = f"financial_provider_reconciliation|{enterprise_name}|{mismatch.get('year')}|{mismatch.get('metric_key')}|{mismatch.get('absolute_diff')}"
    return "ev_fin_reconcile_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def reconciliation_to_evidence(enterprise_name: str, reconciliation: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for mismatch in reconciliation.get("mismatches") or []:
        label = mismatch.get("label") or mismatch.get("metric_key")
        year = mismatch.get("year")
        evidence.append({
            "id": _evidence_id(enterprise_name, mismatch),
            "label": f"{year}年{label}跨源差异",
            "value": f"{mismatch.get('primary_provider')}={mismatch.get('primary_value')}；{mismatch.get('secondary_provider')}={mismatch.get('secondary_value')}",
            "claim": f"{year}年{label}在{mismatch.get('primary_provider')}与{mismatch.get('secondary_provider')}之间存在超过阈值的结构化数据差异，需回到巨潮/交易所原始公告或审计报告复核。",
            "source": "公开财报数据源交叉校验",
            "source_name": "公开财报数据源交叉校验",
            "source_type": "financial_provider_reconciliation",
            "agent": "financial",
            "domain": "financial",
            "category": "financial",
            "confidence": 0.9,
            "trust_level": "medium",
            "requires_manual_review": True,
            "metadata": {"mismatch": mismatch, "reconciliation_summary": {k: reconciliation.get(k) for k in ["primary_provider", "secondary_provider", "relative_threshold", "absolute_threshold"]}},
        })
    return evidence


def reconciliation_to_gaps(task_id: str, enterprise_name: str, reconciliation: Dict[str, Any]) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []
    for mismatch in (reconciliation.get("mismatches") or [])[:8]:
        label = mismatch.get("label") or mismatch.get("metric_key")
        year = mismatch.get("year")
        gaps.append({
            "id": _evidence_id(enterprise_name, mismatch).replace("ev_", "gap_"),
            "task_id": task_id,
            "description": f"{year}年{label}在{reconciliation.get('primary_provider')}与{reconciliation.get('secondary_provider')}之间存在超过阈值的差异。",
            "why_it_matters": "跨源结构化财务数据不一致会影响偿债指标、利润质量和授信测算，应以原始公告或审计报告复核。",
            "suggested_next_actions": ["回查巨潮/交易所原始年报PDF", "核对审计报告附注和财务报表项目口径", "必要时要求客户提供盖章版三大表"],
            "severity": "medium",
            "metadata": {"mismatch": mismatch},
        })
    return gaps
