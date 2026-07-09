"""LLM-assisted financial narrative writer.

The financial agent computes metrics deterministically. This module only turns
those verified metrics into customer-manager style risk text, with quality
checks and deterministic fallback.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, TimeoutError, wait
from functools import lru_cache
import json
import re
import time

from app.config.llm_config import cached_invoke, get_llm
from app.config import settings
from app.config.prompt_loader import load_prompt_template, render_prompt_template
from app.config.quality_gate_loader import (
    get_banned_terms,
    get_ocr_error_hints,
    get_business_penetration_config,
)


BANNED_TERMS = get_banned_terms("financial_narrative")
_OCR_ERROR_HINTS = get_ocr_error_hints()
_BUSINESS_PENETRATION = get_business_penetration_config()

LLM_NARRATIVE_TIMEOUT_SECONDS = max(60, settings.LLM_TIMEOUT_SECONDS)
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="financial-narrative")


@lru_cache()
def _get_primary_narrative_llm() -> BaseChatModel:
    """Configure primary LLM for structured financial prose."""
    return get_llm(
        temperature=0,
        max_tokens=16384,
        timeout=max(settings.LLM_TIMEOUT_SECONDS, LLM_NARRATIVE_TIMEOUT_SECONDS),
        max_retries=1,
        response_format="json_object",
    )


@lru_cache()
def _get_backup_narrative_llm() -> BaseChatModel | None:
    if not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY or not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL:
        return None
    return get_llm(
        model=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_MODEL or settings.LLM_MODEL,
        api_key=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY,
        base_url=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL,
        temperature=0,
        max_tokens=16384,
        timeout=max(settings.LLM_TIMEOUT_SECONDS, LLM_NARRATIVE_TIMEOUT_SECONDS),
        max_retries=1,
        response_format="json_object",
    )


def _available_narrative_llms() -> List[tuple[str, ChatOpenAI]]:
    backup = _get_backup_narrative_llm()
    if backup is not None:
        return [("backup", backup)]
    return [("primary", _get_primary_narrative_llm())]


DIAGNOSTIC_DIMENSIONS = [
    "盈利质量与成长性风险",
    "资产真实性与营运效率风险",
    "资本结构与偿债能力风险",
]


# Mapping from structured package metric keys to legacy key_metrics names.
_PACKAGE_METRIC_ALIASES = {
    "operating_cashflow": "operating_cash_flow",
    "investing_cashflow": "investing_cash_flow",
    "financing_cashflow": "financing_cash_flow",
    "short_debt": "short_loan",
    "ebitda_interest_coverage": "ebitda_interest_coverage",
}


def _derive_inputs_from_structured_package(
    structured_financial_package: Dict[str, Any],
    key_metrics: Dict[str, Any],
    key_metric_series: Dict[str, Dict[str, str]] | None,
    data_boundary: str,
    risk_summary: List[str],
) -> tuple[Dict[str, Any], Dict[str, Dict[str, str]], str, List[str]]:
    """Use structured financial package as the single source of truth for metric values.

    Legacy computed fields (e.g. revenue_growth) are preserved if they do not conflict
    with package-derived values.
    """
    package = structured_financial_package or {}
    latest_metrics = package.get("latest_metrics") or {}
    display_metrics = package.get("display_metrics") or {}
    trends = package.get("trends") or {}

    derived_metrics = dict(key_metrics or {})
    derived_series = dict(key_metric_series or {})

    for metric_key, meta in latest_metrics.items():
        if not isinstance(meta, dict):
            continue
        legacy_key = _PACKAGE_METRIC_ALIASES.get(metric_key, metric_key)
        display_value = meta.get("display_value")
        if display_value and display_value != "数据不可用":
            derived_metrics[legacy_key] = display_value
        trend = trends.get(metric_key)
        if trend and trend != "数据不足":
            derived_metrics[f"{legacy_key}_trend"] = trend
        series = display_metrics.get(metric_key)
        if series:
            derived_series[legacy_key] = series

    # Use package data boundary when available.
    boundary_items = package.get("data_boundary") or []
    derived_boundary = data_boundary
    if boundary_items:
        derived_boundary = "；".join(str(item) for item in boundary_items if item)

    # Merge package red flags into risk summary without duplicates.
    derived_risks = list(risk_summary or [])
    existing_texts = {str(r).strip() for r in derived_risks}
    for flag in package.get("red_flags") or []:
        detail = flag.get("detail") or ""
        if detail and detail.strip() not in existing_texts:
            derived_risks.append(detail.strip())
            existing_texts.add(detail.strip())

    return derived_metrics, derived_series, derived_boundary, derived_risks


# 盈利能力分析表格中必须使用的标准化指标标签。
_STANDARD_FINANCIAL_METRIC_LABELS = {
    "ebitda": "EBITDA（亿元）",
    "net_margin": "销售净利率(%)",
    "roa": "ROA(%)",
    "roe": "ROE(%)",
}


def _ocr_error_warnings(text: str) -> List[str]:
    """Detect corrupted characters / OCR mistakes in generated prose."""
    warnings: List[str] = []
    for bad, hint in _OCR_ERROR_HINTS.items():
        if bad in text:
            warnings.append(f"文本包含OCR/低质量表达：'{bad}'，应修正为'{hint}'")
    return warnings


def _metric_label_warnings(text: str) -> List[str]:
    """Ensure financial metric labels are standard terms, not OCR garbage."""
    warnings: List[str] = []
    # 表格头或正文中若把 ROE 写成鱼子、鱼籽等，应拦截。
    corrupted_metric_patterns = [
        (r"鱼子\s*[（(]?%?[%）)]?", "ROE"),
        (r"鱼籽\s*[（(]?%?[%）)]?", "ROE"),
    ]
    for pattern, correct in corrupted_metric_patterns:
        if re.search(pattern, text):
            warnings.append(f"指标标签被识别为错误术语，应使用标准名称：{correct}")
    return warnings


def _risk_label(rating: str) -> str:
    return {"low": "低风险", "medium": "中风险", "high": "高风险"}.get(rating, rating or "中风险")


def _series_items(values: Dict[str, str], limit: int = 3) -> List[tuple[str, str]]:
    return [(str(year), str(value)) for year, value in (values or {}).items() if value and value != "数据不可用"][:limit]


def _series_sentence(values: Dict[str, str], label: str) -> str:
    items = _series_items(values)
    if len(items) >= 2:
        return f"近三年{label}分别为" + "、".join(f"{year}年{value}" for year, value in items)
    if len(items) == 1:
        return f"{items[0][0]}年{label}为{items[0][1]}"
    return f"{label}数据待补充"


def _latest_series_value(values: Dict[str, str]) -> tuple[str, str] | None:
    items = _series_items(values, limit=10)
    return items[-1] if items else None


def _numeric_sign(raw: Any) -> int:
    """Return -1/0/1 for the numeric value parsed from a string like '-3.5%' or '1.2亿'."""
    if raw is None:
        return 0
    text = str(raw).strip()
    if not text or text in ("数据不可用", "--", "-"):
        return 0
    # Remove common units and trailing chars, keep sign and digits/decimals.
    cleaned = re.sub(r"[^\d.\-]", "", text.split("（")[0].split("(")[0])
    try:
        return 1 if float(cleaned) > 0 else -1 if float(cleaned) < 0 else 0
    except ValueError:
        return 0


def _clean_join(parts: List[str]) -> str:
    return "".join(part for part in parts if part)


def _render_credit_style_summary(
    enterprise_name: str,
    key_metrics: Dict[str, Any],
    risk_rating: str,
    risk_score: int | None,
    recommendation: str,
    data_boundary: str,
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    diagnostics: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
) -> List[str]:
    """Render stable, customer-manager style prose from verified metrics.

    LLM output is allowed to shape risk labels and review points, but the final
    report prose is assembled here so corrupted wording cannot enter the report.
    """
    series = key_metric_series or {}
    revenue_series = series.get("revenue") or {}
    net_profit_series = series.get("net_profit") or {}
    debt_ratio_series = series.get("debt_ratio") or {}
    operating_cf_series = series.get("operating_cash_flow") or {}
    gross_margin_series = series.get("gross_margin") or {}

    latest_year = str(key_metrics.get("latest_year") or (_latest_series_value(revenue_series) or ("最新年度", ""))[0])
    risk_level = _risk_label(risk_rating)
    score_text = f"（{risk_score}分）" if risk_score is not None else ""
    revenue_growth = key_metrics.get("revenue_growth", "数据不可用")
    revenue_cagr = key_metrics.get("revenue_cagr", "数据不可用")
    net_margin = key_metrics.get("net_margin", "数据不可用")
    gross_margin = key_metrics.get("gross_margin", "数据不可用")
    cost = key_metrics.get("cost", "数据不可用")
    deducted_net_profit = key_metrics.get("deducted_net_profit", "数据不可用")
    receivable = key_metrics.get("receivable", "数据不可用")
    receivable_to_revenue = key_metrics.get("receivable_to_revenue", "数据不可用")
    receivable_growth = key_metrics.get("receivable_growth", "数据不可用")
    receivable_turnover_days = key_metrics.get("receivable_turnover_days", "数据不可用")
    inventory_turnover_days = key_metrics.get("inventory_turnover_days", "数据不可用")
    operating_cf_to_net_profit = key_metrics.get("operating_cf_to_net_profit", "数据不可用")
    current_ratio = key_metrics.get("current_ratio", "数据不可用")
    current_ratio_change = key_metrics.get("current_ratio_change", "数据不可用")
    debt_ratio_change = key_metrics.get("debt_ratio_change", "数据不可用")
    short_loan = key_metrics.get("short_loan", "数据不可用")
    cash_to_short_debt = key_metrics.get("cash_to_short_debt", "数据不可用")
    ebitda_interest_coverage = key_metrics.get("ebitda_interest_coverage", "数据不可用")
    profit_cash_bridge = profit_cash_bridge or (diagnostics or {}).get("profit_cash_bridge") or {}
    bridge_conclusion = profit_cash_bridge.get("conclusion") or "利润与经营现金流需结合报表附注进一步桥接分析。"
    bridge_explanation = profit_cash_bridge.get("bridge_explanation") or "需补充折旧摊销、减值损失、营运资本变动和非经常性损益明细，判断利润现金含量。"
    deducted_profit_judgement = profit_cash_bridge.get("deducted_profit_judgement") or "扣非净利润和非经常性损益明细需进一步核验。"
    heavy_asset_judgement = profit_cash_bridge.get("heavy_asset_judgement") or "需结合固定资产、在建工程和产能利用率判断重资产投入对利润和现金流的影响。"
    investment_income_judgement = profit_cash_bridge.get("investment_income_judgement") or "需核查投资收益等非主营损益对净利润的影响。"

    diagnostic_rows = (diagnostics or {}).get("diagnostics") or []
    review_points: List[str] = []
    for row in diagnostic_rows:
        for item in row.get("verification_action") or []:
            if item and item not in review_points:
                review_points.append(str(item))
    review_text = "；".join(review_points[:3]) or "复核审计意见、报表附注、银行流水和纳税申报匹配情况"

    # Interpretive lead sentences for the chapter summary so it is not just a list of numbers.
    profit_lead = ""
    if _numeric_sign(revenue_growth) > 0:
        profit_lead = "收入规模持续扩张"
    net_profit_latest = (
        list(net_profit_series.values())[-1]
        if net_profit_series and net_profit_series.values()
        else key_metrics.get("net_profit", "数据不可用")
    )
    if _numeric_sign(net_profit_latest) < 0:
        profit_lead += "但利润端承压" if profit_lead else "利润端承压"
    profit_lead = (profit_lead + "，") if profit_lead else ""

    debt_lead = ""
    if _numeric_sign(debt_ratio_change) > 0:
        debt_lead = "杠杆水平上升"
    if _numeric_sign(current_ratio_change) < 0:
        debt_lead += "且流动性边际走弱" if debt_lead else "流动性边际走弱"
    debt_lead = (debt_lead + "，") if debt_lead else ""

    receivable_lead = ""
    if _numeric_sign(receivable_growth) > 0:
        receivable_lead = "应收账款占用增加，"

    summary = [
        f"【总体评价】{risk_level}{score_text} | {enterprise_name}财务表现呈{risk_level}，{recommendation}。授信前应重点复核盈利质量、经营现金流、应收回款和短期偿债安排。",
        _clean_join([
            "3.1 收入与利润分析：",
            profit_lead,
            _series_sentence(revenue_series, "营业收入"),
            f"，{latest_year}年较上年增长{revenue_growth}，近三年CAGR为{revenue_cagr}。",
            _series_sentence(net_profit_series, "净利润"),
            f"；{latest_year}年营业成本为{cost}，扣非净利润为{deducted_net_profit}，毛利率为{gross_margin}、销售净利率为{net_margin}。",
            f"{deducted_profit_judgement}收入增长能否转化为稳定利润，需要结合主营构成、价格变化、费用结构、非经常性损益和行业景气度继续核验。",
        ]),
        _clean_join([
            "3.2 资产负债分析：",
            debt_lead,
            _series_sentence(debt_ratio_series, "资产负债率"),
            f"，较首年变化{debt_ratio_change}；{latest_year}年短期借款为{short_loan}，流动比率为{current_ratio}，较首年变化{current_ratio_change}。",
            f"{heavy_asset_judgement}若杠杆上升或流动比率下降，应进一步拆分短期借款、应付票据、应付账款、或有负债和未使用授信额度，判断未来12个月偿债压力。",
        ]),
        _clean_join([
            "3.3 盈利质量与营运效率：",
            receivable_lead,
            _series_sentence(gross_margin_series, "毛利率") if gross_margin_series else f"{latest_year}年毛利率为{gross_margin}",
            f"；{latest_year}年应收账款余额为{receivable}，应收/营收占比为{receivable_to_revenue}，应收账款较上年增长{receivable_growth}。",
            f"应收账款周转天数为{receivable_turnover_days}，存货周转天数为{inventory_turnover_days}。若应收或存货周转拉长，应重点核查客户信用政策、账龄结构、期后回款、跌价准备和坏账计提充分性。",
        ]),
        _clean_join([
            "3.4 偿债能力与财务信号异常：",
            _series_sentence(operating_cf_series, "经营活动产生的现金流量净额"),
            f"；经营现金流/净利润为{operating_cf_to_net_profit}，现金短债比为{cash_to_short_debt}，EBITDA利息保障倍数为{ebitda_interest_coverage}。",
            f"{bridge_conclusion}{bridge_explanation}{investment_income_judgement}经营现金流走弱、利润与现金流背离或短债集中到期，都会削弱报表偿债能力的安全边际。",
            f"核查重点包括：{review_text}。",
        ]),
        f"数据边界：上述判断基于{data_boundary}，正式授信前仍需结合审计报告、报表附注、银行流水、纳税资料、主要合同和贷款用途复核。",
    ]
    return summary[:6]


def _format_attribution_drivers(drivers: List[Dict[str, Any]], prefix: str) -> str:
    """把归因驱动因子渲染为可嵌入 fallback driver 的句子。"""
    if not drivers:
        return ""
    parts: List[str] = []
    for driver in drivers[:3]:
        factor = driver.get("factor") or ""
        evidence = driver.get("evidence") or ""
        if factor:
            sentence = factor
            if evidence:
                sentence += f"（年报原文：{evidence}）"
            parts.append(sentence)
    if not parts:
        return ""
    return prefix + "；".join(parts) + "（来源：年报经营情况讨论与分析章节）。"


def _fallback_diagnostics(
    enterprise_name: str,
    key_metrics: Dict[str, Any],
    risk_summary: List[str],
    recommendation: str,
    risk_rating: str,
    risk_score: int | None,
    data_boundary: str,
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    knowledge_context: Dict[str, Any] | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    annual_report_notes: Dict[str, Any] | None = None,
    industry_context: Dict[str, Any] | None = None,
    business_segments: List[Dict[str, Any]] | None = None,
    annual_business_review: Dict[str, Any] | None = None,
    financial_business_hints: List[str] | None = None,
) -> Dict[str, Any]:
    latest_year = key_metrics.get("latest_year") or "最新年度"
    revenue = key_metrics.get("revenue", "数据不可用")
    revenue_growth = key_metrics.get("revenue_growth", "数据不可用")
    revenue_cagr = key_metrics.get("revenue_cagr", "数据不可用")
    gross_margin = key_metrics.get("gross_margin", "数据不可用")
    net_margin = key_metrics.get("net_margin", "数据不可用")
    net_profit = key_metrics.get("net_profit", "数据不可用")
    debt_ratio = key_metrics.get("debt_ratio", "数据不可用")
    debt_ratio_change = key_metrics.get("debt_ratio_change", "数据不可用")
    current_ratio = key_metrics.get("current_ratio", "数据不可用")
    current_ratio_change = key_metrics.get("current_ratio_change", "数据不可用")
    operating_cash_flow = key_metrics.get("operating_cash_flow", "数据不可用")
    receivable = key_metrics.get("receivable", "数据不可用")
    receivable_to_revenue = key_metrics.get("receivable_to_revenue", "数据不可用")
    receivable_growth = key_metrics.get("receivable_growth", "数据不可用")
    operating_cf_to_net_profit = key_metrics.get("operating_cf_to_net_profit", "数据不可用")
    first_risk = risk_summary[0] if risk_summary else "未发现明显重大财务异常，但仍需结合底层材料复核。"
    series = key_metric_series or {}
    revenue_series = series.get("revenue") or {}
    net_profit_series = series.get("net_profit") or {}
    debt_ratio_series = series.get("debt_ratio") or {}
    operating_cf_series = series.get("operating_cash_flow") or {}

    def series_text(values: Dict[str, str], label: str) -> str:
        items = [f"{year}年{value}" for year, value in values.items() if value and value != "数据不可用"]
        if len(items) >= 2:
            return f"近三年{label}分别为" + "、".join(items) + ""
        return f"{latest_year}年{label}为{key_metrics.get(label, '数据不可用')}"

    knowledge_context = knowledge_context or {}
    triggered_rules = knowledge_context.get("triggered_rules") or []
    source_ids = [hit.get("source_id") for hit in (knowledge_context.get("knowledge_briefs") or []) if hit.get("source_id")]
    codeact_analysis = codeact_analysis or {}
    validation_issues = codeact_analysis.get("validation_issues") or []
    validation_warnings = codeact_analysis.get("validation_warnings") or []
    reconciliation_notes = [item.get("message") for item in (validation_issues + validation_warnings) if isinstance(item, dict) and item.get("message")]
    profit_cash_bridge = profit_cash_bridge or {}

    profit_cash_bridge = profit_cash_bridge or {}

    # 年报深度归因：若存在则替换/补充通用归因模板。
    attribution = (annual_report_notes or {}).get("attribution") or {}
    revenue_attribution_text = _format_attribution_drivers(attribution.get("revenue_drivers") or [], "年报管理层对营收变动的解释：")
    margin_attribution_text = _format_attribution_drivers(attribution.get("margin_drivers") or [], "年报管理层对毛利率变动的解释：")
    profit_attribution_text = _format_attribution_drivers(attribution.get("profit_drivers") or [], "年报管理层对利润变动的解释：")
    capacity_status = attribution.get("capacity_status") or ""
    annual_industry_context = attribution.get("industry_context") or ""
    forward_risks = attribution.get("forward_risks") or []
    forward_risk_text = _format_attribution_drivers(forward_risks, "年报提示的未来风险：")

    # 营收/毛利归因：优先使用年报管理层解释，再保留结构化核查维度。
    revenue_driver_core = revenue_attribution_text or margin_attribution_text or ""
    profit_driver_core = profit_attribution_text or ""
    if capacity_status and capacity_status not in (revenue_driver_core + profit_driver_core):
        revenue_driver_core += f"产能状态：{capacity_status}（来源：年报经营情况讨论与分析章节）。"
    if annual_industry_context and annual_industry_context not in (revenue_driver_core + profit_driver_core):
        profit_driver_core += f"行业层面：{annual_industry_context}（来源：年报经营情况讨论与分析章节）。"
    if forward_risk_text and forward_risk_text not in profit_driver_core:
        profit_driver_core += forward_risk_text

    def rule_ids_for(dimension: str) -> List[str]:
        return [rule.get("rule_id") for rule in triggered_rules if rule.get("rule_id") and rule.get("dimension") == dimension][:4]

    risk_label = _risk_label(risk_rating)
    score_text = f"（{risk_score}分）" if risk_score is not None else ""

    # Interpretive lead sentences so the phenomenon is not just a list of numbers.
    profit_lead = ""
    if _numeric_sign(revenue_growth) > 0:
        profit_lead = "收入规模持续扩张"
    if _numeric_sign(net_profit) < 0 or (net_profit_series and _numeric_sign(list(net_profit_series.values())[-1] if net_profit_series.values() else 0) < 0):
        profit_lead += "但利润端承压" if profit_lead else "利润端承压"
    profit_lead = (profit_lead + "，") if profit_lead else ""

    debt_lead = ""
    if _numeric_sign(debt_ratio_change) > 0:
        debt_lead = "杠杆水平上升"
    if _numeric_sign(current_ratio_change) < 0:
        debt_lead += "且流动性边际走弱" if debt_lead else "流动性边际走弱"
    debt_lead = (debt_lead + "，") if debt_lead else ""

    receivable_lead = ""
    if _numeric_sign(receivable_growth) > 0 or (receivable_to_revenue and _numeric_sign(str(receivable_to_revenue).replace("%", "")) > 20):
        receivable_lead = "应收账款占用增加，"

    return {
        "overall_evaluation": {
            "risk_level": risk_label,
            "score": risk_score,
            "conclusion": f"{enterprise_name}财务表现呈{risk_label}{score_text}，{recommendation}",
        },
        "diagnostics": [
            {
                "title": "盈利质量与成长性风险",
                "phenomenon": f"{profit_lead}{series_text(revenue_series, '营业收入')}，{latest_year}年较上年增长{revenue_growth}，近三年CAGR为{revenue_cagr}；{series_text(net_profit_series, '净利润')}，{latest_year}年毛利率为{gross_margin}、销售净利率为{net_margin}。交叉验证：收入增速与利润增速是否匹配，毛利率变动是否伴随产能扩张或产品结构变化。",
                "driver": (profit_cash_bridge.get("deducted_profit_judgement") or "") + (revenue_driver_core or "收入增长质量需结合以下维度判断：①主营构成——若收入增长来自非核心业务或一次性订单，则可持续性存疑；②费用结构——若销售费用或管理费用增速高于收入增速，则盈利空间被侵蚀；③非经常性损益——若政府补助或投资收益占净利润比重较高，则主营造血能力未实质修复。") + "若利润修复弱于收入扩张，需警惕规模增长未能转化为主营造血能力。[需补充：行业基准数据，以判断毛利率是否偏离行业均值]。",
                "risk_level": "中风险" if risk_rating != "high" else "中高风险",
                "verification_action": [
                    "拆分近三年收入增长的产品、客户和区域来源，判断增长可持续性",
                    "核验毛利率与历史期间及行业均值的差异，排查产能过剩或价格下行影响",
                    "复核非经常性损益明细、政府补助到账情况和费用资本化政策"
                ],
                "missing_items": ["主营构成明细", "同业毛利率基准", "审计意见和报表附注"],
                "rule_ids": rule_ids_for("盈利质量与成长性风险"),
                "knowledge_source_ids": source_ids[:3],
            },
            {
                "title": "资产真实性与营运效率风险",
                "phenomenon": f"{receivable_lead}{latest_year}年应收账款余额为{receivable}，应收/营收占比为{receivable_to_revenue}，应收账款较上年增长{receivable_growth}；{series_text(operating_cf_series, '经营活动产生的现金流量净额')}，经营现金流/净利润为{operating_cf_to_net_profit}。交叉验证：应收增速是否高于收入增速，经营现金流是否弱于账面利润。",
                "driver": (profit_driver_core or "") + "若应收增速高于收入增速或经营现金流弱于利润表现，需从以下维度归因：①信用政策——是否对下游客户放宽账期以刺激销售；②客户集中度——是否过度依赖少数大客户导致回款滞后；③收入确认质量——是否存在提前确认收入或关联交易虚增。" + (profit_cash_bridge.get("bridge_explanation") or "") + "存货周转放缓可能因行业去库存周期或产品滞销，需关注跌价准备充分性。[需补充：行业应收周转天数和存货周转天数基准]。",
                "risk_level": "中风险",
                "verification_action": [
                    "获取应收账龄结构、前十大客户余额及期后回款测试",
                    "执行函证程序，核实大额应收账款的真实性和可回收性",
                    "复核坏账计提充分性及客户信用政策变化，排查关联方资金占用"
                ],
                "missing_items": ["应收账龄表", "前十大客户回款明细", "银行流水和纳税申报匹配材料"],
                "rule_ids": rule_ids_for("资产真实性与营运效率风险"),
                "knowledge_source_ids": source_ids[:3],
            },
            {
                "title": "资本结构与偿债能力风险",
                "phenomenon": f"{debt_lead}{series_text(debt_ratio_series, '资产负债率')}，较首年变化{debt_ratio_change}；{latest_year}年流动比率为{current_ratio}，较首年变化{current_ratio_change}。交叉验证：资产负债率上升是否伴随短期借款增加，流动比率下降是否因流动负债增速高于流动资产。",
                "driver": (profit_cash_bridge.get("credit_implication") or "") + (profit_driver_core or "") + "杠杆变化和流动比率下降需从以下维度归因：①融资结构——短期借款增加是否用于长期资产投资（短债长用）；②应付账款/票据——是否通过延长供应商账期或增加票据融资维持流动性；③或有负债——是否存在对外担保、未决诉讼或表外融资。报表流动性不等同于可即时偿债现金，因为流动资产中应收账款和存货的变现能力存在不确定性。[需补充：行业中位数资产负债率和流动比率]。",
                "risk_level": "中风险" if risk_rating != "low" else "低中风险",
                "verification_action": [
                    "编制未来12个月债务到期和现金流预测，评估再融资需求",
                    "核实短期借款、应付票据、担保和或有负债清单",
                    "评估应收账款保理、票据贴现等表外融资安排及未使用授信额度"
                ],
                "missing_items": ["有息负债明细", "担保及或有负债清单", "未来12个月现金流预测"],
                "rule_ids": rule_ids_for("资本结构与偿债能力风险"),
                "knowledge_source_ids": source_ids[:3],
            },
        ],
        "data_boundary": data_boundary,
        "profit_cash_bridge": profit_cash_bridge,
        "manual_review_items": ["审计报告及附注", "银行流水", "纳税资料", "主要合同", first_risk] + reconciliation_notes[:4],
        "sections": _build_fallback_sections(
            enterprise_name, key_metrics, risk_rating, risk_score, recommendation, data_boundary,
            key_metric_series, profit_cash_bridge, annual_report_notes,
            industry_context, business_segments, annual_business_review, financial_business_hints,
        ),
    }


def _build_fallback_sections(
    enterprise_name: str,
    key_metrics: Dict[str, Any],
    risk_rating: str,
    risk_score: int | None,
    recommendation: str,
    data_boundary: str,
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    annual_report_notes: Dict[str, Any] | None = None,
    industry_context: Dict[str, Any] | None = None,
    business_segments: List[Dict[str, Any]] | None = None,
    annual_business_review: Dict[str, Any] | None = None,
    financial_business_hints: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """当没有业务上下文时，把现有 summary 拆成四大板块作为 sections 的 fallback。"""
    # 防御性归一化：上游可能传入字符串而非 dict/list
    if isinstance(industry_context, str):
        industry_context = None
    if isinstance(annual_business_review, str):
        annual_business_review = {"summary": annual_business_review}
    if isinstance(business_segments, str):
        business_segments = None
    series = key_metric_series or {}
    revenue_series = series.get("revenue") or {}
    net_profit_series = series.get("net_profit") or {}
    debt_ratio_series = series.get("debt_ratio") or {}
    operating_cf_series = series.get("operating_cash_flow") or {}
    gross_margin_series = series.get("gross_margin") or {}

    latest_year = str(key_metrics.get("latest_year") or (_latest_series_value(revenue_series) or ("最新年度", ""))[0])
    risk_level = _risk_label(risk_rating)
    score_text = f"（{risk_score}分）" if risk_score is not None else ""
    revenue_growth = key_metrics.get("revenue_growth", "数据不可用")
    revenue_cagr = key_metrics.get("revenue_cagr", "数据不可用")
    net_margin = key_metrics.get("net_margin", "数据不可用")
    gross_margin = key_metrics.get("gross_margin", "数据不可用")
    cost = key_metrics.get("cost", "数据不可用")
    deducted_net_profit = key_metrics.get("deducted_net_profit", "数据不可用")
    receivable = key_metrics.get("receivable", "数据不可用")
    receivable_to_revenue = key_metrics.get("receivable_to_revenue", "数据不可用")
    receivable_growth = key_metrics.get("receivable_growth", "数据不可用")
    receivable_turnover_days = key_metrics.get("receivable_turnover_days", "数据不可用")
    inventory_turnover_days = key_metrics.get("inventory_turnover_days", "数据不可用")
    operating_cf_to_net_profit = key_metrics.get("operating_cf_to_net_profit", "数据不可用")
    current_ratio = key_metrics.get("current_ratio", "数据不可用")
    current_ratio_change = key_metrics.get("current_ratio_change", "数据不可用")
    debt_ratio_change = key_metrics.get("debt_ratio_change", "数据不可用")
    short_loan = key_metrics.get("short_loan", "数据不可用")
    cash_to_short_debt = key_metrics.get("cash_to_short_debt", "数据不可用")
    ebitda_interest_coverage = key_metrics.get("ebitda_interest_coverage", "数据不可用")
    profit_cash_bridge = profit_cash_bridge or {}
    bridge_conclusion = profit_cash_bridge.get("conclusion") or "利润与经营现金流需结合报表附注进一步桥接分析。"
    bridge_explanation = profit_cash_bridge.get("bridge_explanation") or "需补充折旧摊销、减值损失、营运资本变动和非经常性损益明细，判断利润现金含量。"
    deducted_profit_judgement = profit_cash_bridge.get("deducted_profit_judgement") or "扣非净利润和非经常性损益明细需进一步核验。"
    heavy_asset_judgement = profit_cash_bridge.get("heavy_asset_judgement") or "需结合固定资产、在建工程和产能利用率判断重资产投入对利润和现金流的影响。"
    investment_income_judgement = profit_cash_bridge.get("investment_income_judgement") or "需核查投资收益等非主营损益对净利润的影响。"

    # 业务上下文摘要（fallback 中简短引用，不编造）
    industry_summary = ""
    if industry_context:
        diag = industry_context.get("diagnosis_summary") or industry_context.get("data_anchor") or ""
        industry_summary = str(diag)[:800]
    segments_summary = ""
    if business_segments:
        segments = business_segments[:5]
        parts = []
        for seg in segments:
            name = seg.get("segment_name") or seg.get("name") or ""
            ratio = seg.get("revenue_ratio") or seg.get("ratio") or ""
            if name:
                parts.append(f"{name}({ratio})" if ratio else name)
        segments_summary = "、".join(parts)
    review_summary = ""
    if annual_business_review:
        review = annual_business_review.get("management_review") or annual_business_review.get("summary") or ""
        review_summary = str(review)[:800]
    hints_summary = ""
    if financial_business_hints:
        hints_summary = "；".join(financial_business_hints[:5])

    # 因果三段式前缀（仅在提供了业务上下文时附加）
    business_prefix = ""
    if industry_summary or segments_summary or review_summary or hints_summary:
        business_prefix = "[业务上下文]"
        if industry_summary:
            business_prefix += f"行业层面：{industry_summary}。"
        if segments_summary:
            business_prefix += f"主营构成：{segments_summary}。"
        if review_summary:
            business_prefix += f"经营讨论：{review_summary}。"
        if hints_summary:
            business_prefix += f"归因提示：{hints_summary}。"
        business_prefix += "\n"

    profit_lead = ""
    if _numeric_sign(revenue_growth) > 0:
        profit_lead = "收入规模持续扩张"
    net_profit_latest = (
        list(net_profit_series.values())[-1]
        if net_profit_series and net_profit_series.values()
        else key_metrics.get("net_profit", "数据不可用")
    )
    if _numeric_sign(net_profit_latest) < 0:
        profit_lead += "但利润端承压" if profit_lead else "利润端承压"
    profit_lead = (profit_lead + "，") if profit_lead else ""

    debt_lead = ""
    if _numeric_sign(debt_ratio_change) > 0:
        debt_lead = "杠杆水平上升"
    if _numeric_sign(current_ratio_change) < 0:
        debt_lead += "且流动性边际走弱" if debt_lead else "流动性边际走弱"
    debt_lead = (debt_lead + "，") if debt_lead else ""

    receivable_lead = ""
    if _numeric_sign(receivable_growth) > 0:
        receivable_lead = "应收账款占用增加，"

    return [
        {
            "section_title": "收入与利润分析",
            "metrics_table": [
                {"label": "营业收入", "value": _series_sentence(revenue_series, "营业收入")},
                {"label": "营收增长", "value": revenue_growth},
                {"label": "营收CAGR", "value": revenue_cagr},
                {"label": "毛利率", "value": gross_margin},
                {"label": "销售净利率", "value": net_margin},
                {"label": "扣非净利润", "value": deducted_net_profit},
            ],
            "narrative": business_prefix + _clean_join([
                profit_lead,
                _series_sentence(revenue_series, "营业收入"),
                f"，{latest_year}年较上年增长{revenue_growth}，近三年CAGR为{revenue_cagr}。",
                _series_sentence(net_profit_series, "净利润"),
                f"；{latest_year}年营业成本为{cost}，扣非净利润为{deducted_net_profit}，毛利率为{gross_margin}、销售净利率为{net_margin}。",
                f"{deducted_profit_judgement}收入增长能否转化为稳定利润，需要结合主营构成、价格变化、费用结构、非经常性损益和行业景气度继续核验。",
            ]),
            "anomalies": [
                "收入增速与利润增速不匹配" if _numeric_sign(revenue_growth) > 0 and _numeric_sign(net_profit_latest) < 0 else "",
                "毛利率偏离行业均值" if not industry_summary else "",
            ],
        },
        {
            "section_title": "资产负债分析",
            "metrics_table": [
                {"label": "资产负债率", "value": _series_sentence(debt_ratio_series, "资产负债率")},
                {"label": "资产负债率变化", "value": debt_ratio_change},
                {"label": "短期借款", "value": short_loan},
                {"label": "流动比率", "value": current_ratio},
                {"label": "流动比率变化", "value": current_ratio_change},
            ],
            "narrative": business_prefix + _clean_join([
                debt_lead,
                _series_sentence(debt_ratio_series, "资产负债率"),
                f"，较首年变化{debt_ratio_change}；{latest_year}年短期借款为{short_loan}，流动比率为{current_ratio}，较首年变化{current_ratio_change}。",
                f"{heavy_asset_judgement}若杠杆上升或流动比率下降，应进一步拆分短期借款、应付票据、应付账款、或有负债和未使用授信额度，判断未来12个月偿债压力。",
            ]),
            "anomalies": [
                "杠杆水平上升" if _numeric_sign(debt_ratio_change) > 0 else "",
                "流动性边际走弱" if _numeric_sign(current_ratio_change) < 0 else "",
            ],
        },
        {
            "section_title": "盈利质量与营运效率",
            "metrics_table": [
                {"label": "毛利率", "value": _series_sentence(gross_margin_series, "毛利率") if gross_margin_series else f"{latest_year}年毛利率为{gross_margin}"},
                {"label": "应收账款", "value": receivable},
                {"label": "应收/营收", "value": receivable_to_revenue},
                {"label": "应收增长", "value": receivable_growth},
                {"label": "应收周转天数", "value": receivable_turnover_days},
                {"label": "存货周转天数", "value": inventory_turnover_days},
            ],
            "narrative": business_prefix + _clean_join([
                receivable_lead,
                _series_sentence(gross_margin_series, "毛利率") if gross_margin_series else f"{latest_year}年毛利率为{gross_margin}",
                f"；{latest_year}年应收账款余额为{receivable}，应收/营收占比为{receivable_to_revenue}，应收账款较上年增长{receivable_growth}。",
                f"应收账款周转天数为{receivable_turnover_days}，存货周转天数为{inventory_turnover_days}。若应收或存货周转拉长，应重点核查客户信用政策、账龄结构、期后回款、跌价准备和坏账计提充分性。",
            ]),
            "anomalies": [
                "应收账款占用增加" if _numeric_sign(receivable_growth) > 0 else "",
                "应收周转天数拉长" if receivable_turnover_days and str(receivable_turnover_days).replace("天", "").isdigit() and int(str(receivable_turnover_days).replace("天", "")) > 90 else "",
            ],
        },
        {
            "section_title": "偿债能力与财务信号异常",
            "metrics_table": [
                {"label": "经营现金流", "value": _series_sentence(operating_cf_series, "经营活动产生的现金流量净额")},
                {"label": "经营现金流/净利润", "value": operating_cf_to_net_profit},
                {"label": "现金短债比", "value": cash_to_short_debt},
                {"label": "EBITDA利息保障倍数", "value": ebitda_interest_coverage},
            ],
            "narrative": business_prefix + _clean_join([
                _series_sentence(operating_cf_series, "经营活动产生的现金流量净额"),
                f"；经营现金流/净利润为{operating_cf_to_net_profit}，现金短债比为{cash_to_short_debt}，EBITDA利息保障倍数为{ebitda_interest_coverage}。",
                f"{bridge_conclusion}{bridge_explanation}{investment_income_judgement}经营现金流走弱、利润与现金流背离或短债集中到期，都会削弱报表偿债能力的安全边际。",
            ]),
            "anomalies": [
                "经营现金流/净利润偏低" if operating_cf_to_net_profit and _numeric_sign(str(operating_cf_to_net_profit).replace("%", "")) < 0 else "",
                "现金短债比不足" if cash_to_short_debt and _numeric_sign(str(cash_to_short_debt).replace("%", "")) < 1 else "",
            ],
        },
    ]


def _render_diagnostics(diagnostics: Dict[str, Any]) -> List[str]:
    overall = diagnostics.get("overall_evaluation") or {}
    risk_level = overall.get("risk_level") or "中风险"
    score = overall.get("score")
    score_text = f"（{score}分）" if score is not None else ""
    summary = [f"【总体评价】{risk_level}{score_text} | {overall.get('conclusion') or '财务表现需结合原始凭证和人工尽调复核。'}"]
    for index, item in enumerate(diagnostics.get("diagnostics") or [], 1):
        title = item.get("title") or (DIAGNOSTIC_DIMENSIONS[index - 1] if index <= len(DIAGNOSTIC_DIMENSIONS) else f"财务风险{index}")
        actions = item.get("verification_action") or []
        if isinstance(actions, str):
            actions = [actions]
        action_text = "；".join(str(action).strip() for action in actions if str(action).strip())
        missing_items = item.get("missing_items") or []
        if isinstance(missing_items, str):
            missing_items = [missing_items]
        missing_text = "；待补充：" + "、".join(str(value) for value in missing_items[:4]) if missing_items else ""
        summary.append(
            f"{index}. {title}\n"
            f"现象与归因：{item.get('phenomenon') or '指标现象待补充。'}{item.get('driver') or ''}\n"
            f"风险定性：{item.get('risk_level') or '中风险'}。\n"
            f"核查要点：{action_text or '补充底层明细并执行人工复核。'}{missing_text}"
        )
    boundary = diagnostics.get("data_boundary")
    if boundary:
        summary.append(f"数据边界：上述判断基于{boundary}，正式授信前仍需结合审计报告、报表附注、银行流水、纳税资料和贷款用途复核。")
    return summary[:6]


def _fallback_summary(
    enterprise_name: str,
    key_metrics: Dict[str, Any],
    risk_summary: List[str],
    recommendation: str,
    risk_rating: str,
    risk_score: int | None,
    data_boundary: str,
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    annual_report_notes: Dict[str, Any] | None = None,
) -> List[str]:
    diagnostics = _fallback_diagnostics(
        enterprise_name,
        key_metrics,
        risk_summary,
        recommendation,
        risk_rating,
        risk_score,
        data_boundary,
        key_metric_series,
        codeact_analysis=codeact_analysis,
        profit_cash_bridge=profit_cash_bridge,
        annual_report_notes=annual_report_notes,
    )
    return _render_credit_style_summary(
        enterprise_name,
        key_metrics,
        risk_rating,
        risk_score,
        recommendation,
        data_boundary,
        key_metric_series,
        diagnostics,
        profit_cash_bridge,
    )


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_summary(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    summary = []
    for item in value:
        text = str(item).strip()
        if text:
            summary.append(text)
    return summary[:6]


def _normalize_sections(value: Any, fallback_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """归一化 LLM 输出的 sections；若缺失则用 fallback 补齐。"""
    if isinstance(value, list) and len(value) >= 4:
        normalized = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("section_title") or item.get("title") or "").strip()
            if not title:
                continue
            normalized.append({
                "section_title": title,
                "metrics_table": item.get("metrics_table") if isinstance(item.get("metrics_table"), list) else [],
                "narrative": str(item.get("narrative") or item.get("content") or "").strip(),
                "anomalies": item.get("anomalies") if isinstance(item.get("anomalies"), list) else [],
            })
        if len(normalized) >= 4:
            return normalized
    # 如果没有 sections，把现有 summary 作为单一条目包装
    return fallback_sections


def _normalize_diagnostics(value: Any, fallback: Dict[str, Any], data_boundary: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    overall = value.get("overall_evaluation") if isinstance(value.get("overall_evaluation"), dict) else {}
    items = value.get("diagnostics") if isinstance(value.get("diagnostics"), list) else []
    normalized_items = []
    for index, item in enumerate(items[:3]):
        if not isinstance(item, dict):
            continue
        actions = item.get("verification_action") or item.get("verification_actions") or []
        if isinstance(actions, str):
            actions = [actions]
        missing_items = item.get("missing_items") or item.get("manual_review_items") or []
        if isinstance(missing_items, str):
            missing_items = [missing_items]
        normalized_items.append({
            "title": str(item.get("title") or (DIAGNOSTIC_DIMENSIONS[index] if index < len(DIAGNOSTIC_DIMENSIONS) else f"财务风险{index + 1}")).strip(),
            "phenomenon": str(item.get("phenomenon") or "").strip(),
            "driver": str(item.get("driver") or "").strip(),
            "risk_level": str(item.get("risk_level") or "中风险").strip(),
            "verification_action": [str(action).strip() for action in actions if str(action).strip()][:5],
            "missing_items": [str(missing).strip() for missing in missing_items if str(missing).strip()][:5],
            "rule_ids": item.get("rule_ids") if isinstance(item.get("rule_ids"), list) else [],
            "knowledge_source_ids": item.get("knowledge_source_ids") if isinstance(item.get("knowledge_source_ids"), list) else [],
        })
    if len(normalized_items) < 3:
        fallback_items = fallback.get("diagnostics") or []
        normalized_items.extend(fallback_items[len(normalized_items):3])

    return {
        "overall_evaluation": {
            "risk_level": str(overall.get("risk_level") or (fallback.get("overall_evaluation") or {}).get("risk_level") or "中风险").strip(),
            "score": overall.get("score", (fallback.get("overall_evaluation") or {}).get("score")),
            "conclusion": str(overall.get("conclusion") or (fallback.get("overall_evaluation") or {}).get("conclusion") or "财务表现需结合原始凭证和人工尽调复核。").strip(),
        },
        "diagnostics": normalized_items[:3],
        "data_boundary": value.get("data_boundary") or data_boundary,
        "manual_review_items": value.get("manual_review_items") if isinstance(value.get("manual_review_items"), list) else fallback.get("manual_review_items", []),
    }


def _summary_from_text(text: str) -> List[str]:
    """Recover usable prose when the model ignores the JSON-only instruction."""
    cleaned = re.sub(r"```(?:json)?|```", "", text or "").strip()
    cleaned = re.sub(r"^[\s\S]*?summary\s*[:：]", "", cleaned, flags=re.I).strip()
    parts = re.split(r"\n+|(?<=[。！？])\s*", cleaned)
    summary: List[str] = []
    for part in parts:
        item = re.sub(r"^[\s\-—*、，,;；\d.）)]+", "", part).strip().strip('"""[]{}')
        if len(item) >= 18 and any(keyword in item for keyword in ["营业收入", "盈利", "资产负债率", "现金流", "复核", "审计"]):
            if not item.endswith(("。", "！", "？")):
                item += "。"
            summary.append(item)
        if len(summary) >= 6:
            break
    return summary


def _has_boundary_text(summary: List[str]) -> bool:
    joined = "\n".join(summary)
    return any(keyword in joined for keyword in ["需结合", "需复核", "需核验", "需进一步核验", "审计意见", "审计报告", "报表附注", "正式授信前"])


def _ensure_boundary_summary(summary: List[str], data_boundary: str) -> List[str]:
    if _has_boundary_text(summary):
        return summary
    augmented = summary[:]
    augmented.append(f"上述判断基于{data_boundary}，正式授信前仍需结合审计报告、报表附注、银行流水和授信用途复核。")
    return augmented[:6]


def _ensure_coverage(summary: List[str], fallback: List[str]) -> tuple[List[str], List[str]]:
    """Keep LLM prose when usable, but fill missing financial dimensions."""
    checks = [
        ("收入趋势", ["营业收入", "收入"], fallback[0] if len(fallback) > 0 else ""),
        ("盈利能力", ["盈利", "净利润", "毛利率", "净利率"], fallback[1] if len(fallback) > 1 else ""),
        ("偿债能力", ["资产负债率", "流动比率", "偿债"], fallback[2] if len(fallback) > 2 else ""),
        ("现金流与营运质量", ["现金流", "应收账款"], fallback[3] if len(fallback) > 3 else ""),
    ]
    joined = "\n".join(summary)
    augmented = summary[:]
    notes: List[str] = []
    for label, keywords, fallback_line in checks:
        if fallback_line and not any(keyword in joined for keyword in keywords):
            augmented.append(fallback_line)
            joined += "\n" + fallback_line
            notes.append(f"LLM输出缺少{label}，已用结构化指标补充。")
    return augmented[:6], notes


def _allowed_numbers(
    key_metrics: Dict[str, Any],
    years: List[str],
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    risk_score: int | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
) -> Set[str]:
    allowed: Set[str] = set()
    for year in years:
        allowed.add(str(year))
    for value in key_metrics.values():
        text = str(value)
        for number in re.findall(r"\d+(?:\.\d+)?", text):
            allowed.add(number)
    for values in (key_metric_series or {}).values():
        for value in values.values():
            for number in re.findall(r"\d+(?:\.\d+)?", str(value)):
                allowed.add(number)
    if risk_score is not None:
        allowed.add(str(risk_score))
    if codeact_analysis:
        for number in re.findall(r"\d+(?:\.\d+)?", json.dumps(codeact_analysis, ensure_ascii=False, default=str)):
            allowed.add(number)
    if profit_cash_bridge:
        for number in re.findall(r"\d+(?:\.\d+)?", json.dumps(profit_cash_bridge, ensure_ascii=False, default=str)):
            allowed.add(number)
    return allowed


def _number_warnings(
    summary: List[str],
    key_metrics: Dict[str, Any],
    years: List[str],
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    risk_score: int | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
) -> List[str]:
    allowed = _allowed_numbers(key_metrics, years, key_metric_series, risk_score, codeact_analysis, profit_cash_bridge)
    warnings = []
    text = "\n".join(summary)
    text = re.sub(r"FIN-[A-Z]+-\d+", "", text)
    text = re.sub(r"source_id['\"]?\s*[:：]\s*['\"]?kb_[0-9a-f]+", "", text, flags=re.I)
    for number in re.findall(r"\d+(?:\.\d+)?", text):
        if number not in allowed:
            # Ignore ordinary phrase fragments such as 12个月 in review guidance and section numbers.
            if number in {"1", "2", "3", "4", "5", "6", "12", "70", "80", "100", "3.1", "3.2", "3.3", "3.4"}:
                continue
            warnings.append(f"LLM输出包含未提供的数字：{number}")
    return warnings[:5]


def _quality_warnings(
    summary: List[str],
    key_metrics: Dict[str, Any],
    years: List[str],
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    risk_score: int | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
) -> List[str]:
    warnings: List[str] = []
    if not 4 <= len(summary) <= 6:
        warnings.append("LLM输出段落数量不符合4-6条要求")
    joined = "\n".join(summary)
    for term in BANNED_TERMS:
        if term in joined:
            warnings.append(f"LLM输出包含禁用表达：{term}")
    warnings.extend(_ocr_error_warnings(joined))
    warnings.extend(_metric_label_warnings(joined))
    if not _has_boundary_text(summary):
        warnings.append("LLM输出缺少数据边界或人工复核提示")
    warnings.extend(_number_warnings(summary, key_metrics, years, key_metric_series, risk_score, codeact_analysis, profit_cash_bridge))
    return warnings


def _business_penetration_warnings(
    text: str,
    financial_business_hints: List[str] | None = None,
) -> List[str]:
    """检查财务叙事是否具备经营穿透深度。"""
    warnings: List[str] = []
    cfg = _BUSINESS_PENETRATION
    causal_words = cfg.get("causal_words") or ["主因是", "受", "影响", "反映", "表明", "导致", "源于"]
    causal_threshold = cfg.get("causal_count_threshold", 3)
    hint_threshold = cfg.get("hint_hits_threshold", 2)
    required_sections = cfg.get("required_sections") or ["收入与利润", "资产负债", "盈利质量", "偿债能力"]

    # 1. 因果表达词检查
    causal_count = sum(1 for word in causal_words if word in text)
    if causal_count < causal_threshold:
        warnings.append(f"财务叙事缺乏业务动因解释（因果表达词仅{causal_count}个，需至少{causal_threshold}个）")

    # 2. financial_business_hints 关键词覆盖检查（支持子串/关键词命中）
    if financial_business_hints:
        norm_text = text.replace(" ", "").replace("，", "").replace("。", "").replace("、", "")
        hint_hits = 0
        for hint in financial_business_hints:
            norm_hint = hint.replace(" ", "").replace("，", "").replace("。", "").replace("、", "")
            if norm_hint and norm_hint in norm_text:
                hint_hits += 1
                continue
            # 退回到关键词：取 hint 中长度>=2 的连续词组
            tokens = [
                norm_hint[i : i + 4]
                for i in range(0, max(1, len(norm_hint) - 3))
            ] or [norm_hint]
            if any(token and token in norm_text for token in tokens):
                hint_hits += 1
        if hint_hits < hint_threshold:
            warnings.append(f"财务叙事未充分使用业务归因提示（仅命中{hint_hits}个关键词，需至少{hint_threshold}个）")

    # 3. 四大板块标题检查
    missing_sections = [sec for sec in required_sections if sec not in text]
    if missing_sections:
        warnings.append(f"财务叙事缺少四大板块标题：{', '.join(missing_sections)}")

    # 4. 核心判断检查
    if "核心判断：" not in text:
        warnings.append("财务叙事缺少板块核心判断（每个板块 narrative 必须以'核心判断：'开头）")

    # 5. 行业上下文引用检查（仅当提供了 hints 时才检查）
    if financial_business_hints:
        has_industry_baseline = "[需补充：行业基准]" in text
        has_industry_keyword = False
        for hint in financial_business_hints:
            tokens = [hint[i : i + 4] for i in range(0, max(1, len(hint) - 3))] or [hint]
            if any(token and token in text for token in tokens):
                has_industry_keyword = True
                break
        if not has_industry_baseline and not has_industry_keyword:
            warnings.append("财务叙事未充分引用行业上下文（缺少行业基准或业务归因关键词）")

    return warnings


def _diagnostic_text(diagnostics: Dict[str, Any]) -> str:
    return json.dumps(diagnostics or {}, ensure_ascii=False, default=str)


def _diagnostic_warnings(diagnostics: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    diagnostic_text = _diagnostic_text(diagnostics)
    for term in BANNED_TERMS:
        if term in diagnostic_text:
            warnings.append(f"LLM诊断字段包含禁用表达：{term}")
    warnings.extend(_ocr_error_warnings(diagnostic_text))
    warnings.extend(_metric_label_warnings(diagnostic_text))
    if not isinstance(diagnostics.get("overall_evaluation"), dict):
        warnings.append("LLM输出缺少overall_evaluation")
    items = diagnostics.get("diagnostics") or []
    if len(items) < 3:
        warnings.append("LLM输出诊断维度不足3项")
    for index, item in enumerate(items[:3], 1):
        for field in ["phenomenon", "driver", "risk_level", "verification_action"]:
            if not item.get(field):
                warnings.append(f"第{index}项缺少{field}")
    return warnings[:6]


def _prompt(
    enterprise_name: str,
    years: List[str],
    key_metrics: Dict[str, Any],
    key_metric_series: Dict[str, Dict[str, str]] | None,
    risk_summary: List[str],
    recommendation: str,
    risk_rating: str,
    risk_score: int | None,
    data_boundary: str,
    knowledge_context: Dict[str, Any] | None = None,
    public_context: List[Dict[str, Any]] | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    annual_report_notes: Dict[str, Any] | None = None,
    industry_context: Dict[str, Any] | None = None,
    business_segments: List[Dict[str, Any]] | None = None,
    annual_business_review: Dict[str, Any] | None = None,
    financial_business_hints: List[str] | None = None,
) -> str:
    # 防御性归一化：上游可能传入字符串而非 dict/list
    if isinstance(industry_context, str):
        industry_context = None
    if isinstance(annual_business_review, str):
        annual_business_review = {"summary": annual_business_review}
    if isinstance(business_segments, str):
        business_segments = None

    metric_lines = "；".join(f"{key}={value}" for key, value in key_metrics.items())
    series_lines = json.dumps(key_metric_series or {}, ensure_ascii=False)
    score_json = str(risk_score) if risk_score is not None else "null"
    allowed_numbers = sorted(_allowed_numbers(key_metrics, years, key_metric_series, risk_score, codeact_analysis, profit_cash_bridge))
    knowledge_context = knowledge_context or {}
    triggered_rules = knowledge_context.get("triggered_rules") or []
    knowledge_briefs = knowledge_context.get("knowledge_briefs") or []
    knowledge_lines = json.dumps({
        "triggered_rules": [
            {
                "rule_id": rule.get("rule_id"),
                "title": rule.get("title"),
                "dimension": rule.get("dimension"),
                "risk_label": rule.get("risk_label"),
                "risk_level": rule.get("risk_level"),
                "prompt_hint": rule.get("prompt_hint"),
            }
            for rule in triggered_rules[:4]
        ],
        "rag_knowledge": knowledge_briefs[:3],
    }, ensure_ascii=False)
    # Separate PDF annual report content from general public search results
    pdf_narrative_items = []
    general_public_items = []
    for item in (public_context or []):
        source_type = item.get("source_type") or ""
        content = item.get("content") or item.get("summary") or item.get("value") or ""
        if "exchange_announcement" in source_type or "巨潮" in str(item.get("source")) or "年报" in str(item.get("title")):
            pdf_narrative_items.append({
                "title": item.get("title") or item.get("label"),
                "source": item.get("source") or item.get("source_name"),
                "content": content[:800],
            })
        else:
            general_public_items.append({
                "title": item.get("title") or item.get("label"),
                "source": item.get("source") or item.get("source_name"),
                "content": content[:360],
            })
    pdf_narrative_lines = json.dumps(pdf_narrative_items[:4], ensure_ascii=False)
    public_lines = json.dumps(general_public_items[:4], ensure_ascii=False)
    codeact_lines = json.dumps({
        "financial_ratios": (codeact_analysis or {}).get("metrics") or {},
        "growth_metrics": (codeact_analysis or {}).get("growth_metrics") or {},
        "statement_validation": {
            "passed": (codeact_analysis or {}).get("validation_passed"),
            "issues": (codeact_analysis or {}).get("validation_issues") or [],
            "warnings": (codeact_analysis or {}).get("validation_warnings") or [],
        },
    }, ensure_ascii=False, default=str)
    profit_cash_bridge_lines = json.dumps(profit_cash_bridge or {}, ensure_ascii=False, default=str)

    # 年报深度归因：从经营情况讨论与分析章节抽取的管理层解释，权威定性来源。
    attribution = (annual_report_notes or {}).get("attribution") or {}
    attribution_payload: Dict[str, Any] = {}
    if attribution and attribution.get("source") != "fallback":
        attribution_payload = {
            "data_boundary": attribution.get("data_boundary"),
            "source": attribution.get("source"),
            "revenue_drivers": attribution.get("revenue_drivers") or [],
            "margin_drivers": attribution.get("margin_drivers") or [],
            "profit_drivers": attribution.get("profit_drivers") or [],
            "capacity_status": attribution.get("capacity_status"),
            "industry_context": attribution.get("industry_context"),
            "company_strategy": attribution.get("company_strategy"),
            "forward_risks": attribution.get("forward_risks") or [],
        }
    attribution_lines = json.dumps(attribution_payload, ensure_ascii=False, default=str)

    # 业务上下文构建
    industry_summary = ""
    if industry_context:
        diag = industry_context.get("diagnosis_summary") or industry_context.get("data_anchor") or ""
        industry_summary = str(diag)[:800]
    segments_summary = ""
    if business_segments:
        segments = business_segments[:5]
        parts = []
        for seg in segments:
            name = seg.get("segment_name") or seg.get("name") or ""
            ratio = seg.get("revenue_ratio") or seg.get("ratio") or ""
            if name:
                parts.append(f"{name}({ratio})" if ratio else name)
        segments_summary = "、".join(parts)
    review_summary = ""
    if annual_business_review:
        review = annual_business_review.get("management_review") or annual_business_review.get("summary") or ""
        review_summary = str(review)[:800]
    hints_summary = ""
    if financial_business_hints:
        hints_summary = "；".join(financial_business_hints[:5])
    business_context_lines = json.dumps({
        "industry_summary": industry_summary,
        "business_segments": segments_summary,
        "annual_business_review": review_summary,
        "financial_business_hints": hints_summary,
    }, ensure_ascii=False, default=str)

    template = load_prompt_template("financial_narrative")
    variables = {
        "enterprise_name": enterprise_name,
        "years": ",".join(years),
        "risk_label": _risk_label(risk_rating),
        "risk_score": risk_score,
        "metric_lines": metric_lines,
        "series_lines": series_lines,
        "risk_summary": "；".join(risk_summary[:3]),
        "recommendation": recommendation,
        "data_boundary": data_boundary,
        "codeact_lines": codeact_lines,
        "profit_cash_bridge_lines": profit_cash_bridge_lines,
        "knowledge_lines": knowledge_lines,
        "attribution_lines": attribution_lines,
        "pdf_narrative_lines": pdf_narrative_lines,
        "public_lines": public_lines,
        "business_context_lines": business_context_lines,
        "banned_terms": ", ".join(BANNED_TERMS),
        "score_json": score_json,
    }
    return render_prompt_template(template, variables).strip()


def _invoke_one_llm(
    provider: str,
    llm: ChatOpenAI,
    prompt: str,
    session_id: str | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    started_at = time.monotonic()
    response = cached_invoke(llm, prompt, session_id=session_id, task_id=task_id)
    return {
        "provider": provider,
        "raw_response": str(getattr(response, "content", response)),
        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
        "response_metadata": getattr(response, "response_metadata", {}) or {},
    }


def _parse_candidate(
    raw_response: str,
    enterprise_name: str,
    risk_rating: str,
    recommendation: str,
    fallback: List[str],
    fallback_diagnostics: Dict[str, Any],
    key_metrics: Dict[str, Any],
    years: List[str],
    data_boundary: str,
    key_metric_series: Dict[str, Dict[str, str]] | None,
    risk_score: int | None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    financial_business_hints: List[str] | None = None,
) -> tuple[List[str], Dict[str, Any], List[str], List[str]]:
    parsed = _extract_json(raw_response)
    diagnostics = _normalize_diagnostics(parsed, fallback_diagnostics, data_boundary) if parsed else {}
    if diagnostics:
        summary = _render_credit_style_summary(
            enterprise_name,
            key_metrics,
            risk_rating,
            risk_score,
            recommendation,
            data_boundary,
            key_metric_series,
            diagnostics,
            profit_cash_bridge,
        )
    else:
        summary = _normalize_summary(parsed.get("summary")) or _summary_from_text(raw_response)
        diagnostics = fallback_diagnostics
    summary = _ensure_boundary_summary(summary, data_boundary)
    summary, augmentation_notes = _ensure_coverage(summary, fallback)
    warnings = _diagnostic_warnings(diagnostics) + _quality_warnings(summary, key_metrics, years, key_metric_series, risk_score, codeact_analysis, profit_cash_bridge)
    # 经营穿透质量门控：同时检查 summary 和 sections narrative
    joined_text = "\n".join(summary)
    if parsed:
        section_texts = [
            sec.get("narrative", "") for sec in (parsed.get("sections") or []) if sec.get("narrative")
        ]
        joined_text += "\n" + "\n".join(section_texts)
    warnings.extend(_business_penetration_warnings(joined_text, financial_business_hints))
    return summary, diagnostics, warnings, augmentation_notes


def _invoke_llm_race_with_timeout(
    prompt: str,
    enterprise_name: str,
    risk_rating: str,
    recommendation: str,
    fallback: List[str],
    fallback_diagnostics: Dict[str, Any],
    key_metrics: Dict[str, Any],
    years: List[str],
    data_boundary: str,
    key_metric_series: Dict[str, Dict[str, str]] | None,
    risk_score: int | None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    financial_business_hints: List[str] | None = None,
) -> Dict[str, Any]:
    futures: Dict[Future, str] = {
        _LLM_EXECUTOR.submit(_invoke_one_llm, provider, llm, prompt, session_id, task_id): provider
        for provider, llm in _available_narrative_llms()
    }
    if not futures:
        raise RuntimeError("未配置可用财务叙述 LLM")
    try:
        deadline = time.monotonic() + LLM_NARRATIVE_TIMEOUT_SECONDS
        errors: List[str] = []
        first_candidate: Dict[str, Any] | None = None
        while futures:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            done, _ = wait(futures.keys(), timeout=remaining, return_when=FIRST_COMPLETED)
            if not done:
                break
            for future in done:
                provider = futures.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    errors.append(f"{provider}失败：{type(exc).__name__}")
                    continue
                if result.get("raw_response"):
                    summary, diagnostics, warnings, augmentation_notes = _parse_candidate(
                        result["raw_response"],
                        enterprise_name,
                        risk_rating,
                        recommendation,
                        fallback,
                        fallback_diagnostics,
                        key_metrics,
                        years,
                        data_boundary,
                        key_metric_series,
                        risk_score,
                        codeact_analysis,
                        profit_cash_bridge,
                        financial_business_hints=financial_business_hints,
                    )
                    result["summary"] = summary
                    result["diagnostics"] = diagnostics
                    result["quality_warnings"] = warnings
                    result["augmentation_notes"] = augmentation_notes
                    if not warnings:
                        for pending in futures:
                            pending.cancel()
                        result["race_errors"] = errors
                        return result
                    if first_candidate is None:
                        first_candidate = result
                    errors.append(f"{provider}未通过质量闸门：{'；'.join(warnings[:3])}")
                    continue
                finish_reason = (result.get("response_metadata") or {}).get("finish_reason")
                errors.append(f"{provider}返回空内容" + (f"，finish_reason={finish_reason}" if finish_reason else ""))
        for pending in futures:
            pending.cancel()
        if first_candidate is not None:
            first_candidate["race_errors"] = errors
            return first_candidate
        raise TimeoutError("；".join(errors) or f"LLM财务叙述超过{LLM_NARRATIVE_TIMEOUT_SECONDS}秒未返回")
    except TimeoutError as exc:
        raise TimeoutError(f"LLM财务叙述超过{LLM_NARRATIVE_TIMEOUT_SECONDS}秒未返回") from exc


def build_financial_narrative(
    enterprise_name: str,
    years: List[str],
    key_metrics: Dict[str, Any],
    risk_summary: List[str],
    recommendation: str,
    risk_rating: str = "medium",
    risk_score: int | None = None,
    data_boundary: str = "已解析的财务报表数据",
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    knowledge_context: Dict[str, Any] | None = None,
    public_context: List[Dict[str, Any]] | None = None,
    codeact_analysis: Dict[str, Any] | None = None,
    profit_cash_bridge: Dict[str, Any] | None = None,
    structured_financial_package: Dict[str, Any] | None = None,
    annual_report_notes: Dict[str, Any] | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    industry_context: Dict[str, Any] | None = None,
    business_segments: List[Dict[str, Any]] | None = None,
    annual_business_review: Dict[str, Any] | None = None,
    financial_business_hints: List[str] | None = None,
) -> Dict[str, Any]:
    """Build financial narrative with LLM and guarded fallback.

    When ``structured_financial_package`` is provided, it becomes the authoritative
    source for metric values, series and data boundary. Legacy ``key_metrics`` and
    ``key_metric_series`` are still accepted for backward compatibility.
    """
    if structured_financial_package:
        key_metrics, key_metric_series, data_boundary, risk_summary = _derive_inputs_from_structured_package(
            structured_financial_package,
            key_metrics,
            key_metric_series,
            data_boundary,
            risk_summary,
        )

    key_metrics = dict(key_metrics or {})
    key_metrics.setdefault("enterprise_name", enterprise_name)
    fallback_diagnostics = _fallback_diagnostics(
        enterprise_name,
        key_metrics,
        risk_summary,
        recommendation,
        risk_rating,
        risk_score,
        data_boundary,
        key_metric_series,
        knowledge_context,
        codeact_analysis=codeact_analysis,
        profit_cash_bridge=profit_cash_bridge,
        annual_report_notes=annual_report_notes,
        industry_context=industry_context,
        business_segments=business_segments,
        annual_business_review=annual_business_review,
        financial_business_hints=financial_business_hints,
    )
    fallback = _render_credit_style_summary(
        enterprise_name,
        key_metrics,
        risk_rating,
        risk_score,
        recommendation,
        data_boundary,
        key_metric_series,
        fallback_diagnostics,
        profit_cash_bridge,
    )
    started_at = time.monotonic()
    try:
        candidate = _invoke_llm_race_with_timeout(
            _prompt(enterprise_name, years, key_metrics, key_metric_series, risk_summary, recommendation, risk_rating, risk_score, data_boundary, knowledge_context, public_context, codeact_analysis, profit_cash_bridge, annual_report_notes, industry_context, business_segments, annual_business_review, financial_business_hints),
            enterprise_name,
            risk_rating,
            recommendation,
            fallback,
            fallback_diagnostics,
            key_metrics,
            years,
            data_boundary,
            key_metric_series,
            risk_score,
            codeact_analysis,
            profit_cash_bridge,
            session_id=session_id,
            task_id=task_id,
            financial_business_hints=financial_business_hints,
        )
        summary = candidate.get("summary") or []
        warnings = candidate.get("quality_warnings") or []
        # 归一化 sections
        parsed = _extract_json(candidate.get("raw_response", ""))
        fallback_sections = fallback_diagnostics.get("sections") or []
        sections = _normalize_sections(parsed.get("sections") if parsed else None, fallback_sections)
        if warnings:
            return {
                "success": False,
                "source": "fallback",
                "summary": fallback,
                "diagnostics": fallback_diagnostics,
                "sections": sections,
                "quality_warnings": warnings + (candidate.get("race_errors") or []),
                "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
                "llm_provider": candidate.get("provider"),
            }
        return {
            "success": True,
            "source": "llm",
            "summary": summary,
            "diagnostics": candidate.get("diagnostics") or fallback_diagnostics,
            "sections": sections,
            "quality_warnings": (candidate.get("augmentation_notes") or []) + (candidate.get("race_errors") or []),
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
            "llm_provider": candidate.get("provider"),
        }
    except Exception as exc:  # LLM failures should not block report generation.
        import traceback
        traceback.print_exc()
        fallback_sections = fallback_diagnostics.get("sections") or []
        return {
            "success": False,
            "source": "fallback",
            "summary": fallback,
            "diagnostics": fallback_diagnostics,
            "sections": fallback_sections,
            "quality_warnings": [f"LLM财务叙述生成失败：{type(exc).__name__}"],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }
