"""LLM-assisted industry diagnostic writer.

The industry agent already performs deterministic classification, public-info
collection, RAG retrieval, and rule triggering. This module only turns those
bounded inputs into due-diligence style diagnostic prose, with quality gates and
deterministic fallback when the model output is too generic or unavailable.
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, TimeoutError, wait
from functools import lru_cache
from typing import Any, Dict, List
import json
import re
import time

from langchain_openai import ChatOpenAI

from app.config import settings


LLM_INDUSTRY_TIMEOUT_SECONDS = 60
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=3, thread_name_prefix="industry-diagnostic")

BANNED_GENERIC_TERMS = [
    "竞争激烈",
    "政策利好",
    "市场空间广阔",
    "技术更新快",
    "人才重要",
    "估值偏高",
    "发展前景良好",
    "机遇与挑战并存",
]

GENERIC_REWRITES = {
    "竞争激烈": "竞争强度需通过CR5、价格变化、产能利用率和订单覆盖率核验",
    "政策利好": "政策影响需拆分为补贴、准入、出口管制和监管约束后判断",
    "市场空间广阔": "市场空间需以行业增速、渗透率、头部公司增速和订单覆盖率验证",
    "技术更新快": "技术迭代需以关键工艺节点、研发投入、量产进度和客户认证周期验证",
    "人才重要": "人才依赖需以核心团队稳定性、工艺文档化率和激励覆盖范围验证",
    "估值偏高": "估值压力需以PB/PE、ROE、产能利用率和折旧压力对标验证",
    "发展前景良好": "发展前景需以订单、价格、产能利用率和现金流兑现情况验证",
    "机遇与挑战并存": "行业判断需拆分为需求、供给、政策、技术路线和资金链五类假设验证",
}

DEFAULT_DIAGNOSTIC_TITLES = [
    "行业阶段与竞争格局风险",
    "产业链议价能力与经营韧性风险",
    "行业KPI与授信审查适配风险",
]


@lru_cache()
def _get_primary_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0,
        max_tokens=3072,
        timeout=min(max(settings.LLM_TIMEOUT_SECONDS, LLM_INDUSTRY_TIMEOUT_SECONDS), 90),
        max_retries=1,
    )


@lru_cache()
def _get_backup_llm() -> ChatOpenAI | None:
    if not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY or not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL:
        return None
    return ChatOpenAI(
        model=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_MODEL or settings.LLM_MODEL,
        api_key=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY,
        base_url=settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL,
        temperature=0,
        max_tokens=3072,
        timeout=min(max(settings.LLM_TIMEOUT_SECONDS, LLM_INDUSTRY_TIMEOUT_SECONDS), 90),
        max_retries=1,
    )


def _available_llms() -> List[tuple[str, ChatOpenAI]]:
    backup = _get_backup_llm()
    if backup is not None:
        return [("backup", backup)]
    return [("primary", _get_primary_llm())]


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


def _as_list(value: Any, limit: int = 6) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def _unique(items: List[str], limit: int = 8) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        item = str(item).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _public_anchor_lines(public_info: Dict[str, Any]) -> List[str]:
    public_info = public_info or {}
    basic = public_info.get("basic_info") or {}
    review = public_info.get("annual_business_review") or {}
    main_business = public_info.get("main_business_composition") or []
    clues = public_info.get("search_clues") or {}
    lines: List[str] = []
    for key, label in [
        ("industry", "公开行业标签"),
        ("main_business", "主营业务"),
        ("concepts", "资本市场概念"),
        ("profile", "公开简介"),
    ]:
        value = basic.get(key)
        if value:
            lines.append(f"{label}：{value}")
    if review.get("business_review"):
        lines.append(f"年报经营讨论：{review.get('business_review')[:700]}")
    for row in main_business[:6]:
        if isinstance(row, dict):
            lines.append("主营构成：" + "，".join(f"{k}={v}" for k, v in row.items() if v))
    for clue_group in ["industry_position", "research_summaries", "litigation_announcements", "guarantee_pledge_announcements"]:
        for item in clues.get(clue_group) or []:
            content = item.get("content") or item.get("title") or ""
            if content:
                lines.append(f"公开线索/{clue_group}：{content[:240]}")
    return _unique(lines, 14)


def _rule_lines(knowledge_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "rule_id": rule.get("rule_id"),
            "title": rule.get("title"),
            "dimension": rule.get("dimension"),
            "required_checks": rule.get("required_checks") or [],
            "prompt_hint": rule.get("prompt_hint") or rule.get("risk_label") or "",
        }
        for rule in (knowledge_context.get("triggered_rules") or [])[:8]
    ]


def _knowledge_lines(knowledge_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "source_id": hit.get("source_id"),
            "title": hit.get("title"),
            "source": hit.get("source"),
            "content": hit.get("content"),
            "confidence": hit.get("confidence"),
        }
        for hit in (knowledge_context.get("knowledge_briefs") or [])[:6]
    ]


def _fallback_diagnostics(
    enterprise_name: str,
    classification: Dict[str, Any],
    public_info: Dict[str, Any],
    knowledge_context: Dict[str, Any],
) -> Dict[str, Any]:
    semantic_name = classification.get("semantic_industry_name") or classification.get("industry_name") or "待确认行业"
    path = " > ".join(classification.get("industry_path") or []) or "标准行业路径待确认"
    context_text = " ".join([
        semantic_name,
        path,
        str(((public_info or {}).get("basic_info") or {}).get("main_business") or ""),
        str(((public_info or {}).get("basic_info") or {}).get("concepts") or ""),
    ])
    is_semiconductor = any(keyword in context_text for keyword in ["半导体", "集成电路", "芯片", "电子器件"])
    basic = (public_info or {}).get("basic_info") or {}
    main_business = basic.get("main_business") or "[需补充：主营收入构成、核心产品和核心客户]"
    rules = _rule_lines(knowledge_context)
    source_ids = [hit.get("source_id") for hit in _knowledge_lines(knowledge_context) if hit.get("source_id")]

    def rule_ids(index: int) -> List[str]:
        return [rule.get("rule_id") for rule in rules[index:index + 3] if rule.get("rule_id")]

    if is_semiconductor:
        diagnostic_items = [
            {
                "title": "技术节点、产品结构与产能利用风险",
                "current_anchor": f"标的行业识别为{semantic_name}；标准路径为{path}；公开主营信息为{main_business}。当前尚未取得细分产品收入占比、晶圆产线节点、良率、产能利用率和客户认证进度。",
                "risk_substance": "集成电路制造/IDM企业的授信风险不能停留在概念标签，需穿透到工艺节点、产品毛利、产线稼动率和新增折旧压力；若扩产节奏快于订单覆盖或良率爬坡，利润和现金流会被折旧、研发投入与库存占用同步挤压。",
                "verification_actions": ["获取近三年按产品/工艺节点划分的收入和毛利", "核验主要产线产能利用率、良率和客户认证进度", "对标华虹公司、晶合集成、中芯国际等同业的成熟制程价格与稼动率"],
                "missing_items": ["主营构成", "工艺节点和良率", "产能利用率", "同业对标"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(0),
            },
            {
                "title": "产业链供需、库存周期与议价能力风险",
                "current_anchor": "半导体产业链受下游消费电子、汽车电子、工业控制等需求周期影响，当前公开资料尚不足以判断标的核心客户、供应商集中度和库存周期位置。",
                "risk_substance": "若下游需求修复弱于扩产节奏，成熟制程可能出现价格下行和库存跌价压力；若上游设备、材料或EDA/IP受制约，产线爬坡和交付稳定性也会影响回款质量与授信安全边界。",
                "verification_actions": ["获取前五大客户和供应商集中度及账期", "核查库存库龄、跌价准备和在手订单覆盖率", "跟踪设备、材料、出口管制和国产替代验证进度"],
                "missing_items": ["客户/供应商集中度", "库存库龄", "订单覆盖率", "设备材料约束"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(2),
            },
            {
                "title": "资本开支、研发投入与偿债压力传导风险",
                "current_anchor": f"当前已触发{len(rules)}条行业动态规则，知识库命中{len(source_ids)}条片段；尚未取得CAPEX计划、在建工程转固节奏、研发资本化比例和新增折旧测算。",
                "risk_substance": "半导体制造环节资金沉淀重，授信审查应把行业判断传导到现金流压力测试：若产能利用率、良率或订单不及预期，新增折旧和研发费用会压缩利润，存货和应收占用会进一步削弱偿债缓冲。",
                "verification_actions": ["编制CAPEX、转固和新增折旧滚动表", "测算不同产能利用率下的EBITDA和现金流敏感性", "核实政府补助、资本化研发和银行授信使用情况"],
                "missing_items": ["CAPEX计划", "转固和折旧测算", "研发资本化", "现金流敏感性模型"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(4),
            },
        ]
    else:
        diagnostic_items = [
            {
                "title": "行业阶段与竞争格局风险",
                "current_anchor": f"标的行业识别为{semantic_name}；公开主营信息为{main_business}；行业路径为{path}。",
                "risk_substance": "若行业已进入成熟期或周期底部，而企业仍依赖扩产、价格修复或单一产品放量支撑增长，则需重点核查增长假设与订单兑现能力。",
                "verification_actions": ["获取近三年行业增速、CR5和头部企业收入增速", "对比标的主营产品与头部企业产品结构", "核验新增订单、产能利用率和价格趋势"],
                "missing_items": ["行业增速", "CR5/市场份额", "头部企业对标数据"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(0),
            },
            {
                "title": "产业链议价能力与经营韧性风险",
                "current_anchor": "公开资料尚不足以完整判断上下游集中度、账期结构和关键客户替代成本。",
                "risk_substance": "若上游集中且下游议价强，企业可能面临原材料涨价难以传导、应收账期拉长和库存跌价压力；报告需避免仅用行业概念标签替代产业链核查。",
                "verification_actions": ["获取前五大客户和供应商集中度", "计算应付账款周转天数/应收账款周转天数", "核查核心合同价格调整和排他条款"],
                "missing_items": ["前五大客户/供应商", "账期和回款结构", "核心合同条款"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(2),
            },
            {
                "title": "行业KPI与授信审查适配风险",
                "current_anchor": f"当前已触发{len(rules)}条行业动态规则，知识库命中{len(source_ids)}条片段。",
                "risk_substance": "不同行业的关键KPI不同，需按四级行业确认细分赛道，再将专属KPI与收入、毛利、现金流、库存和应收账款交叉验证。",
                "verification_actions": ["按四级行业重新确认细分赛道", "补充行业专属KPI并与财务指标交叉验证", "将授信期限、额度释放和贷后监控条件绑定到行业KPI"],
                "missing_items": ["行业专属KPI", "同业基准", "政策和技术路线变化"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(4),
            },
        ]

    return {
        "overall_position": {
            "cycle_stage": "[需补充：行业增速、库存周期和头部公司财报后判断]",
            "positioning": f"{enterprise_name}已识别为{semantic_name}，标准路径为{path}",
            "core_judgement": "现阶段行业结论基于标准行业分类、公开资料线索和本地尽调规则，尚未取得足够的行业KPI与同业对标数据，正式授信前需补充验证。",
            "confidence": 0.62,
        },
        "diagnostics": diagnostic_items,
        "assumptions": ["行业增速和竞争格局需以监管、行业协会、上市公司年报和权威研报为准", "公开搜索线索只能作为初筛，不能替代人工核验"],
        "data_boundary": "行业诊断基于行业代码库、公开资料线索、RAG知识库和触发规则生成；缺失细分KPI时使用[需补充]标记，不作为最终授信依据。",
    }


def _sanitize_generic_text(text: str) -> str:
    result = text or ""
    for term, replacement in GENERIC_REWRITES.items():
        result = result.replace(term, replacement)
    return result


def _normalize(parsed: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    overall = parsed.get("overall_position") if isinstance(parsed.get("overall_position"), dict) else {}
    items = parsed.get("diagnostics") if isinstance(parsed.get("diagnostics"), list) else []
    normalized_items = []
    fallback_items = fallback.get("diagnostics") or []
    for index, item in enumerate(items[:3]):
        if not isinstance(item, dict):
            continue
        fb = fallback_items[index] if index < len(fallback_items) else {}
        normalized_items.append({
            "title": _sanitize_generic_text(str(item.get("title") or fb.get("title") or DEFAULT_DIAGNOSTIC_TITLES[index]).strip()),
            "current_anchor": _sanitize_generic_text(str(item.get("current_anchor") or item.get("anchor") or fb.get("current_anchor") or "").strip()),
            "risk_substance": _sanitize_generic_text(str(item.get("risk_substance") or item.get("risk") or fb.get("risk_substance") or "").strip()),
            "verification_actions": [_sanitize_generic_text(value) for value in (_as_list(item.get("verification_actions") or item.get("verification_action"), 5) or fb.get("verification_actions") or [])],
            "missing_items": [_sanitize_generic_text(value) for value in (_as_list(item.get("missing_items"), 5) or fb.get("missing_items") or [])],
            "evidence_ids": _as_list(item.get("evidence_ids") or item.get("knowledge_source_ids"), 5) or fb.get("evidence_ids") or [],
            "rule_ids": _as_list(item.get("rule_ids"), 5) or fb.get("rule_ids") or [],
        })
    if len(normalized_items) < 3:
        normalized_items.extend(fallback_items[len(normalized_items):3])
    return {
        "overall_position": {
            "cycle_stage": _sanitize_generic_text(str(overall.get("cycle_stage") or (fallback.get("overall_position") or {}).get("cycle_stage") or "[需补充：行业周期]").strip()),
            "positioning": _sanitize_generic_text(str(overall.get("positioning") or (fallback.get("overall_position") or {}).get("positioning") or "行业定位待补充").strip()),
            "core_judgement": _sanitize_generic_text(str(overall.get("core_judgement") or overall.get("conclusion") or (fallback.get("overall_position") or {}).get("core_judgement") or "行业结论需补充公开资料后复核。" ).strip()),
            "confidence": overall.get("confidence", (fallback.get("overall_position") or {}).get("confidence", 0.6)),
        },
        "diagnostics": normalized_items[:3],
        "assumptions": _as_list(parsed.get("assumptions"), 6) or fallback.get("assumptions") or [],
        "data_boundary": str(parsed.get("data_boundary") or fallback.get("data_boundary") or "行业诊断需人工复核。").strip(),
    }


def render_industry_diagnostics(diagnostics: Dict[str, Any]) -> List[str]:
    overall = diagnostics.get("overall_position") or {}
    header = f"【行业定位与周期判断】{overall.get('cycle_stage') or '[需补充：行业周期]'} | {overall.get('positioning') or '行业定位待补充'}。{overall.get('core_judgement') or ''}".strip()
    lines = [header]
    for index, item in enumerate(diagnostics.get("diagnostics") or [], 1):
        actions = "；".join(_as_list(item.get("verification_actions"), 5)) or "补充行业KPI、同业对标和公开权威来源后复核"
        missing = _as_list(item.get("missing_items"), 5)
        missing_text = "；待补充：" + "、".join(missing) if missing else ""
        lines.append(
            f"{index}. {item.get('title') or DEFAULT_DIAGNOSTIC_TITLES[index - 1]}\n"
            f"现状锚定：{item.get('current_anchor') or '[需补充：行业事实锚点]'}\n"
            f"风险实质：{item.get('risk_substance') or '[需补充：风险实质]'}\n"
            f"核查要点：{actions}{missing_text}"
        )
    boundary = diagnostics.get("data_boundary")
    if boundary:
        lines.append(f"数据边界：{boundary}")
    return lines[:6]


def _has_anchor(text: str) -> bool:
    return bool(
        re.search(r"\d+(?:\.\d+)?\s*(?:%|pct|年|个月|亿元|万元|倍|家|条|项)?", text)
        or "[需补充" in text
        or any(keyword in text for keyword in ["对标", "同业", "头部", "年报", "公开", "主营", "行业路径", "规则", "知识库"])
    )


def _quality_warnings(diagnostics: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    rendered = "\n".join(render_industry_diagnostics(diagnostics))
    for term in BANNED_GENERIC_TERMS:
        if term in rendered:
            warnings.append(f"LLM行业诊断包含泛化表达：{term}")
    items = diagnostics.get("diagnostics") or []
    if len(items) < 3:
        warnings.append("LLM行业诊断不足3项")
    for index, item in enumerate(items[:3], 1):
        if not item.get("current_anchor") or not item.get("risk_substance"):
            warnings.append(f"第{index}项缺少现状锚定或风险实质")
        if not item.get("verification_actions"):
            warnings.append(f"第{index}项缺少核查要点")
        if not (item.get("rule_ids") or item.get("evidence_ids")):
            warnings.append(f"第{index}项缺少规则ID或证据来源ID")
        if not _has_anchor(f"{item.get('current_anchor', '')}\n{item.get('risk_substance', '')}"):
            warnings.append(f"第{index}项缺少具体事实锚点或[需补充]标记")
    if not diagnostics.get("data_boundary"):
        warnings.append("LLM行业诊断缺少数据边界")
    return warnings[:8]


def _prompt(
    enterprise_name: str,
    classification: Dict[str, Any],
    public_info: Dict[str, Any],
    knowledge_context: Dict[str, Any],
) -> str:
    payload = {
        "enterprise_name": enterprise_name,
        "industry_classification": {
            "industry_code": classification.get("industry_code"),
            "industry_name": classification.get("industry_name"),
            "industry_path": classification.get("industry_path"),
            "semantic_industry_id": classification.get("semantic_industry_id"),
            "semantic_industry_name": classification.get("semantic_industry_name"),
            "classification_source": classification.get("classification_source"),
            "llm_reason": classification.get("llm_reason"),
            "ignored_noise": classification.get("ignored_noise"),
        },
        "public_anchors": _public_anchor_lines(public_info),
        "triggered_rules": _rule_lines(knowledge_context),
        "rag_knowledge": _knowledge_lines(knowledge_context),
    }
    return f"""
你是银行贷前尽调行业分析师。请基于输入资料生成“尽调式诊断”，只输出 JSON，不要输出 Markdown，不要解释过程。

输入资料：{json.dumps(payload, ensure_ascii=False)}

写作目标：学习资深分析师的结构，但绝不编造未提供的数字。行业分析要回答“这门生意好不好、能不能持续、授信审查应核什么”。

硬性要求：
1. 输出 overall_position 和 3 个 diagnostics，结构为“现状锚定 / 风险实质 / 核查要点”。
2. 每个 diagnostics 至少引用一个 rule_id 或 evidence/source_id；若证据不足，必须写 [需补充：...]，不能虚构良率、市场份额、估值、CR5、订单覆盖率等数字。
3. 每段必须绑定标的行业、主营业务、公开资料、RAG 知识或触发规则之一，不能写行业科普。
4. 行业子赛道必须尽量精准，例如半导体需区分设计、制造、封测、设备材料；无法判断时写 [需补充：细分赛道]。
5. 必须包含关键假设和数据边界，提醒公开资料只能用于初筛。
6. 禁止空泛表达：{', '.join(BANNED_GENERIC_TERMS)}。如果需要表达类似含义，必须加事实锚点、对标对象、时间节点或 [需补充]。

JSON格式：
{{
  "overall_position": {{"cycle_stage": "周期阶段或[需补充]", "positioning": "行业定位", "core_judgement": "一句话核心判断", "confidence": 0.75}},
  "diagnostics": [
    {{"title": "技术/产品/竞争格局风险", "current_anchor": "现状锚定", "risk_substance": "风险实质", "verification_actions": ["核查动作"], "missing_items": ["待补充材料"], "evidence_ids": ["知识或证据ID"], "rule_ids": ["规则ID"]}},
    {{"title": "产业链议价能力与经营韧性风险", "current_anchor": "现状锚定", "risk_substance": "风险实质", "verification_actions": ["核查动作"], "missing_items": ["待补充材料"], "evidence_ids": ["知识或证据ID"], "rule_ids": ["规则ID"]}},
    {{"title": "行业KPI与授信审查适配风险", "current_anchor": "现状锚定", "risk_substance": "风险实质", "verification_actions": ["核查动作"], "missing_items": ["待补充材料"], "evidence_ids": ["知识或证据ID"], "rule_ids": ["规则ID"]}}
  ],
  "assumptions": ["关键假设"],
  "data_boundary": "数据边界"
}}
""".strip()


def _invoke_one(provider: str, llm: ChatOpenAI, prompt: str) -> Dict[str, Any]:
    started_at = time.monotonic()
    response = llm.invoke(prompt)
    return {
        "provider": provider,
        "raw_response": str(getattr(response, "content", response)),
        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
        "response_metadata": getattr(response, "response_metadata", {}) or {},
    }


def _invoke_llm(prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    futures: Dict[Future, str] = {
        _LLM_EXECUTOR.submit(_invoke_one, provider, llm, prompt): provider
        for provider, llm in _available_llms()
    }
    if not futures:
        raise RuntimeError("未配置可用行业诊断 LLM")
    deadline = time.monotonic() + LLM_INDUSTRY_TIMEOUT_SECONDS
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
            parsed = _extract_json(result.get("raw_response") or "")
            diagnostics = _normalize(parsed, fallback) if parsed else {}
            warnings = _quality_warnings(diagnostics) if diagnostics else ["LLM行业诊断未返回可解析JSON"]
            result["diagnostics"] = diagnostics or fallback
            result["summary"] = render_industry_diagnostics(result["diagnostics"])
            result["quality_warnings"] = warnings
            if not warnings:
                for pending in futures:
                    pending.cancel()
                result["race_errors"] = errors
                return result
            if first_candidate is None:
                first_candidate = result
            errors.append(f"{provider}未通过质量闸门：{'；'.join(warnings[:3])}")
    for pending in futures:
        pending.cancel()
    if first_candidate is not None:
        first_candidate["race_errors"] = errors
        return first_candidate
    raise TimeoutError("；".join(errors) or f"LLM行业诊断超过{LLM_INDUSTRY_TIMEOUT_SECONDS}秒未返回")


def build_industry_diagnostic_narrative(
    enterprise_name: str,
    classification: Dict[str, Any],
    public_info: Dict[str, Any] | None = None,
    industry_knowledge_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build industry diagnostics with guarded LLM fallback."""
    public_info = public_info or {}
    knowledge_context = industry_knowledge_context or {}
    fallback = _fallback_diagnostics(enterprise_name, classification, public_info, knowledge_context)
    started_at = time.monotonic()
    try:
        candidate = _invoke_llm(_prompt(enterprise_name, classification, public_info, knowledge_context), fallback)
        warnings = candidate.get("quality_warnings") or []
        if warnings:
            return {
                "success": False,
                "source": "fallback",
                "summary": render_industry_diagnostics(fallback),
                "diagnostics": fallback,
                "quality_warnings": warnings + (candidate.get("race_errors") or []),
                "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
                "llm_provider": candidate.get("provider"),
            }
        return {
            "success": True,
            "source": "llm",
            "summary": candidate.get("summary") or render_industry_diagnostics(candidate.get("diagnostics") or fallback),
            "diagnostics": candidate.get("diagnostics") or fallback,
            "quality_warnings": candidate.get("race_errors") or [],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
            "llm_provider": candidate.get("provider"),
        }
    except Exception as exc:
        return {
            "success": False,
            "source": "fallback",
            "summary": render_industry_diagnostics(fallback),
            "diagnostics": fallback,
            "quality_warnings": [f"LLM行业诊断生成失败：{type(exc).__name__}"],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
        }
