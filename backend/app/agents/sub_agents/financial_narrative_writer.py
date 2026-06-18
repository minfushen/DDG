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

from langchain_openai import ChatOpenAI

from app.config import settings


BANNED_TERMS = [
    "此前为",
    "销售额为",
    "资产持有率",
    "流动资金比例",
    "经营活动量净额",
    "财务指标整体准确",
    "建议授信",
    "牛奶准入",
    "细线准入",
    "兜模拟底",
    "债务比率",
    "极强",
    "绝对安全",
    "完全无风险",
    "欠质量",
    "现象与增益",
    "主要血",
    "现象与极限",
    "经营杠杆/利息",
    "目的要点",
    "有息保安",
    "设有及或有库存",
    "营运收益",
    "经营同期/日历",
    "应收昔",
    "剩余金额净额",
    "纳税规模增长未能转化",
    "资产风险真实性",
    "流动负债为1.",
    "经营程度与收入增长",
    # OCR/识别错误词与低质量口语表达
    "鱼子",
    "鱼籽",
    "显着",
    "显箸",
    "什么玩意儿",
    "啥玩意儿",
    "玩意儿",
    # 财务叙述常见错误表达
    "资产证券分析",
    "最新原来",
    "同期波动",
    "近期一期",
    "资产拓展",
]

LLM_NARRATIVE_TIMEOUT_SECONDS = max(60, settings.LLM_TIMEOUT_SECONDS)
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="financial-narrative")


@lru_cache()
def _get_primary_narrative_llm() -> ChatOpenAI:
    """Configure primary LLM for structured financial prose."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0,
        max_tokens=8192,
        timeout=max(settings.LLM_TIMEOUT_SECONDS, LLM_NARRATIVE_TIMEOUT_SECONDS),
        max_retries=1,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


@lru_cache()
def _get_backup_narrative_llm() -> ChatOpenAI | None:
    if not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY or not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL:
        return None
    return ChatOpenAI(
        model=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_MODEL or settings.LLM_MODEL,
        api_key=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY,
        base_url=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL,
        temperature=0,
        max_tokens=8192,
        timeout=max(settings.LLM_TIMEOUT_SECONDS, LLM_NARRATIVE_TIMEOUT_SECONDS),
        max_retries=1,
        model_kwargs={"response_format": {"type": "json_object"}},
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


# 常见 OCR / 识别错误词 -> 建议正确写法。用于把质量警告写得更可执行。
_OCR_ERROR_HINTS = {
    "鱼子": "ROE（净资产收益率）",
    "鱼籽": "ROE（净资产收益率）",
    "显着": "显著",
    "显箸": "显著",
    "什么玩意儿": "删除口语化表达",
    "啥玩意儿": "删除口语化表达",
    "玩意儿": "删除口语化表达",
    "资产证券分析": "资产负债分析",
    "最新原来": "最新同比增速",
    "同期波动": "同比变动/同比增速",
    "近期一期": "最近一期",
    "资产拓展": "资产扩张",
}


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

    summary = [
        f"【总体评价】{risk_level}{score_text} | {enterprise_name}财务表现呈{risk_level}，{recommendation}。授信前应重点复核盈利质量、经营现金流、应收回款和短期偿债安排。",
        _clean_join([
            "3.1 收入与利润分析：",
            _series_sentence(revenue_series, "营业收入"),
            f"，{latest_year}年较上年增长{revenue_growth}，近三年CAGR为{revenue_cagr}。",
            _series_sentence(net_profit_series, "净利润"),
            f"；{latest_year}年营业成本为{cost}，扣非净利润为{deducted_net_profit}，毛利率为{gross_margin}、销售净利率为{net_margin}。",
            f"{deducted_profit_judgement}收入增长能否转化为稳定利润，需要结合主营构成、价格变化、费用结构、非经常性损益和行业景气度继续核验。",
        ]),
        _clean_join([
            "3.2 资产负债分析：",
            _series_sentence(debt_ratio_series, "资产负债率"),
            f"，较首年变化{debt_ratio_change}；{latest_year}年短期借款为{short_loan}，流动比率为{current_ratio}，较首年变化{current_ratio_change}。",
            f"{heavy_asset_judgement}若杠杆上升或流动比率下降，应进一步拆分短期借款、应付票据、应付账款、或有负债和未使用授信额度，判断未来12个月偿债压力。",
        ]),
        _clean_join([
            "3.3 盈利质量与营运效率：",
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

    def rule_ids_for(dimension: str) -> List[str]:
        return [rule.get("rule_id") for rule in triggered_rules if rule.get("rule_id") and rule.get("dimension") == dimension][:4]

    risk_label = _risk_label(risk_rating)
    score_text = f"（{risk_score}分）" if risk_score is not None else ""
    return {
        "overall_evaluation": {
            "risk_level": risk_label,
            "score": risk_score,
            "conclusion": f"{enterprise_name}财务表现呈{risk_label}{score_text}，{recommendation}",
        },
        "diagnostics": [
            {
                "title": "盈利质量与成长性风险",
                "phenomenon": f"{series_text(revenue_series, '营业收入')}，{latest_year}年较上年增长{revenue_growth}，近三年CAGR为{revenue_cagr}；{series_text(net_profit_series, '净利润')}，{latest_year}年毛利率为{gross_margin}、销售净利率为{net_margin}。",
                "driver": (profit_cash_bridge.get("deducted_profit_judgement") or "") + "收入增长质量需结合主营构成、订单连续性、费用结构、非经常性损益和行业景气度复核；若利润修复弱于收入扩张，需警惕规模增长未能转化为主营造血能力。",
                "risk_level": "中风险" if risk_rating != "high" else "中高风险",
                "verification_action": ["拆分收入增长的产品、客户和区域来源", "核验毛利率与同业、历史期间的差异", "复核非经常性损益、政府补助和费用资本化影响"],
                "missing_items": ["主营构成明细", "同业毛利率基准", "审计意见和报表附注"],
                "rule_ids": rule_ids_for("盈利质量与成长性风险"),
                "knowledge_source_ids": source_ids[:3],
            },
            {
                "title": "资产真实性与营运效率风险",
                "phenomenon": f"{latest_year}年应收账款余额为{receivable}，应收/营收占比为{receivable_to_revenue}，应收账款较上年增长{receivable_growth}；{series_text(operating_cf_series, '经营活动产生的现金流量净额')}，经营现金流/净利润为{operating_cf_to_net_profit}。",
                "driver": "若应收增速高于收入增速或经营现金流弱于利润表现，需关注信用政策放宽、客户集中回款滞后和收入确认质量。" + (profit_cash_bridge.get("bridge_explanation") or ""),
                "risk_level": "中风险",
                "verification_action": ["获取应收账龄结构和前十大客户余额", "执行期后回款测试和函证程序", "复核坏账计提充分性及客户信用政策变化"],
                "missing_items": ["应收账龄表", "前十大客户回款明细", "银行流水和纳税申报匹配材料"],
                "rule_ids": rule_ids_for("资产真实性与营运效率风险"),
                "knowledge_source_ids": source_ids[:3],
            },
            {
                "title": "资本结构与偿债能力风险",
                "phenomenon": f"{series_text(debt_ratio_series, '资产负债率')}，较首年变化{debt_ratio_change}；{latest_year}年流动比率为{current_ratio}，较首年变化{current_ratio_change}。",
                "driver": (profit_cash_bridge.get("credit_implication") or "") + "杠杆变化和流动比率下降需结合短期借款、应付账款、票据融资、或有负债及未使用授信额度判断，报表流动性不等同于可即时偿债现金。",
                "risk_level": "中风险" if risk_rating != "low" else "低中风险",
                "verification_action": ["编制未来12个月债务到期和现金流预测", "核实短期借款、票据、担保和或有负债", "评估应收账款保理、票据贴现等表外融资安排"],
                "missing_items": ["有息负债明细", "担保及或有负债清单", "未来12个月现金流预测"],
                "rule_ids": rule_ids_for("资本结构与偿债能力风险"),
                "knowledge_source_ids": source_ids[:3],
            },
        ],
        "data_boundary": data_boundary,
        "profit_cash_bridge": profit_cash_bridge,
        "manual_review_items": ["审计报告及附注", "银行流水", "纳税资料", "主要合同", first_risk] + reconciliation_notes[:4],
    }


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
        item = re.sub(r"^[\s\-—*、，,;；\d.）)]+", "", part).strip().strip('"“”[]{}')
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
) -> str:
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
    public_lines = json.dumps([
        {
            "title": item.get("title") or item.get("label"),
            "source": item.get("source") or item.get("source_name"),
            "content": (item.get("content") or item.get("summary") or item.get("value") or "")[:360],
        }
        for item in (public_context or [])[:6]
    ], ensure_ascii=False)
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
    return f"""
你是银行贷前尽调财务分析师。请把结构化财务指标升级为“诊断性”风险分析，只输出 JSON，不要输出 Markdown 或解释过程。

输入数据：公司={enterprise_name}；年度={','.join(years)}；风险评级={_risk_label(risk_rating)}；风险分={risk_score}；最新指标={metric_lines}；近三年指标序列={series_lines}。
已有风险提示：{'；'.join(risk_summary[:3])}。授信建议：{recommendation}。数据边界：{data_boundary}。
CodeAct确定性计算与三大表勾稽结果（优先使用，不能与其冲突）：{codeact_lines}
CPA利润-现金流桥确定性诊断（优先使用，不能与其冲突）：{profit_cash_bridge_lines}
本次动态注入的领域知识：{knowledge_lines}
公开公告/搜索线索（仅用于归因和核查方向，不得直接引用其中未经结构化校验的数字）：{public_lines}

硬性要求：
1. 必须分析近三年趋势，不能只点评最新一年。
2. 每个数据点必须搭配同比/首尾变化/CAGR/占比/关联指标中的至少一项作为参照系。
3. 必须输出3个诊断维度：盈利质量与成长性风险、资产真实性与营运效率风险、资本结构与偿债能力风险。
4. 每个诊断维度必须包含 phenomenon、driver、risk_level、verification_action、missing_items。
5. 必须优先使用 triggered_rules 和 rag_knowledge 中的领域规则；每个诊断维度尽量引用 rule_id 或 source_id。
6. 必须优先使用 CodeAct 的 financial_ratios 和 statement_validation；如存在 P0/P1 勾稽问题，必须写入对应诊断维度和人工复核清单。
7. 当应收增速或应收/营收偏高时，必须关联经营现金流、信用政策、期后回款和坏账计提。
8. 当资产负债率上升或流动比率下降时，必须关联短债、应付账款/票据、或有负债和未来12个月偿债压力。
9. 必须使用利润-现金流桥解释净利润、扣非净利润、经营现金流、折旧摊销、减值损失、投资收益之间的关系；缺失字段必须写成[需补充：...]。
10. 若净利润下降但经营现金流为正，应说明现金流可能优于账面利润，但扣非利润、折旧摊销、资产减值和产能利用率仍需核查；不得简单写成“现金流差”。
11. 若扣非净利润连续为负，应明确“主营业务尚未实现真正盈利/主营造血能力未实质修复”。
12. 只使用输入数据，不编造数字；不得引入行业均值、行业平均、同业水平等未提供数字；除段落编号和“12个月”外，输出中只能出现这些数字：{', '.join(allowed_numbers)}。
13. 公告/搜索线索可用于解释“可能原因”和“核查方向”，但不得把其中数字写入结论，除非该数字也出现在最新指标、近三年指标序列、CodeAct结果或利润-现金流桥中。
14. 缺失原因、行业基准或同业数据时用”[需补充：...]”，不要自行估算。
15. summary 段落编号必须使用标准标题：3.1 收入与利润分析、3.2 资产负债分析、3.3 盈利质量与营运效率、3.4 偿债能力与财务信号异常；不得写成”资产证券分析”等错误标题。
16. 增长率/变动率必须表述为”同比增速”或”同比变动”，不得使用”原来””同期波动””近期一期”等错误表达。
17. 禁止：{', '.join(BANNED_TERMS)}。

JSON格式：
{{
  "overall_evaluation": {{"risk_level": "{_risk_label(risk_rating)}", "score": {score_json}, "conclusion": "一句话总体评价"}},
  "diagnostics": [
    {{"title": "盈利质量与成长性风险", "phenomenon": "现象与数据参照", "driver": "归因和风险逻辑", "risk_level": "中风险", "verification_action": ["核查动作"], "missing_items": ["待补充材料"], "rule_ids": ["触发规则ID"], "knowledge_source_ids": ["知识片段ID"]}},
    {{"title": "资产真实性与营运效率风险", "phenomenon": "现象与数据参照", "driver": "归因和风险逻辑", "risk_level": "中风险", "verification_action": ["核查动作"], "missing_items": ["待补充材料"], "rule_ids": ["触发规则ID"], "knowledge_source_ids": ["知识片段ID"]}},
    {{"title": "资本结构与偿债能力风险", "phenomenon": "现象与数据参照", "driver": "归因和风险逻辑", "risk_level": "中风险", "verification_action": ["核查动作"], "missing_items": ["待补充材料"], "rule_ids": ["触发规则ID"], "knowledge_source_ids": ["知识片段ID"]}}
  ],
  "data_boundary": "{data_boundary}",
  "manual_review_items": ["人工复核清单"]
}}
""".strip()


def _invoke_one_llm(provider: str, llm: ChatOpenAI, prompt: str) -> Dict[str, Any]:
    started_at = time.monotonic()
    response = llm.invoke(prompt)
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
) -> Dict[str, Any]:
    futures: Dict[Future, str] = {
        _LLM_EXECUTOR.submit(_invoke_one_llm, provider, llm, prompt): provider
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
            _prompt(enterprise_name, years, key_metrics, key_metric_series, risk_summary, recommendation, risk_rating, risk_score, data_boundary, knowledge_context, public_context, codeact_analysis, profit_cash_bridge),
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
        )
        summary = candidate.get("summary") or []
        warnings = candidate.get("quality_warnings") or []
        if warnings:
            return {
                "success": False,
                "source": "fallback",
                "summary": fallback,
                "diagnostics": fallback_diagnostics,
                "quality_warnings": warnings + (candidate.get("race_errors") or []),
                "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
                "llm_provider": candidate.get("provider"),
            }
        return {
            "success": True,
            "source": "llm",
            "summary": summary,
            "diagnostics": candidate.get("diagnostics") or fallback_diagnostics,
            "quality_warnings": (candidate.get("augmentation_notes") or []) + (candidate.get("race_errors") or []),
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
            "llm_provider": candidate.get("provider"),
        }
    except Exception as exc:  # LLM failures should not block report generation.
        return {
            "success": False,
            "source": "fallback",
            "summary": fallback,
            "diagnostics": fallback_diagnostics,
            "quality_warnings": [f"LLM财务叙述生成失败：{type(exc).__name__}"],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }
