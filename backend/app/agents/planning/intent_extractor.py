"""LLM-backed + rule user input extraction for multi-intent task creation.

升级点（相较早期单意图版本）：
- 多意图：单个用户输入可映射到多个研究类别（财务/行业/司法/工商/关联/舆情/授信），
  输出 ``intents`` 列表，下游 planner 据此裁剪研究任务而非让 LLM planner 再猜。
- 槽位（slot）：抽取报告深度、时间窗口、对比基准、行业细分、授信假设、是否含现场材料、
  输出格式等结构化参数，统一经 ``SLOT_SCHEMA`` 校验并回填默认值。
- 歧义澄清：企业名称缺失或置信度过低时返回 ``needs_clarification=True`` + ``clarification_prompt``，
  而非硬猜。

向后兼容：仍输出 ``task_type`` / ``target_agent`` / ``enterprise_name`` / ``stock_code`` /
``confidence``，旧调用方不受影响。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Literal, Optional

TaskType = Literal["full", "single"]
TargetAgent = Literal["business", "financial", "legal", "industry", "relationship", "sentiment", "credit"]

# 与 research_engine/prompts.ALLOWED_RESEARCH_CATEGORIES 保持一致（去掉 general）
RESEARCH_CATEGORIES = ["business", "financial", "legal", "industry", "relationship", "sentiment", "credit"]


# ─── 槽位 schema ────────────────────────────────────────────────────────────
SLOT_SCHEMA: Dict[str, Dict[str, Any]] = {
    "depth": {"type": "enum", "enum": ["quick", "standard", "full"], "default": "full",
              "description": "报告深度：quick=简版速览，standard=标准，full=完整尽调"},
    "time_window": {"type": "enum", "enum": ["latest", "近一年", "近三年", "近五年"], "default": "近三年",
                    "description": "财务/经营分析时间窗口"},
    "comparison": {"type": "enum", "enum": ["none", "peer", "self"], "default": "self",
                   "description": "对比基准：none=不对比，peer=同业对比，self=自身同比/环比"},
    "industry_segment": {"type": "str", "default": None, "description": "行业细分（如半导体/白酒/新能源）"},
    "credit_assumptions": {"type": "str", "default": None, "description": "授信假设：拟申请额度/期限/品种"},
    "has_on_site_materials": {"type": "bool", "default": False, "description": "是否含客户经理现场收集材料"},
    "output_format": {"type": "enum", "enum": ["report", "brief", "slides"], "default": "report",
                      "description": "输出格式：report=正式报告，brief=简报，slides=演示"},
}
VALID_SLOT_KEYS = set(SLOT_SCHEMA.keys())


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

# 命中即视为"完整尽调"（不裁剪类别）
FULL_TASK_WORDS = ["完整", "全面", "全方位", "整体", "综合", "贷前尽调", "尽调报告", "全套", "整体尽调", "全量"]

# 多类别关键词映射（覆盖七类研究维度）
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "business": ["工商", "股东", "注册", "法人", "高管", "经营范围", "变更", "对外投资", "股权结构", "治理", "董监高", "实控人"],
    "financial": ["财务", "盈利", "现金流", "偿债", "资产负债", "营收", "利润", "毛利率", "roe", "流动比率", "速动比率", "业绩", "偿债压力"],
    "legal": ["司法", "法律", "诉讼", "裁判", "失信", "处罚", "被执行", "立案", "合规", "监管问询"],
    "industry": ["行业风险", "行业情况", "行业分析", "所属行业", "产业", "竞争", "市场", "政策", "景气", "格局", "赛道", "产业链", "上下游"],
    "relationship": ["关联", "担保", "股权质押", "质押", "供应链", "关联交易", "穿透", "担保圈", "对外担保", "关联网络"],
    "sentiment": ["舆情", "负面", "声誉", "处罚", "投诉", "批评", "监管处罚", "新闻", "口碑", "声誉风险"],
    "credit": ["授信", "额度", "信贷", "贷款", "融资", "敞口", "准入", "贷前", "授信方案"],
}

# 行业细分轻量词典（仅做提示性抽取，缺省由 LLM/人工补全）
_SEGMENT_MAP = {
    "半导体": "半导体", "芯片": "半导体", "集成电路": "半导体", "晶圆": "半导体",
    "白酒": "白酒", "啤酒": "白酒", "酒类": "白酒",
    "新能源": "新能源", "锂电": "新能源", "锂电池": "新能源", "光伏": "新能源",
    "医药": "医药", "医疗": "医药", "生物制药": "医药",
    "房地产": "房地产", "地产": "房地产", "物业": "房地产",
    "银行": "银行", "保险": "保险", "券商": "证券",
    "汽车": "汽车", "整车": "汽车", "零部件": "汽车",
    "互联网": "互联网", "电商": "互联网", "游戏": "互联网",
}


def _fast_normalize_enterprise_name(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return normalized
    normalized = re.sub(r"（.*?）|\(.*?\)", "", normalized).strip()
    for word in FAST_TASK_WORDS:
        normalized = normalized.replace(word, "")
    normalized = re.sub(r"[，,。.!！?？：:\s]+", "", normalized).strip()
    return normalized or (text or "").strip()


# 指代性/占位性名称，无法作为有效主体，应触发澄清
_GENERIC_NAME_HINTS = ["这家", "这个", "该公司", "某某", "测试公司", "xxx", "xx公司", "某企业", "某公司", "那家"]


def _is_generic_name(name: str) -> bool:
    n = (name or "").strip()
    if not n:
        return True
    if len(n) <= 1:
        return True
    return any(hint in n for hint in _GENERIC_NAME_HINTS)


def _detect_categories(text: str) -> List[str]:
    """从用户输入抽取命中的研究类别。空列表表示完整尽调（不裁剪）。"""
    if any(word in (text or "") for word in FULL_TASK_WORDS):
        return []
    lowered = (text or "").lower()
    hits: List[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            hits.append(category)
    return hits


def _extract_slots(text: str) -> Dict[str, Any]:
    """规则抽取槽位（仅抽取有信号的字段，缺失由 validate_slots 补默认）。"""
    t = text or ""
    slots: Dict[str, Any] = {}

    if any(w in t for w in ["简版", "速览", "快速", "极简"]):
        slots["depth"] = "quick"
    elif any(w in t for w in ["标准版", "标准尽调", "标准"]):
        slots["depth"] = "standard"

    if any(w in t for w in ["近一年", "最近一年", "过去一年", "近1年"]):
        slots["time_window"] = "近一年"
    elif any(w in t for w in ["近三年", "近3年", "过去三年"]):
        slots["time_window"] = "近三年"
    elif any(w in t for w in ["近五年", "近5年", "过去五年"]):
        slots["time_window"] = "近五年"
    elif any(w in t for w in ["最新一期", "最新", "当期", "本期"]):
        slots["time_window"] = "latest"

    if any(w in t for w in ["同业", "同行", "竞品", "对标", "对比同"]):
        slots["comparison"] = "peer"
    elif any(w in t for w in ["自身", "同比", "环比", "纵向"]):
        slots["comparison"] = "self"
    elif any(w in t for w in ["不对比", "无需对比", "不用对比"]):
        slots["comparison"] = "none"

    for keyword, segment in _SEGMENT_MAP.items():
        if keyword in t:
            slots["industry_segment"] = segment
            break

    m_amt = re.search(r"(\d+\.?\d*)\s*(万|亿|w|万元|亿元)?\s*(额度|贷款|授信|融资|敞口)", t)
    m_term = re.search(r"期限\s*(\d+)\s*(年|个月|月|周)", t)
    parts: List[str] = []
    if m_amt:
        amt = m_amt.group(1) + (m_amt.group(2) or "")
        parts.append(f"拟申请{amt}{m_amt.group(3)}")
    if m_term:
        parts.append(f"期限{m_term.group(1)}{m_term.group(2)}")
    if parts:
        slots["credit_assumptions"] = "，".join(parts)

    if any(w in t for w in ["现场材料", "尽调底稿", "客户经理提供", "客户提供", "底稿", "现场尽调材料"]):
        slots["has_on_site_materials"] = True

    if any(w in t for w in ["简报", "速览", "摘要版"]):
        slots["output_format"] = "brief"
    elif any(w in t.lower() for w in ["ppt", "slides", "演示文稿", "演示"]):
        slots["output_format"] = "slides"
    return slots


def validate_slots(slots: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], List[str]]:
    """校验并补全槽位：筛除未知键、枚举约束、缺失补默认。返回 (clean, issues)。"""
    clean: Dict[str, Any] = {}
    issues: List[str] = []
    raw = slots if isinstance(slots, dict) else {}
    for name, spec in SLOT_SCHEMA.items():
        val = raw.get(name, None)
        if val is None:
            clean[name] = spec["default"]
            continue
        if name not in VALID_SLOT_KEYS:
            issues.append(f"未知槽位 {name}，已忽略")
            continue
        if spec.get("type") == "enum":
            if val not in spec["enum"]:
                issues.append(f"槽位 {name}={val!r} 不在枚举 {spec['enum']}，使用默认 {spec['default']!r}")
                clean[name] = spec["default"]
            else:
                clean[name] = val
        elif spec.get("type") == "bool":
            clean[name] = bool(val)
        else:
            clean[name] = val
    return clean, issues


# 单类别关键词（保留用于历史兜底/单意图推断）
_SINGLE_KEYWORD_MAP: Dict[TargetAgent, List[str]] = {c: kws for c, kws in CATEGORY_KEYWORDS.items()}  # type: ignore


def _fallback_target(text: str) -> Optional[TargetAgent]:
    lowered = text.lower()
    for agent, keywords in _SINGLE_KEYWORD_MAP.items():
        if any(keyword in lowered for keyword in keywords):
            return agent
    return None


_GOAL_FOR: Dict[str, str] = {
    "business": "确认企业主体、工商登记、股权治理与异常事项。",
    "financial": "分析近三年财务趋势、盈利质量、现金流与偿债能力。",
    "legal": "核查诉讼、执行、失信、处罚与监管问询等司法合规事项。",
    "industry": "判断行业周期、竞争格局与上下游经营环境。",
    "relationship": "呈现股权结构、对外担保/质押、关联与供应链位置及关联风险。",
    "sentiment": "监测公开舆情、监管处罚与声誉风险信号。",
    "credit": "形成授信准入边界、前置条件与贷后监控要求。",
}


def _build_intents(categories: List[str], slots: Dict[str, Any]) -> List[Dict[str, Any]]:
    cats = categories if categories else list(RESEARCH_CATEGORIES)
    return [{"category": c, "goal": _GOAL_FOR.get(c, f"核查{c}维度"), "slots": slots} for c in cats]


def _assemble(
    enterprise_name: str,
    stock_code: Optional[str],
    categories: List[str],
    slots: Dict[str, Any],
    confidence: float,
    source: str,
    reason: str,
    ambiguities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    intents = _build_intents(categories, slots)
    task_type = "full" if not categories else "single"
    target_agent = intents[0]["category"] if task_type == "single" else None
    needs = bool(ambiguities)
    return {
        "enterprise_name": enterprise_name,
        "stock_code": stock_code,
        "task_type": task_type,
        "target_agent": target_agent,
        "intents": intents,
        "slots": slots,
        "needs_clarification": needs,
        "clarification_prompt": ("；".join(ambiguities) + " 请补充后重试。") if needs else "",
        "ambiguities": ambiguities or [],
        "confidence": confidence,
        "source": source,
        "reason": reason,
    }


def fallback_extract_user_intent(user_input: str) -> Dict[str, Any]:
    """Rule fallback used only when the LLM extractor is unavailable."""
    from app.agents.tools.listed_company_tool import normalize_enterprise_name, resolve_listed_company

    stock_match = re.search(r"(?<!\d)([036]\d{5})(?!\d)", user_input or "")
    enterprise_name = normalize_enterprise_name(user_input)
    listed = resolve_listed_company(user_input, stock_code=stock_match.group(1) if stock_match else "")
    if listed:
        enterprise_name = listed.get("company_name") or listed.get("security_name") or enterprise_name

    categories = _detect_categories(user_input)
    slots, _ = validate_slots(_extract_slots(user_input))
    ambiguities = ["未识别到明确的企业主体，请确认企业名称（全称或证券简称）"] if _is_generic_name(enterprise_name) else None
    return _assemble(
        enterprise_name,
        stock_match.group(1) if stock_match else (listed or {}).get("stock_code"),
        categories,
        slots,
        0.55,
        "rule_fallback",
        "LLM抽取不可用或返回不完整，使用规则兜底。",
        ambiguities,
    )


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

    categories = _detect_categories(user_input)
    slots, _ = validate_slots(_extract_slots(user_input))
    ambiguities = ["未识别到明确的企业主体，请确认企业名称（全称或证券简称）"] if _is_generic_name(enterprise_name) else None
    confidence = 0.6 if (listed or categories) else 0.5
    return _assemble(
        enterprise_name,
        stock_match.group(1) if stock_match else (listed or {}).get("stock_code"),
        categories,
        slots,
        confidence,
        "fast_rule",
        "创建任务阶段使用纯本地快速规则解析（多意图+槽位），避免入口等待LLM或外部搜索超时。",
        ambiguities,
    )


def _json_from_text(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    parsed = json.loads(text[start:end])
    return parsed if isinstance(parsed, dict) else {}


def _intents_from_llm(parsed: Dict[str, Any], slots: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 LLM JSON 解析 intents；非法类别忽略，空则回退到规则检测。"""
    raw_intents = parsed.get("intents") or []
    if isinstance(raw_intents, list) and raw_intents:
        kept = []
        for it in raw_intents:
            if not isinstance(it, dict):
                continue
            cat = it.get("category")
            if cat in RESEARCH_CATEGORIES:
                kept.append({"category": cat, "goal": str(it.get("goal") or _GOAL_FOR.get(cat, "")), "slots": slots})
        if kept:
            return kept
    # 回退：用规则检测类别
    cats = _detect_categories(str(parsed.get("raw_input") or ""))
    return _build_intents(cats, slots)


def extract_user_intent(user_input: str) -> Dict[str, Any]:
    """Extract enterprise name, multi-intent and slots using the configured LLM."""
    fallback = fallback_extract_user_intent(user_input)
    try:
        from app.config.llm_config import get_llm, cached_invoke
        from app.agents.tools.listed_company_tool import resolve_listed_company

        prompt = f"""你是银行尽调系统的入口意图解析器。请从用户输入中抽取结构化信息，只输出JSON。

用户输入：{user_input}

输出字段：
- enterprise_name: 企业名称、证券简称或公司全称，不要包含任务话术。
- intents: 研究意图列表，每项 {{"category": 类别, "goal": 简短目标}}。类别只能是 {', '.join(RESEARCH_CATEGORIES)}。
  若用户要"完整尽调/全方位/贷前尽调/尽调报告"或同时涉及多维度，列出所有相关类别；
  若只问某一维度（如仅财务、仅舆情），只列该类别。
- slots: 槽位对象，可包含：depth(quick/standard/full)、time_window(latest/近一年/近三年/近五年)、
  comparison(none/peer/self)、industry_segment(如"半导体")、credit_assumptions(如"拟申请5000万授信，期限3年")、
  has_on_site_materials(true/false)、output_format(report/brief/slides)。未提及的槽位不要出现。
- needs_clarification: 当企业名称缺失或明显歧义时为 true，否则 false。
- clarification_prompt: needs_clarification 为 true 时给用户的澄清问题。
- confidence: 0到1。
- reason: 简短说明。

示例：
输入"分析一下卓胜微这家上市公司" => {{"enterprise_name":"卓胜微","intents":[{{"category":"business","goal":"主体与工商"}},{{"category":"financial","goal":"财务"}},{{"category":"legal","goal":"司法"}},{{"category":"industry","goal":"行业"}},{{"category":"relationship","goal":"关联"}},{{"category":"sentiment","goal":"舆情"}},{{"category":"credit","goal":"授信"}}],"slots":{{}},"needs_clarification":false,"confidence":0.95,"reason":"完整尽调"}}
输入"分析一下A公司的财务风险和行业竞争格局" => {{"enterprise_name":"A公司","intents":[{{"category":"financial","goal":"财务风险"}},{{"category":"industry","goal":"行业竞争"}}],"slots":{{"time_window":"近三年"}},"needs_clarification":false,"confidence":0.9,"reason":"多意图：财务+行业"}}
"""
        response = cached_invoke(get_llm(), prompt)
        parsed = _json_from_text(str(getattr(response, "content", response)))
        enterprise_name = str(parsed.get("enterprise_name") or "").strip()
        if not enterprise_name:
            return fallback

        stock_code = parsed.get("stock_code") or fallback.get("stock_code")
        listed = resolve_listed_company(enterprise_name, stock_code=stock_code or "")
        if listed and enterprise_name in {listed.get("security_name"), listed.get("stock_code")}:
            enterprise_name = listed.get("company_name") or enterprise_name

        # 槽位：优先 LLM，缺失用规则补，再统一校验
        llm_slots = parsed.get("slots") or {}
        merged_slots = {**_extract_slots(user_input), **llm_slots}
        slots, _ = validate_slots(merged_slots)

        intents = _intents_from_llm({**parsed, "raw_input": user_input}, slots)

        ambiguities: Optional[List[str]] = None
        if parsed.get("needs_clarification"):
            ambiguities = [str(parsed.get("clarification_prompt") or "企业主体存在歧义，请确认。")]
        elif not enterprise_name:
            ambiguities = ["未识别到企业名称"]

        return _assemble(
            enterprise_name,
            stock_code,
            [it["category"] for it in intents],
            slots,
            float(parsed.get("confidence") or 0.8),
            "llm",
            parsed.get("reason") or "LLM结构化抽取（多意图+槽位）。",
            ambiguities,
        )
    except Exception as exc:
        fallback["error"] = str(exc)
        return fallback
