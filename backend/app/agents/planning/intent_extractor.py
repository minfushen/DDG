"""LLM-backed user input extraction for task creation."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal, Optional

TaskType = Literal["full", "single"]
TargetAgent = Literal["business", "financial", "legal", "industry"]


FAST_LISTED_COMPANY_MAP = {
    "欣旺达": {"stock_code": "300207", "stock_exchange": "SZ", "secu_code": "300207.SZ", "security_name": "欣旺达", "company_name": "欣旺达电子股份有限公司"},
    "欣旺达电子股份有限公司": {"stock_code": "300207", "stock_exchange": "SZ", "secu_code": "300207.SZ", "security_name": "欣旺达", "company_name": "欣旺达电子股份有限公司"},
    "比亚迪": {"stock_code": "002594", "stock_exchange": "SZ", "secu_code": "002594.SZ", "security_name": "比亚迪", "company_name": "比亚迪股份有限公司"},
    "宁德时代": {"stock_code": "300750", "stock_exchange": "SZ", "secu_code": "300750.SZ", "security_name": "宁德时代", "company_name": "宁德时代新能源科技股份有限公司"},
    "贵州茅台": {"stock_code": "600519", "stock_exchange": "SH", "secu_code": "600519.SH", "security_name": "贵州茅台", "company_name": "贵州茅台酒股份有限公司"},
    "士兰微": {"stock_code": "600460", "stock_exchange": "SH", "secu_code": "600460.SH", "security_name": "士兰微", "company_name": "杭州士兰微电子股份有限公司"},
    "杭州士兰微电子股份有限公司": {"stock_code": "600460", "stock_exchange": "SH", "secu_code": "600460.SH", "security_name": "士兰微", "company_name": "杭州士兰微电子股份有限公司"},
    "闻泰科技": {"stock_code": "600745", "stock_exchange": "SH", "secu_code": "600745.SH", "security_name": "*ST闻泰", "company_name": "闻泰科技股份有限公司"},
    "闻泰科技股份有限公司": {"stock_code": "600745", "stock_exchange": "SH", "secu_code": "600745.SH", "security_name": "*ST闻泰", "company_name": "闻泰科技股份有限公司"},
}


FAST_TASK_WORDS = [
    "完成", "帮我", "请", "做一下", "做", "生成", "分析一下", "分析", "查看", "跑", "开展", "进行",
    "完整尽调", "尽调", "贷前", "报告", "这个上市公司", "这家上市公司", "上市公司", "公司", "企业", "的",
]


def _fast_normalize_enterprise_name(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return normalized
    normalized = re.sub(r"（.*?）|\(.*?\)", "", normalized).strip()
    for word in FAST_TASK_WORDS:
        normalized = normalized.replace(word, "")
    normalized = re.sub(r"[，,。.!！?？：:\s]+", "", normalized).strip()
    return normalized or (text or "").strip()


def _fallback_target(text: str) -> Optional[TargetAgent]:
    lowered = text.lower()
    keyword_map: Dict[TargetAgent, list[str]] = {
        "industry": ["行业风险", "行业情况", "行业分析", "所属行业", "产业", "竞争", "市场", "政策", "景气", "格局", "赛道"],
        "financial": ["财务", "盈利", "现金流", "偿债", "资产负债", "营收", "利润", "毛利率", "roe", "流动比率", "速动比率"],
        "legal": ["司法", "法律", "诉讼", "裁判", "失信", "处罚", "被执行", "立案"],
        "business": ["工商", "股东", "注册", "法人", "高管", "经营范围", "变更", "对外投资"],
    }
    for agent, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            return agent
    return None


def fallback_extract_user_intent(user_input: str) -> Dict[str, Any]:
    """Rule fallback used only when the LLM extractor is unavailable."""
    from app.agents.tools.listed_company_tool import normalize_enterprise_name, resolve_listed_company

    stock_match = re.search(r"(?<!\d)([036]\d{5})(?!\d)", user_input or "")
    enterprise_name = normalize_enterprise_name(user_input)
    listed = resolve_listed_company(user_input, stock_code=stock_match.group(1) if stock_match else "")
    if listed:
        enterprise_name = listed.get("company_name") or listed.get("security_name") or enterprise_name

    target = _fallback_target(user_input)
    return {
        "enterprise_name": enterprise_name,
        "task_type": "single" if target else "full",
        "target_agent": target,
        "stock_code": stock_match.group(1) if stock_match else (listed or {}).get("stock_code"),
        "confidence": 0.55,
        "source": "rule_fallback",
        "reason": "LLM抽取不可用或返回不完整，使用规则兜底。",
    }


def fast_extract_user_intent(user_input: str) -> Dict[str, Any]:
    """Fast path for task creation.

    The landing page must return a task id quickly. Do not block task creation
    on a long LLM call; background agents can do slower semantic enrichment.
    """
    stock_match = re.search(r"(?<!\d)([036]\d{5})(?!\d)", user_input or "")
    enterprise_name = _fast_normalize_enterprise_name(user_input)
    listed = None
    if stock_match:
        code = stock_match.group(1)
        listed = next((info for info in FAST_LISTED_COMPANY_MAP.values() if info.get("stock_code") == code), None)
        if not listed:
            exchange = "SH" if code.startswith("6") else "SZ"
            listed = {"stock_code": code, "stock_exchange": exchange, "secu_code": f"{code}.{exchange}", "security_name": enterprise_name}
    else:
        for keyword, info in FAST_LISTED_COMPANY_MAP.items():
            if keyword in enterprise_name or keyword in (user_input or ""):
                listed = info
                break
    if listed:
        enterprise_name = listed.get("company_name") or listed.get("security_name") or enterprise_name

    target = _fallback_target(user_input)
    return {
        "enterprise_name": enterprise_name,
        "task_type": "single" if target else "full",
        "target_agent": target,
        "stock_code": stock_match.group(1) if stock_match else (listed or {}).get("stock_code"),
        "confidence": 0.6 if listed or target else 0.5,
        "source": "fast_rule",
        "reason": "创建任务阶段使用纯本地快速规则解析，避免入口等待LLM或外部搜索超时。",
    }


def _json_from_text(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    parsed = json.loads(text[start:end])
    return parsed if isinstance(parsed, dict) else {}


def extract_user_intent(user_input: str) -> Dict[str, Any]:
    """Extract enterprise name and task intent using the configured LLM."""
    fallback = fallback_extract_user_intent(user_input)
    try:
        from app.config.llm_config import get_llm, cached_invoke

        prompt = f"""你是银行尽调系统的入口意图解析器。请从用户输入中抽取结构化信息，只输出JSON。

用户输入：{user_input}

输出字段：
- enterprise_name: 企业名称、证券简称或公司全称，不要包含“帮我、分析一下、完整尽调、这家上市公司”等任务话术。
- task_type: "full" 或 "single"。完整尽调/全方位尽调/尽调报告为 full；只问财务、工商、司法、行业其中一种为 single。
- target_agent: task_type 为 single 时填 business/financial/legal/industry，否则为 null。
- stock_code: 如果输入中包含股票代码则填6位代码，否则为 null。
- confidence: 0到1。
- reason: 简短说明。

示例：
输入“分析一下卓胜微这家上市公司” => {{"enterprise_name":"卓胜微","task_type":"full","target_agent":null,"stock_code":null,"confidence":0.95,"reason":"用户要求对上市公司做完整尽调"}}
输入“分析一下深圳市欣旺达能源科技有限公司的财务风险情况” => {{"enterprise_name":"深圳市欣旺达能源科技有限公司","task_type":"single","target_agent":"financial","stock_code":null,"confidence":0.95,"reason":"用户只要求财务风险分析"}}
"""
        response = cached_invoke(get_llm(), prompt)
        parsed = _json_from_text(str(getattr(response, "content", response)))
        enterprise_name = str(parsed.get("enterprise_name") or "").strip()
        if not enterprise_name:
            return fallback

        task_type = parsed.get("task_type") if parsed.get("task_type") in {"full", "single"} else fallback["task_type"]
        target_agent = parsed.get("target_agent") if parsed.get("target_agent") in {"business", "financial", "legal", "industry"} else None
        if task_type == "single" and not target_agent:
            target_agent = fallback.get("target_agent")
        if task_type == "full":
            target_agent = None

        stock_code = parsed.get("stock_code") or fallback.get("stock_code")
        listed = resolve_listed_company(enterprise_name, stock_code=stock_code or "")
        if listed and enterprise_name in {listed.get("security_name"), listed.get("stock_code")}:
            enterprise_name = listed.get("company_name") or enterprise_name

        return {
            "enterprise_name": enterprise_name,
            "task_type": task_type,
            "target_agent": target_agent,
            "stock_code": stock_code,
            "confidence": float(parsed.get("confidence") or 0.8),
            "source": "llm",
            "reason": parsed.get("reason") or "LLM结构化抽取。",
        }
    except Exception as exc:
        fallback["error"] = str(exc)
        return fallback
