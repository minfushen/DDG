"""Dynamic knowledge context for industry due-diligence reports."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
import json

from app.config import settings
from app.rag.knowledge_retrieval_service import retrieve_knowledge


RULE_PATH = settings.BASE_DIR / "knowledge_base" / "risk_frameworks" / "industry_analysis_rules.json"


@lru_cache(maxsize=1)
def load_industry_analysis_rules() -> List[Dict[str, Any]]:
    if not Path(RULE_PATH).exists():
        return []
    return json.loads(Path(RULE_PATH).read_text(encoding="utf-8"))


def _semantic_text(classification: Dict[str, Any]) -> str:
    return " ".join([
        str(classification.get("semantic_industry_id") or ""),
        str(classification.get("semantic_industry_name") or ""),
        str(classification.get("industry_name") or ""),
        " ".join(classification.get("industry_path") or []),
    ]).lower()


def _triggered_rules(classification: Dict[str, Any], public_info: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    text = _semantic_text(classification)
    public_info = public_info or {}
    basic = public_info.get("basic_info") or {}
    context = " ".join([
        text,
        str(basic.get("industry") or ""),
        str(basic.get("main_business") or ""),
        str(basic.get("concepts") or ""),
    ]).lower()
    active: List[Dict[str, Any]] = []
    for rule in load_industry_analysis_rules():
        rule_id = rule.get("rule_id") or ""
        triggered = False
        if rule_id in {"IND-LIFE-001", "IND-LIFE-002", "IND-CHAIN-001", "IND-CHAIN-002", "IND-POLICY-001"}:
            triggered = True
        elif rule_id == "IND-KPI-MFG-001":
            triggered = any(keyword in context for keyword in ["制造", "半导体", "集成电路", "新能源", "电池", "电子器件"])
        elif rule_id == "IND-KPI-SOFT-001":
            triggered = any(keyword in context for keyword in ["软件", "saas", "互联网", "订阅", "云"])
        elif rule_id == "IND-KPI-TRADE-001":
            triggered = any(keyword in context for keyword in ["贸易", "供应链", "批发", "零售", "进出口"])
        elif rule_id == "IND-RISK-EXPORT-001":
            triggered = any(keyword in context for keyword in ["出口", "海外", "外销", "进出口"])
        if triggered:
            active.append({**rule, "confidence": 0.78})
    return active[:8]


def _build_query(enterprise_name: str, classification: Dict[str, Any], public_info: Dict[str, Any] | None, triggered_rules: List[Dict[str, Any]]) -> str:
    public_info = public_info or {}
    basic = public_info.get("basic_info") or {}
    rule_titles = " ".join(rule.get("title", "") for rule in triggered_rules)
    return " ".join([
        enterprise_name,
        classification.get("semantic_industry_name") or "",
        classification.get("industry_name") or "",
        " ".join(classification.get("industry_path") or []),
        str(basic.get("industry") or ""),
        str(basic.get("main_business") or ""),
        "行业生命周期 竞争格局 产业链议价能力 行业KPI 政策技术风险 授信审查",
        rule_titles,
    ])


def build_industry_knowledge_context(
    enterprise_name: str,
    classification: Dict[str, Any],
    public_info: Dict[str, Any] | None = None,
    top_k: int = 6,
) -> Dict[str, Any]:
    triggered = _triggered_rules(classification, public_info)
    query = _build_query(enterprise_name, classification, public_info, triggered)
    retrieval = retrieve_knowledge(query=query, domain="industry", top_k=top_k)
    hits = retrieval.get("results") or []
    knowledge_briefs = []
    for hit in hits[:top_k]:
        knowledge_briefs.append({
            "source_id": hit.get("id"),
            "title": hit.get("title"),
            "source": hit.get("relative_path") or hit.get("source"),
            "header": hit.get("header"),
            "content": hit.get("content", "")[:420],
            "confidence": hit.get("confidence"),
            "retrieval_mode": hit.get("retrieval_mode"),
        })
    return {
        "query": query,
        "triggered_rules": triggered,
        "knowledge_briefs": knowledge_briefs,
        "retrieval": retrieval,
    }
