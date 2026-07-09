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

from app.config.llm_config import cached_invoke, get_llm
from app.config import settings
from app.config.prompt_loader import load_prompt_template, render_prompt_template
from app.config.quality_gate_loader import get_banned_terms, get_generic_rewrites


LLM_INDUSTRY_TIMEOUT_SECONDS = 60
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=3, thread_name_prefix="industry-diagnostic")

BANNED_GENERIC_TERMS = get_banned_terms("industry_diagnostic")
GENERIC_REWRITES = get_generic_rewrites()

DEFAULT_DIAGNOSTIC_TITLES = [
    "行业阶段与竞争格局风险",
    "产业链议价能力与经营韧性风险",
    "行业KPI与授信审查适配风险",
]


@lru_cache()
def _get_primary_llm() -> BaseChatModel:
    return get_llm(
        temperature=0,
        max_tokens=3072,
        timeout=min(max(settings.LLM_TIMEOUT_SECONDS, LLM_INDUSTRY_TIMEOUT_SECONDS), 90),
        max_retries=1,
    )


@lru_cache()
def _get_backup_llm() -> BaseChatModel | None:
    if not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY or not settings.FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL:
        return None
    return get_llm(
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
        lines.append(f"年报经营讨论：{review.get('business_review')[:1500]}")
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




def _pick_industry_name(classification: dict) -> str:
    """从分类结果中提取优先行业名称。

    优先取 semantic_industry_name，其次 industry_name，兜底为"未知行业"。
    """
    return classification.get("semantic_industry_name") or classification.get("industry_name") or "未知行业"


def _fetch_market_data_anchor(classification: dict) -> dict:
    """获取并规范化行业市场数据锚点。

    调用 get_industry_market_data，对搜索结果截断到 title+snippet 共不超过 240 字符，
    并保留 source/date/url 以及质量相关字段。失败时保留 error 字段。
    """
    from app.agents.tools.industry_market_data_tool import get_industry_market_data

    raw = get_industry_market_data(_pick_industry_name(classification))
    if not raw.get("success"):
        return {"success": False, "error": raw.get("error") or "获取行业市场数据失败"}

    def _truncate_result(result: dict) -> dict:
        title = (result.get("title") or "")[:120]
        snippet = (result.get("snippet") or "")[:120]
        return {
            "title": title,
            "snippet": snippet,
            "source": result.get("source"),
            "date": result.get("date"),
            "url": result.get("url"),
            "trust_level": result.get("trust_level"),
            "confidence": result.get("confidence"),
            "source_type": result.get("source_type"),
            "requires_manual_review": result.get("requires_manual_review"),
            "query": result.get("query"),
        }

    def _normalize_search_category(category: dict) -> dict:
        return {
            "queries": category.get("queries") or [],
            "results": [_truncate_result(r) for r in (category.get("results") or [])],
            "quality_score": category.get("quality_score"),
            "quality_level": category.get("quality_level"),
            "refilled": category.get("refilled"),
        }

    index_data = raw.get("index_data") or {}
    return {
        "success": True,
        "industry_name": raw.get("industry_name"),
        "quality_summary": raw.get("quality_summary"),
        "index_data": {
            "success": index_data.get("success", False),
            "symbol": index_data.get("symbol"),
            "latest_close": index_data.get("latest_close"),
            "latest_date": index_data.get("latest_date"),
            "year_change_pct": index_data.get("year_change_pct"),
            "avg_turnover": index_data.get("avg_turnover"),
            "source": index_data.get("source"),
            "error": index_data.get("error"),
            "quality_level": index_data.get("quality_level"),
            "fallback_search": index_data.get("fallback_search"),
        },
        "market_size": _normalize_search_category(raw.get("market_size") or {}),
        "concentration": _normalize_search_category(raw.get("concentration") or {}),
        "policy": _normalize_search_category(raw.get("policy") or {}),
        "chain": _normalize_search_category(raw.get("chain") or {}),
        "research_reports": _normalize_search_category(raw.get("research_reports") or {}),
    }


def _build_market_data_anchor_text(data_anchors: dict) -> list[str]:
    """将市场数据锚点渲染为供 LLM 引用的文本行列表。"""
    lines: list[str] = []
    index = data_anchors.get("index_data") or {}
    if index.get("success"):
        symbol = index.get("symbol") or ""
        latest_close = index.get("latest_close")
        latest_date = index.get("latest_date") or ""
        year_change = index.get("year_change_pct")
        avg_turnover = index.get("avg_turnover")
        parts = []
        if latest_close is not None:
            parts.append(f"最新收盘 {latest_close}")
        if latest_date:
            parts.append(f"日期 {latest_date}")
        if year_change is not None:
            parts.append(f"近一年涨跌幅 {year_change}%")
        if avg_turnover is not None:
            parts.append(f"近20日平均成交额 {avg_turnover} 亿元")
        line = f"东方财富行业指数（{symbol}）" + "，".join(parts) + "。"
        idx_quality = index.get("quality_level")
        if idx_quality and idx_quality != "ok":
            line += f"[指数数据：{idx_quality}]"
        if index.get("error"):
            line += "[需补充]"
        lines.append(line)
    else:
        lines.append("行业指数：未获取到有效指数数据。")

    category_labels = {
        "market_size": "市场规模",
        "concentration": "竞争格局",
        "policy": "政策",
        "chain": "产业链",
        "research_reports": "研报",
    }
    for key, label in category_labels.items():
        category = data_anchors.get(key) or {}
        results = category.get("results") or []
        cat_quality_level = category.get("quality_level")
        if not results:
            missing_line = f"[{label}] 未获取到有效公开线索"
            if cat_quality_level in ("low", "none"):
                missing_line += f" [数据质量：{cat_quality_level}]"
            missing_line += " [需补充]"
            lines.append(missing_line)
            continue
        for result in results[:2]:
            title = result.get("title") or ""
            snippet = (result.get("snippet") or "")[:80]
            source = result.get("source") or ""
            date = result.get("date") or ""
            meta = ", ".join(p for p in [source, date] if p)
            meta_text = f"（{meta}）" if meta else ""
            line = f"[{label}] {title} | {snippet}{meta_text}"
            if cat_quality_level in ("low", "none"):
                line += f"[数据质量：{cat_quality_level}]"
            if result.get("requires_manual_review"):
                line += "[需人工复核]"
            lines.append(line)

    return lines

def _format_attribution_anchor(annual_report_notes: Dict[str, Any] | None) -> str:
    """把年报深度归因渲染为行业诊断可用的现状锚点句。"""
    attribution = (annual_report_notes or {}).get("attribution") or {}
    if not attribution or attribution.get("source") == "fallback":
        return ""
    parts: List[str] = []
    for field, label in [
        ("industry_context", "年报对行业景气/竞争格局的判断"),
        ("capacity_status", "年报披露的产能状态"),
        ("company_strategy", "年报披露的经营策略"),
    ]:
        value = attribution.get(field)
        if value:
            parts.append(f"{label}：{value}")
    for field, label in [
        ("revenue_drivers", "年报对营收增长的解释"),
        ("margin_drivers", "年报对毛利率变动的解释"),
        ("profit_drivers", "年报对利润变动的解释"),
    ]:
        drivers = attribution.get(field) or []
        for driver in drivers[:2]:
            factor = driver.get("factor") or ""
            if factor:
                parts.append(f"{label}：{factor}")
    if not parts:
        return ""
    return "；".join(parts) + "（来源：年报经营情况讨论与分析章节）。"


def _fallback_diagnostics(
    enterprise_name: str,
    classification: Dict[str, Any],
    public_info: Dict[str, Any],
    knowledge_context: Dict[str, Any],
    annual_report_notes: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    semantic_name = classification.get("semantic_industry_name") or classification.get("industry_name") or "待确认行业"
    path = " > ".join(classification.get("industry_path") or []) or "标准行业路径待确认"
    context_text = " ".join([
        semantic_name,
        path,
        str(((public_info or {}).get("basic_info") or {}).get("main_business") or ""),
        str(((public_info or {}).get("basic_info") or {}).get("concepts") or ""),
    ])
    semantic_id = str(classification.get("semantic_industry_id") or "")
    is_new_energy = semantic_id == "new_energy" or any(keyword in context_text for keyword in ["锂电", "锂离子电池", "动力电池", "储能", "电芯", "PACK", "BMS"])
    is_semiconductor = (semantic_id == "semiconductor") or (
        not is_new_energy and any(keyword in context_text for keyword in ["半导体", "集成电路", "芯片", "晶圆", "功率器件", "分立器件"])
    )
    basic = (public_info or {}).get("basic_info") or {}
    main_business = basic.get("main_business") or "[需补充：主营收入构成、核心产品和核心客户]"
    rules = _rule_lines(knowledge_context)
    source_ids = [hit.get("source_id") for hit in _knowledge_lines(knowledge_context) if hit.get("source_id")]
    attribution_anchor = _format_attribution_anchor(annual_report_notes)

    def rule_ids(index: int) -> List[str]:
        return [rule.get("rule_id") for rule in rules[index:index + 3] if rule.get("rule_id")]

    def _anchor_with_attribution(base: str) -> str:
        if not attribution_anchor:
            return base
        if attribution_anchor in base:
            return base
        return base + " " + attribution_anchor

    if is_new_energy:
        diagnostic_items = [
            {
                "title": "产品结构、技术路线与需求周期风险",
                "current_anchor": _anchor_with_attribution(f"标的行业识别为{semantic_name}；标准路径为{path}；公开主营信息为{main_business}。当前仍需补充消费类电池、动力电池、储能、电芯/PACK/BMS等产品收入占比、毛利率和客户结构。"),
                "risk_substance": "锂电池企业授信风险应穿透到产品结构和技术路线：消费电子电池受终端换机周期影响，动力电池受整车厂定点和装车量影响，储能业务受项目交付、消防安全和海外认证影响。若收入增长来自低毛利扩产或价格竞争，现金流和利润修复可能不同步。",
                "verification_actions": ["获取近三年按消费类电池、动力电池、储能等拆分的收入和毛利", "核验核心客户定点、订单覆盖率和装车/出货量数据", "对标宁德时代、亿纬锂能、国轩高科等同业产品结构和毛利率"],
                "missing_items": ["主营构成", "出货量/装车量", "客户定点和订单覆盖率", "同业毛利率基准"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(0),
            },
            {
                "title": "产业链价格、库存与回款质量风险",
                "current_anchor": "锂电池产业链受锂盐、正负极材料价格、下游消费电子/新能源车/储能需求和库存周期共同影响；当前公开资料尚不足以完整判断原材料锁价、库存库龄和主要客户账期。",
                "risk_substance": "若上游材料价格波动无法及时传导，或下游客户议价强、账期拉长，企业可能出现毛利率承压、存货跌价和应收占用并存。授信审查不能只看收入规模，应把库存、应收、经营现金流和客户集中度交叉验证。",
                "verification_actions": ["获取前五大客户/供应商集中度和账期", "核查存货库龄、跌价准备和原材料价格传导机制", "比较应收增速、收入增速和经营现金流匹配度"],
                "missing_items": ["客户/供应商集中度", "存货库龄", "跌价准备", "价格联动条款"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(2),
            },
            {
                "title": "扩产投入、安全合规与授信边界风险",
                "current_anchor": f"当前已触发{len(rules)}条行业动态规则，知识库命中{len(source_ids)}条片段；尚未取得产能利用率、CAPEX计划、海外认证、质量召回和储能安全事故相关核验材料。",
                "risk_substance": "电池制造资本开支和研发投入较重，扩产、良率、质量安全和海外合规会直接影响现金流安全边界。若新增产能释放慢于订单兑现，或海外电池法规、碳足迹、召回责任带来额外成本，授信期限和额度释放应更保守。",
                "verification_actions": ["编制产能、CAPEX、转固和新增折旧滚动表", "核查海外认证、欧盟电池法和碳足迹合规准备", "设置订单、回款、库存和安全事故的贷后监控指标"],
                "missing_items": ["CAPEX和产能利用率", "海外认证/碳足迹资料", "质量召回和安全生产记录", "贷后监控阈值"],
                "evidence_ids": source_ids[:3],
                "rule_ids": rule_ids(4),
            },
        ]
    elif is_semiconductor:
        diagnostic_items = [
            {
                "title": "技术节点、产品结构与产能利用风险",
                "current_anchor": _anchor_with_attribution(f"标的行业识别为{semantic_name}；标准路径为{path}；公开主营信息为{main_business}。当前尚未取得细分产品收入占比、晶圆产线节点、良率、产能利用率和客户认证进度。"),
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
                "current_anchor": _anchor_with_attribution(f"标的行业识别为{semantic_name}；公开主营信息为{main_business}；行业路径为{path}。"),
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
    data_anchors = diagnostics.get("data_anchors")
    if data_anchors:
        anchor_texts = _build_market_data_anchor_text(data_anchors)
        index_line = anchor_texts[0] if anchor_texts else ""
        other_lines = [t for t in anchor_texts[1:] if t]
        summary = " ".join(other_lines[:2]) if other_lines else ""
        if index_line or summary:
            lines.append(f"数据锚点：{index_line} {summary}".strip())
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


def _cross_industry_warnings(diagnostics: Dict[str, Any], classification: Dict[str, Any]) -> List[str]:
    semantic_id = str(classification.get("semantic_industry_id") or "")
    rendered = "\n".join(render_industry_diagnostics(diagnostics))
    warnings: List[str] = []
    if semantic_id == "new_energy":
        forbidden = ["晶圆", "IDM", "集成电路", "半导体制造", "工艺节点", "流片", "制程", "EDA", "光刻", "封测"]
        hits = [term for term in forbidden if term in rendered]
        if hits:
            warnings.append(f"新能源/锂电池行业诊断混入半导体术语：{', '.join(hits[:5])}")
    if semantic_id == "semiconductor":
        forbidden = ["动力电池装车量", "储能电站", "电芯", "PACK", "BMS", "欧盟电池法", "碳足迹"]
        hits = [term for term in forbidden if term in rendered]
        if hits:
            warnings.append(f"半导体行业诊断混入锂电池术语：{', '.join(hits[:5])}")
    return warnings


def _prompt(
    enterprise_name: str,
    classification: Dict[str, Any],
    public_info: Dict[str, Any],
    knowledge_context: Dict[str, Any],
    annual_report_notes: Dict[str, Any] | None = None,
    market_data_anchor: Dict[str, Any] | None = None,
) -> str:
    """构建行业诊断 LLM prompt。"""
    attribution = (annual_report_notes or {}).get("attribution") or {}
    attribution_payload: Dict[str, Any] = {}
    if attribution and attribution.get("source") != "fallback":
        attribution_payload = {
            "industry_context": attribution.get("industry_context"),
            "capacity_status": attribution.get("capacity_status"),
            "company_strategy": attribution.get("company_strategy"),
            "revenue_drivers": attribution.get("revenue_drivers") or [],
            "margin_drivers": attribution.get("margin_drivers") or [],
            "profit_drivers": attribution.get("profit_drivers") or [],
            "forward_risks": attribution.get("forward_risks") or [],
            "data_boundary": attribution.get("data_boundary"),
        }
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
        "annual_report_attribution": attribution_payload,
        "triggered_rules": _rule_lines(knowledge_context),
        "rag_knowledge": _knowledge_lines(knowledge_context),
        "market_data_anchors": _build_market_data_anchor_text(market_data_anchor or {}),
    }
    template = load_prompt_template("industry_diagnostic")
    variables = {
        "payload": json.dumps(payload, ensure_ascii=False),
        "banned_terms": ", ".join(BANNED_GENERIC_TERMS),
    }
    return render_prompt_template(template, variables).strip()


def _invoke_one(
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


def _invoke_llm(
    prompt: str,
    fallback: Dict[str, Any],
    session_id: str | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    futures: Dict[Future, str] = {
        _LLM_EXECUTOR.submit(_invoke_one, provider, llm, prompt, session_id, task_id): provider
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
    annual_report_notes: Dict[str, Any] | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    """Build industry diagnostics with guarded LLM fallback."""
    public_info = public_info or {}
    knowledge_context = industry_knowledge_context or {}
    data_anchors = _fetch_market_data_anchor(classification)
    fallback = _fallback_diagnostics(enterprise_name, classification, public_info, knowledge_context, annual_report_notes=annual_report_notes)
    started_at = time.monotonic()
    try:
        candidate = _invoke_llm(
            _prompt(enterprise_name, classification, public_info, knowledge_context, annual_report_notes=annual_report_notes, market_data_anchor=data_anchors),
            fallback,
            session_id=session_id,
            task_id=task_id,
        )
        diagnostics = candidate.get("diagnostics") or fallback
        warnings = (candidate.get("quality_warnings") or []) + _cross_industry_warnings(diagnostics, classification)
        if warnings:
            return {
                "success": False,
                "source": "fallback",
                "summary": render_industry_diagnostics(fallback),
                "diagnostics": fallback,
                "quality_warnings": warnings + (candidate.get("race_errors") or []),
                "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
                "llm_provider": candidate.get("provider"),
                "data_anchors": data_anchors,
            }
        return {
            "success": True,
            "source": "llm",
            "summary": candidate.get("summary") or render_industry_diagnostics(diagnostics),
            "diagnostics": diagnostics,
            "quality_warnings": candidate.get("race_errors") or [],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
            "llm_provider": candidate.get("provider"),
            "data_anchors": data_anchors,
        }
    except Exception as exc:
        return {
            "success": False,
            "source": "fallback",
            "summary": render_industry_diagnostics(fallback),
            "diagnostics": fallback,
            "quality_warnings": [f"LLM行业诊断生成失败：{type(exc).__name__}"],
            "llm_elapsed_ms": round((time.monotonic() - started_at) * 1000),
            "data_anchors": data_anchors,
        }
