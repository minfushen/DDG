"""LLM-assisted business registry narrative writer.

Turns structured business-registration fields into customer-manager style
risk prose, with deterministic template fallback when the LLM fails or
produces low-quality output.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, wait
from typing import Any, Dict, List, Set

from app.config.llm_config import cached_invoke, get_llm
from app.config import settings
from app.config.prompt_loader import load_prompt_template, render_prompt_template

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = max(30, settings.LLM_TIMEOUT_SECONDS)
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="business-narrative")


def _value(basic_info: Dict[str, Dict[str, Any]], field: str) -> str:
    return str(basic_info.get(field, {}).get("value", "") or "").strip()


def _build_business_narrative(
    basic_info: Dict[str, Dict[str, Any]],
    risk_summary: List[str],
    generated_from: str,
) -> List[str]:
    """Generate heuristic deep-analysis paragraphs for business registry data.

    This is the deterministic fallback used when the LLM is unavailable or its
    output fails quality checks.
    """
    paragraphs: List[str] = []

    name = _value(basic_info, "企业名称") or _value(basic_info, "股票简称")
    credit_code = _value(basic_info, "统一社会信用代码")
    legal_person = _value(basic_info, "法定代表人")
    capital = _value(basic_info, "注册资本")
    founded = _value(basic_info, "成立日期")
    status = _value(basic_info, "经营状态") or _value(basic_info, "企业类型")
    address = _value(basic_info, "注册地址")
    scope = _value(basic_info, "经营范围")
    controller = _value(basic_info, "控股股东/实际控制人")
    stock_code = _value(basic_info, "股票代码")

    # 1. 主体画像
    entity = name if name else "该企业"
    parts = [f"{entity}为"]
    if founded:
        parts.append(f"成立于 {founded} 的")
    if status:
        parts.append(f"{status}主体")
    else:
        parts.append("工商登记主体")
    if capital:
        parts.append(f"，注册资本 {capital}")
    if credit_code:
        parts.append(f"，统一社会信用代码 {credit_code}")
    if stock_code:
        parts.append(f"，A股证券代码 {stock_code}")
    parts.append("。")
    if address:
        parts.append(f"注册地址位于 {address}。")
    paragraphs.append("".join(parts))

    # 2. 治理结构
    governance_parts = []
    if legal_person:
        governance_parts.append(f"法定代表人为 {legal_person}")
    if controller:
        governance_parts.append(f"控股股东/实际控制人为 {controller}")
    if governance_parts:
        paragraphs.append(
            "治理结构方面，" + "，".join(governance_parts) + "。"
            "建议结合股权穿透图、一致行动协议及实际控制人征信/涉诉情况，评估治理集中度和关联交易风险。"
        )
    else:
        paragraphs.append(
            "治理结构方面，当前未稳定识别法定代表人或实际控制人信息，建议通过工商登记档案、年报和权威企业数据 API 补充股权穿透资料，"
            "以判断是否存在隐名控制、股权代持或实际控制人风险传导。"
        )

    # 3. 经营范围与业务边界
    if scope:
        paragraphs.append(
            f"经营范围覆盖 {scope[:160]}{'……' if len(scope) > 160 else ''}。"
            "授信审核时应将经营范围与主营业务收入、主要客户/供应商、行业分类进行交叉验证，"
            "识别是否存在超范围经营、主营业务下滑或依赖单一业务线的风险。"
        )
    else:
        paragraphs.append(
            "经营范围字段缺失，无法直接判断业务边界。建议补充营业执照、公司章程或年报中的主营构成描述，"
            "作为行业定位和现金流稳定性判断的基础。"
        )

    # 4. 数据可信度与缺口
    high_conf_fields = [f for f, v in basic_info.items() if v.get("trust_level") in {"high", "medium"}]
    if high_conf_fields:
        paragraphs.append(
            f"数据来源为 {generated_from}，其中 {len(high_conf_fields)} 个字段（{'、'.join(high_conf_fields[:6])}）"
            f"具备中/高可信度，可作为初审参考；"
            f"其余字段置信度较低，需以国家企业信用信息公示系统、工商登记档案等权威源复核。"
        )
    else:
        paragraphs.append(
            f"数据来源为 {generated_from}，但本次检索未命中高/中可信度来源，当前工商结论仅可作为辅助线索。"
            f"授信前应将工商登记、股权穿透、异常经营和行政处罚核验作为前置条件。"
        )

    # 5. 风险提示与授信建议
    if risk_summary:
        paragraphs.append("风险提示：" + "；".join(risk_summary[:3]))
    paragraphs.append(
        "授信关注建议：优先核对企业主体存续状态、注册资本实缴/认缴情况、法定代表人及实际控制人信用状况；"
        "其次关注经营范围与主营业务匹配度、对外投资/关联交易、股权质押和经营异常记录。"
    )

    return paragraphs


def _allowed_numbers(basic_info: Dict[str, Dict[str, Any]]) -> Set[str]:
    allowed: Set[str] = set()
    for item in basic_info.values():
        value = str(item.get("value", "") or "")
        for number in re.findall(r"\d+(?:\.\d+)?", value):
            allowed.add(number)
    return allowed


def _prompt(enterprise_name: str, basic_info: Dict[str, Dict[str, Any]], risk_summary: List[str], generated_from: str) -> str:
    # Flatten fields for the prompt while preserving provenance.
    fields: Dict[str, Any] = {}
    for field, item in basic_info.items():
        fields[field] = {
            "value": str(item.get("value", "") or ""),
            "trust_level": str(item.get("trust_level", "unknown") or "unknown"),
            "source": str(item.get("source_name", "未知") or "未知"),
        }
    allowed = sorted(_allowed_numbers(basic_info))
    risk_text = "；".join(risk_summary[:4]) if risk_summary else "暂无明确风险提示"
    template = load_prompt_template("business_narrative")
    variables = {
        "enterprise_name": enterprise_name,
        "generated_from": generated_from,
        "fields_json": json.dumps(fields, ensure_ascii=False),
        "risk_text": risk_text,
        "allowed_numbers": ", ".join(allowed) if allowed else "无",
    }
    return render_prompt_template(template, variables).strip()


def _get_llm() -> BaseChatModel:
    return get_llm(
        temperature=0,
        max_tokens=2048,
        timeout=_TIMEOUT_SECONDS,
        max_retries=1,
        response_format="json_object",
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


def _quality_warnings(
    summary: List[str],
    basic_info: Dict[str, Dict[str, Any]],
) -> List[str]:
    warnings: List[str] = []
    if not 4 <= len(summary) <= 6:
        warnings.append(f"LLM输出段落数量为{len(summary)}，不符合4-6段要求")

    allowed = _allowed_numbers(basic_info)
    joined = "\n".join(summary)
    for number in re.findall(r"\d+(?:\.\d+)?", joined):
        if number not in allowed and number not in {"1", "2", "3", "4", "5", "6", "12"}:
            warnings.append(f"LLM输出包含未提供的数字：{number}")

    if not any(keyword in joined for keyword in ["复核", "核验", "数据边界", "需补充", "建议"]):
        warnings.append("LLM输出缺少数据边界或人工复核提示")

    return warnings[:5]


def _invoke_llm(prompt: str) -> Dict[str, Any]:
    started_at = time.monotonic()
    response = cached_invoke(_get_llm(), prompt)
    return {
        "raw_response": str(getattr(response, "content", response)),
        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
    }


def build_business_narrative_with_llm(
    enterprise_name: str,
    basic_info: Dict[str, Dict[str, Any]],
    risk_summary: List[str],
    generated_from: str,
) -> Dict[str, Any]:
    """Build business deep narrative with LLM and deterministic fallback.

    Returns a dict with keys: success, source, narrative_summary, quality_warnings,
    llm_elapsed_ms.
    """
    fallback = _build_business_narrative(basic_info, risk_summary, generated_from)

    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        return {
            "success": True,
            "source": "fallback",
            "narrative_summary": fallback,
            "quality_warnings": ["LLM未配置，使用模板化分析"],
            "llm_elapsed_ms": 0,
        }

    prompt = _prompt(enterprise_name, basic_info, risk_summary, generated_from)
    future: Future = _LLM_EXECUTOR.submit(_invoke_llm, prompt)
    started_at = time.monotonic()
    try:
        result = future.result(timeout=_TIMEOUT_SECONDS)
    except TimeoutError:
        future.cancel()
        return {
            "success": False,
            "source": "fallback",
            "narrative_summary": fallback,
            "quality_warnings": [f"LLM工商叙述超过{_TIMEOUT_SECONDS}秒未返回"],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }
    except Exception as exc:
        return {
            "success": False,
            "source": "fallback",
            "narrative_summary": fallback,
            "quality_warnings": [f"LLM工商叙述调用失败：{type(exc).__name__}"],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }

    parsed = _extract_json(result.get("raw_response", ""))
    summary = _normalize_summary(parsed.get("narrative_summary"))
    warnings = _quality_warnings(summary, basic_info)

    if warnings or not summary:
        return {
            "success": False,
            "source": "fallback",
            "narrative_summary": fallback,
            "quality_warnings": warnings or ["LLM输出未通过质量检查"],
            "llm_elapsed_ms": result.get("elapsed_ms", 0),
        }

    return {
        "success": True,
        "source": "llm",
        "narrative_summary": summary,
        "quality_warnings": warnings,
        "llm_elapsed_ms": result.get("elapsed_ms", 0),
    }
