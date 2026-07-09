"""LLM adjudicator for industry classification candidates.

Rule matching is good at recalling possible national-industry-code rows, but it
is brittle when a business scope contains generic tail phrases such as import
and export. This module lets a lightweight OpenAI-compatible model make the
final semantic choice from a bounded candidate set.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List
import json
import re
import time

from app.config.llm_config import get_llm
from app.config import settings


@lru_cache()
def _get_industry_llm() -> BaseChatModel | None:
    """Prefer the fast backup model already configured by the project."""
    api_key = settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY or settings.LLM_API_KEY
    base_url = settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL or settings.LLM_BASE_URL
    model = settings.FINANCIAL_NARRATIVE_BACKUP_LLM_MODEL or settings.LLM_MODEL
    if not api_key or not base_url or not model:
        return None
    return get_llm(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_tokens=900,
        timeout=settings.INDUSTRY_CLASSIFICATION_LLM_TIMEOUT_SECONDS,
        max_retries=0,
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
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def _shorten(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _prompt(
    enterprise_name: str,
    business_scope: str,
    extra_context: str,
    candidates: List[Dict[str, Any]],
) -> str:
    candidate_payload = [
        {
            "code": item.get("code"),
            "name": item.get("name"),
            "path": " > ".join(item.get("path") or []),
            "score": item.get("score"),
            "signals": item.get("signals") or [],
        }
        for item in candidates[:12]
    ]
    return f"""
你是银行贷前尽调系统中的行业分类裁判。请根据企业名称、经营范围、上市公司公开资料和候选行业，选择最能代表目标公司主营业务的行业。

关键原则：
1. 上市公司年报经营讨论、主营业务、主营构成、资本市场行业标签优先于工商经营范围尾句。
2. “货物进出口、技术进出口、进出口代理、贸易、批发、零售”等如果只是经营范围中的通用许可或尾句，不得作为主营行业。
3. 必须且只能从候选行业列表中选择 selected_code，不要创造行业代码。
4. 如果候选列表没有足以代表主营业务的行业，返回 decision="no_decision"。
5. 只输出 JSON，不要输出解释性前后缀。

企业名称：{enterprise_name}
经营范围：{_shorten(business_scope, 1000)}
公开资料上下文：{_shorten(extra_context, 3000)}
候选行业：{json.dumps(candidate_payload, ensure_ascii=False)}

JSON 格式：
{{
  "decision": "selected" 或 "no_decision",
  "selected_code": "候选行业代码",
  "selected_name": "候选行业名称",
  "semantic_industry_id": "technology/manufacturing/semiconductor/new_energy/construction/trade_import_export/retail/logistics/biopharma/real_estate/energy/agriculture/education/hotel_tourism/internet_saas 之一或空",
  "semantic_industry_name": "面向客户经理可读的行业名称",
  "confidence": 0.0到0.99,
  "reason": "一句话说明为什么这是主营行业",
  "ignored_noise": ["被忽略的通用经营范围噪声"]
}}
""".strip()


def adjudicate_industry_with_llm(
    enterprise_name: str,
    business_scope: str,
    extra_context: str,
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return an LLM-selected candidate code, or a failure payload."""
    llm = _get_industry_llm()
    if llm is None:
        return {"success": False, "error": "未配置可用行业分类 LLM"}
    if not candidates:
        return {"success": False, "error": "候选行业为空"}

    valid_codes = {str(item.get("code")) for item in candidates if item.get("code")}
    started_at = time.monotonic()
    try:
        response = llm.invoke(_prompt(enterprise_name, business_scope, extra_context, candidates))
        raw = str(getattr(response, "content", response))
        parsed = _extract_json(raw)
    except Exception as exc:
        return {
            "success": False,
            "error": f"行业分类 LLM 调用失败：{type(exc).__name__}",
            "elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }

    selected_code = str(parsed.get("selected_code") or "").strip()
    if parsed.get("decision") != "selected" or selected_code not in valid_codes:
        return {
            "success": False,
            "error": "LLM 未选择有效候选行业",
            "raw_response": raw[:1000],
            "elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "success": True,
        "selected_code": selected_code,
        "selected_name": parsed.get("selected_name") or "",
        "semantic_industry_id": parsed.get("semantic_industry_id") or "",
        "semantic_industry_name": parsed.get("semantic_industry_name") or "",
        "confidence": max(0.0, min(confidence, 0.99)),
        "reason": parsed.get("reason") or "",
        "ignored_noise": parsed.get("ignored_noise") if isinstance(parsed.get("ignored_noise"), list) else [],
        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
    }
