"""LLM-assisted attribution extractor for annual report business review.

The deterministic financial pipeline produces "财务数据 + 通用归因模板"，例如
"毛利率下滑通常受行业产能过剩、产品价格下行、产能爬坡期固定成本摊销较高…
影响"。这与 Manus 级别的高度具体归因（如「LED 芯片行业产能过剩导致产品
价格下行」「集成电路业务尚处于产能爬坡期」）存在差距——后者源自对年报
"经营情况讨论与分析"章节的深度阅读。

本模块接受年报 ``business_review`` 原文 + 结构化关键指标 + 主营构成，调用
分析诊断 LLM 池（复用竞速模式）抽取可溯源的归因结构：

- 每个 factor 必须带 evidence（年报原文引用，≤120 字）。
- 不得编造数字；无法抽取的字段写 ``[需补充]``。
- 无原文 / LLM 失败时返回空结构，绝不阻塞报告生成。

抽取结果由 ``financial_report_builder`` / ``financial_narrative_writer`` /
``industry_diagnostic_writer`` 作为权威定性归因引用，替换通用模板话术。
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import json
import logging
import re
import time
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI

from app.config import settings
from app.config.llm_config import cached_invoke, get_analysis_llm_pool
from app.config.prompt_loader import load_prompt_template, render_prompt_template
from app.config.quality_gate_loader import get_banned_terms


logger = logging.getLogger(__name__)

# 触发阈值：年报经营讨论正文过短时不值得调 LLM（用户确认：仅年报有正文才调）。
MIN_BUSINESS_REVIEW_CHARS = 500

LLM_ATTRIBUTION_TIMEOUT_SECONDS = max(60, settings.ANALYSIS_LLM_TIMEOUT_SECONDS)
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="annual-report-attribution")

# 与财务叙述保持一致的禁用表达，防止 OCR 残留/口语化词进入报告。
BANNED_TERMS = get_banned_terms("annual_report_attribution")

# 归因抽取的复用底库：当 LLM 全部失败时返回，保证下游可优雅降级。
EMPTY_ATTRIBUTION: Dict[str, Any] = {
    "revenue_drivers": [],
    "margin_drivers": [],
    "profit_drivers": [],
    "capacity_status": "",
    "industry_context": "",
    "company_strategy": "",
    "forward_risks": [],
    "data_boundary": "未获取到年报经营情况讨论正文，无法进行深度归因抽取。",
    "source": "fallback",
}


# --------------------------------------------------------------------------- #
# 输入归一化
# --------------------------------------------------------------------------- #
def _has_substantive_review(business_review: str | None) -> bool:
    """仅当年报经营讨论正文长度达到阈值才值得调 LLM。"""
    return bool(business_review and len(business_review.strip()) >= MIN_BUSINESS_REVIEW_CHARS)


def _segment_summary(business_segments: List[Dict[str, Any]] | None, limit: int = 8) -> str:
    rows: List[str] = []
    for seg in (business_segments or [])[:limit]:
        if not isinstance(seg, dict):
            continue
        name = seg.get("item_name") or ""
        income = seg.get("income") or ""
        ratio = seg.get("income_ratio") or ""
        parts = [name]
        if income:
            parts.append(f"收入{income}")
        if ratio:
            parts.append(f"占比{ratio}")
        if len(parts) > 1:
            rows.append("、".join(parts))
    return "；".join(rows)


def _metric_context(key_metrics: Dict[str, Any] | None, years: List[str] | None) -> str:
    """拼装结构化关键指标，作为归因对照（防止 LLM 编造与之冲突的数字）。"""
    metrics = key_metrics or {}
    years = years or []
    parts: List[str] = []
    for key in ("revenue", "revenue_growth", "gross_margin", "net_margin", "net_profit", "deducted_net_profit", "debt_ratio", "operating_cash_flow"):
        value = metrics.get(key)
        if value and value != "数据不可用":
            parts.append(f"{key}={value}")
    if years:
        parts.append(f"年度={','.join(years)}")
    return "；".join(parts)


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #
def _build_prompt(
    enterprise_name: str,
    business_review: str,
    key_metrics: Dict[str, Any] | None,
    key_metric_series: Dict[str, Dict[str, str]] | None,
    business_segments: List[Dict[str, Any]] | None,
    risk_section: str | None = None,
) -> str:
    # 经营讨论正文截到 8000 字（与 extractor 上限对齐），保证归因依据完整。
    review_text = (business_review or "").strip()[:8000]
    # 风险因素章节（来自巨潮年报 PDF「公司面临的风险和应对措施」）截到 4000 字，
    # 作为 forward_risks 的权威抽取来源。
    risk_text = (risk_section or "").strip()[:4000]
    metric_context = _metric_context(key_metrics, None)
    series_lines = json.dumps(key_metric_series or {}, ensure_ascii=False)
    segment_lines = _segment_summary(business_segments) or "[无]"

    template = load_prompt_template("annual_report_attribution")
    variables = {
        "enterprise_name": enterprise_name,
        "metric_context": metric_context,
        "series_lines": series_lines,
        "segment_lines": segment_lines,
        "review_text": review_text,
        "risk_section_text": risk_text,
        "banned_terms": ", ".join(BANNED_TERMS),
    }
    return render_prompt_template(template, variables).strip()


# --------------------------------------------------------------------------- #
# JSON 解析与归一化
# --------------------------------------------------------------------------- #
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


def _sanitize_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    for term in BANNED_TERMS:
        text = text.replace(term, "")
    return text[:limit]


def _normalize_driver(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    factor = _sanitize_text(raw.get("factor"), 80)
    evidence = _sanitize_text(raw.get("evidence") or raw.get("quote"), 160)
    direction = str(raw.get("direction") or "").strip().lower()
    if direction not in {"positive", "negative", "neutral"}:
        direction = "neutral"
    if not factor:
        return {}
    return {"factor": factor, "evidence": evidence, "direction": direction}


def _normalize_drivers(raw: Any, limit: int = 5) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    drivers: List[Dict[str, str]] = []
    for item in raw[:limit * 2]:
        normalized = _normalize_driver(item)
        if normalized and normalized not in drivers:
            drivers.append(normalized)
        if len(drivers) >= limit:
            break
    return drivers


def _normalize(parsed: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    return {
        "revenue_drivers": _normalize_drivers(parsed.get("revenue_drivers")),
        "margin_drivers": _normalize_drivers(parsed.get("margin_drivers")),
        "profit_drivers": _normalize_drivers(parsed.get("profit_drivers")),
        "capacity_status": _sanitize_text(parsed.get("capacity_status"), 200),
        "industry_context": _sanitize_text(parsed.get("industry_context"), 400),
        "company_strategy": _sanitize_text(parsed.get("company_strategy"), 400),
        "forward_risks": [
            {"factor": _sanitize_text(item.get("factor"), 80), "evidence": _sanitize_text(item.get("evidence"), 160)}
            for item in (parsed.get("forward_risks") or [])
            if isinstance(item, dict) and _sanitize_text(item.get("factor"), 80)
        ][:5],
        "data_boundary": _sanitize_text(parsed.get("data_boundary"), 300) or "基于年报经营情况讨论与分析章节",
    }


# --------------------------------------------------------------------------- #
# 质量闸门
# --------------------------------------------------------------------------- #
def _quality_warnings(attribution: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    joined = json.dumps(attribution, ensure_ascii=False)
    for term in BANNED_TERMS:
        if term in joined:
            warnings.append(f"归因输出包含禁用表达：{term}")
    total_drivers = (
        len(attribution.get("revenue_drivers") or [])
        + len(attribution.get("margin_drivers") or [])
        + len(attribution.get("profit_drivers") or [])
    )
    if total_drivers == 0 and not attribution.get("industry_context"):
        warnings.append("归因抽取为空：未提取到任何 driver 或行业判断")
    for field in ("revenue_drivers", "margin_drivers", "profit_drivers"):
        for index, driver in enumerate(attribution.get(field) or [], 1):
            if not driver.get("evidence"):
                warnings.append(f"{field} 第{index}项缺少 evidence（年报原文引用）")
    # 行业数字必须来自结构化指标而非 LLM 编造——这里只做表层提示，数字校验由下游叙述器负责。
    industry_number_pattern = re.findall(r"行业(?:中位数|均值|平均|同业)[^，。；]*?(\d+(?:\.\d+)?)", joined)
    if industry_number_pattern:
        warnings.append(f"归因输出疑似编造行业基准数字：{industry_number_pattern[:3]}")
    # 完整性软告警：profit_drivers / capacity_status / forward_risks 是归因深度的核心。
    # 以 [soft] 前缀标记，不阻断报告生成，但供竞速择优时优先选择更完整的候选。
    missing = [
        name for name, val in (
            ("profit_drivers", attribution.get("profit_drivers")),
            ("capacity_status", attribution.get("capacity_status")),
            ("forward_risks", attribution.get("forward_risks")),
        )
        if not (val if isinstance(val, list) else str(val or "").strip())
    ]
    if missing and (attribution.get("revenue_drivers") or attribution.get("margin_drivers")):
        warnings.append(f"[soft] 归因不完整：缺失 {'/'.join(missing)}")
    return warnings[:6]


# --------------------------------------------------------------------------- #
# 竞速
# --------------------------------------------------------------------------- #
def _invoke_one(
    model_id: str,
    llm: ChatOpenAI,
    prompt: str,
    session_id: str | None,
    task_id: str | None,
) -> Dict[str, Any]:
    started_at = time.monotonic()
    response = cached_invoke(llm, prompt, session_id=session_id, task_id=task_id)
    return {
        "model_id": model_id,
        "raw_response": str(getattr(response, "content", response)),
        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
        "response_metadata": getattr(response, "response_metadata", {}) or {},
    }


def _race(
    prompt: str,
    session_id: str | None,
    task_id: str | None,
) -> Dict[str, Any]:
    pool = get_analysis_llm_pool()
    if not pool:
        raise RuntimeError("分析诊断 LLM 池为空，无法进行归因抽取")
    futures: Dict[Future, str] = {
        _LLM_EXECUTOR.submit(_invoke_one, model_id, llm, prompt, session_id, task_id): model_id
        for model_id, llm in pool
    }
    deadline = time.monotonic() + LLM_ATTRIBUTION_TIMEOUT_SECONDS
    errors: List[str] = []
    best_candidate: Dict[str, Any] | None = None
    best_score = None

    def _score(result: Dict[str, Any]):
        attr = result.get("attribution") or {}
        warnings = result.get("quality_warnings") or []
        # [soft] 前缀为完整性软告警，其余为硬告警（禁用词/缺证据/编造数字/空抽取）。
        hard = sum(1 for w in warnings if not w.startswith("[soft]"))
        soft = sum(1 for w in warnings if w.startswith("[soft]"))
        filled = (
            len(attr.get("revenue_drivers") or [])
            + len(attr.get("margin_drivers") or [])
            + len(attr.get("profit_drivers") or [])
            + len(attr.get("forward_risks") or [])
            + (1 if attr.get("capacity_status") else 0)
            + (1 if attr.get("industry_context") else 0)
            + (1 if attr.get("company_strategy") else 0)
        )
        # 优先级：硬告警少 > 软告警少 > 填充字段多（取负填充以便升序比较）。
        return (hard, soft, -filled)

    while futures:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        done, _ = wait(futures.keys(), timeout=remaining, return_when=FIRST_COMPLETED)
        if not done:
            break
        for future in done:
            model_id = futures.pop(future)
            try:
                result = future.result()
            except Exception as exc:
                errors.append(f"{model_id}失败：{type(exc).__name__}")
                continue
            parsed = _extract_json(result.get("raw_response") or "")
            attribution = _normalize(parsed)
            if not attribution:
                errors.append(f"{model_id}返回空或不可解析JSON")
                continue
            warnings = _quality_warnings(attribution)
            result["attribution"] = attribution
            result["quality_warnings"] = warnings
            # 完全干净（零硬零软）立即返回，兼顾深度与延迟。
            if not warnings:
                for pending in futures:
                    pending.cancel()
                result["race_errors"] = errors
                return result
            score = _score(result)
            if best_score is None or score < best_score:
                best_score = score
                best_candidate = result
            errors.append(f"{model_id}未通过质量闸门：{'；'.join(warnings[:2])}")
    for pending in futures:
        pending.cancel()
    if best_candidate is not None:
        best_candidate["race_errors"] = errors
        return best_candidate
    raise TimeoutError("；".join(errors) or f"归因抽取超过{LLM_ATTRIBUTION_TIMEOUT_SECONDS}秒未返回")


# --------------------------------------------------------------------------- #
# 对外入口
# --------------------------------------------------------------------------- #
def extract_annual_report_attribution(
    enterprise_name: str,
    business_review: str | None,
    key_metrics: Dict[str, Any] | None = None,
    key_metric_series: Dict[str, Dict[str, str]] | None = None,
    business_segments: List[Dict[str, Any]] | None = None,
    risk_section: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    """从年报经营讨论章节抽取深度归因。

    若提供 ``risk_section``（巨潮年报 PDF「公司面临的风险和应对措施」章节），
    将作为 ``forward_risks`` 的权威抽取来源，显著丰富前瞻风险维度。

    返回结构见 ``EMPTY_ATTRIBUTION``；当无年报正文、池为空或 LLM 失败时，
    返回 ``source="fallback"`` 的空结构，**绝不抛异常、绝不阻塞报告生成**。
    """
    if not _has_substantive_review(business_review):
        return dict(EMPTY_ATTRIBUTION)

    prompt = _build_prompt(
        enterprise_name,
        business_review or "",
        key_metrics,
        key_metric_series,
        business_segments,
        risk_section=risk_section,
    )
    started_at = time.monotonic()
    try:
        candidate = _race(prompt, session_id=session_id, task_id=task_id)
        attribution = candidate.get("attribution") or dict(EMPTY_ATTRIBUTION)
        attribution["source"] = "llm"
        attribution["model_id"] = candidate.get("model_id")
        attribution["quality_warnings"] = candidate.get("quality_warnings") or []
        attribution["llm_elapsed_ms"] = round((time.monotonic() - started_at) * 1000)
        attribution["race_errors"] = candidate.get("race_errors") or []
        return attribution
    except Exception as exc:
        logger.warning("归因抽取失败，回退空结构：%s", exc)
        result = dict(EMPTY_ATTRIBUTION)
        result["llm_elapsed_ms"] = round((time.monotonic() - started_at) * 1000)
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


# --------------------------------------------------------------------------- #
# 供叙述器使用的便捷渲染（避免下游重复拼装）
# --------------------------------------------------------------------------- #
def render_margin_attribution(attribution: Dict[str, Any] | None) -> str:
    """把毛利归因渲染为可嵌入报告的来源标注句（带年报原文引用）。"""
    attribution = attribution or {}
    drivers = attribution.get("margin_drivers") or []
    if not drivers:
        return ""
    capacity = attribution.get("capacity_status") or ""
    industry = attribution.get("industry_context") or ""
    parts: List[str] = []
    for driver in drivers[:3]:
        factor = driver.get("factor") or ""
        evidence = driver.get("evidence") or ""
        if factor:
            sentence = f"年报管理层指出{factor}"
            if evidence:
                sentence += f"（原文：「{evidence}」）"
            parts.append(sentence + "。")
    if capacity:
        parts.append(f"产能方面，{capacity}。")
    if industry and industry not in " ".join(parts):
        parts.append(f"行业层面，{industry}。")
    if not parts:
        return ""
    return " ".join(parts) + "（来源：年报经营情况讨论与分析章节）"


def render_revenue_attribution(attribution: Dict[str, Any] | None) -> str:
    """把营收归因渲染为可嵌入报告的来源标注句。"""
    attribution = attribution or {}
    drivers = attribution.get("revenue_drivers") or []
    if not drivers:
        return ""
    parts: List[str] = []
    for driver in drivers[:3]:
        factor = driver.get("factor") or ""
        evidence = driver.get("evidence") or ""
        if factor:
            sentence = f"年报披露{factor}"
            if evidence:
                sentence += f"（原文：「{evidence}」）"
            parts.append(sentence + "。")
    if not parts:
        return ""
    return " ".join(parts) + "（来源：年报经营情况讨论与分析章节）"
