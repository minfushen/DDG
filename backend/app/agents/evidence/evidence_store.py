"""Unified evidence normalization and collection.

Agents historically returned small dictionaries like {label, value, source}.
The Evidence Store keeps those fields for compatibility while adding a standard
claim/source/confidence model that reports and future RAG flows can depend on.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


DOMAIN_BY_AGENT = {
    "business": "工商",
    "financial": "财务",
    "legal": "司法",
    "industry": "行业",
    "system": "系统",
}


LOW_RELIABILITY_SOURCES = {"模拟财务数据", "旧模拟司法工具", "系统判定"}
HIGH_SOURCE_KEYWORDS = ["天眼查", "企查查", "国家企业信用", "巨潮", "东方财富", "财报", "审计", "industry_code4", "国民经济行业"]
MEDIUM_SOURCE_KEYWORDS = ["Tavily", "公开搜索", "本地行业", "知识库", "工商登记", "行业代码"]


def _stable_id(agent: str, label: str, value: str, source: str) -> str:
    raw = f"{agent}|{label}|{value}|{source}"
    return "ev_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _infer_reliability(source: str, confidence: Optional[float] = None, trust_level: Optional[str] = None) -> str:
    if trust_level in {"high", "medium", "low"}:
        return trust_level
    if source in LOW_RELIABILITY_SOURCES:
        return "low"
    if confidence is not None:
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.6:
            return "medium"
        return "low"
    if any(keyword in source for keyword in HIGH_SOURCE_KEYWORDS):
        return "high"
    if any(keyword in source for keyword in MEDIUM_SOURCE_KEYWORDS):
        return "medium"
    return "medium" if source else "low"


def _infer_confidence(source: str, reliability: str, confidence: Optional[float] = None) -> float:
    if isinstance(confidence, (int, float)):
        return max(0.0, min(1.0, float(confidence)))
    if source in LOW_RELIABILITY_SOURCES:
        return 0.35
    return {"high": 0.9, "medium": 0.7, "low": 0.4}.get(reliability, 0.55)


def _infer_source_type(source: str) -> str:
    if not source:
        return "unknown"
    if source in LOW_RELIABILITY_SOURCES:
        return "simulation_or_system_boundary"
    if "财报" in source or "审计" in source or "东方财富" in source or "巨潮" in source:
        return "financial_statement"
    if "Tavily" in source or "公开搜索" in source:
        return "public_search"
    if "知识库" in source or "行业指南" in source or "本地行业" in source:
        return "internal_knowledge_base"
    if "工商" in source or "天眼查" in source or "企查查" in source or "企业信用" in source:
        return "business_registry"
    if "司法" in source or "裁判" in source or "执行" in source:
        return "legal_public_source"
    if "industry_code4" in source or "国民经济行业" in source:
        return "industry_codebook"
    return "public_or_internal_source"


def normalize_evidence(item: Dict[str, Any], agent: str = "system", domain: Optional[str] = None) -> Dict[str, Any]:
    """Normalize one evidence dict while preserving old fields."""
    label = str(item.get("label") or item.get("name") or item.get("field") or "证据项")
    value = "" if item.get("value") is None else str(item.get("value", ""))
    source = str(item.get("source") or item.get("source_name") or item.get("generated_from") or "分析过程证据")
    confidence_input = item.get("confidence")
    trust_level = item.get("trust_level") or item.get("reliability")
    reliability = _infer_reliability(source, confidence_input, trust_level)
    confidence = _infer_confidence(source, reliability, confidence_input)
    source_type = str(item.get("source_type") or _infer_source_type(source))
    claim = str(item.get("claim") or (f"{label}：{value}" if value else f"{label}（待补充详细数据）"))
    requires_manual_review = bool(
        item.get("requires_manual_review")
        or reliability == "low"
        or source in LOW_RELIABILITY_SOURCES
        or not value
    )

    normalized = {
        **item,
        "id": item.get("id") or _stable_id(agent, label, value, source),
        "agent": item.get("agent") or agent,
        "domain": item.get("domain") or domain or DOMAIN_BY_AGENT.get(agent, agent),
        "label": label,
        "name": item.get("name") or label,
        "value": value,
        "source": source,
        "source_name": item.get("source_name") or source,
        "source_url": item.get("source_url") or item.get("url"),
        "source_type": source_type,
        "claim": claim,
        "confidence": confidence,
        "reliability": reliability,
        "trust_level": item.get("trust_level") or reliability,
        "used_in_report": item.get("used_in_report", True),
        "requires_manual_review": requires_manual_review,
        "retrieved_at": item.get("retrieved_at") or datetime.now().isoformat(timespec="seconds"),
        "status": item.get("status") or ("pending" if requires_manual_review else "verified"),
    }
    return normalized


def normalize_evidence_list(items: Iterable[Dict[str, Any]], agent: str = "system", domain: Optional[str] = None) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen = set()
    for item in items or []:
        ev = normalize_evidence(item, agent=agent, domain=domain)
        key = (ev.get("label"), ev.get("value"), ev.get("source"))
        if key in seen:
            continue
        seen.add(key)
        normalized.append(ev)
    return normalized


class EvidenceStore:
    """Small in-memory collector for one task run."""

    def __init__(self, items: Optional[Iterable[Dict[str, Any]]] = None):
        self.items: List[Dict[str, Any]] = []
        self._ids = set()
        if items:
            self.add_many(items)

    def add(self, item: Dict[str, Any], agent: str = "system", domain: Optional[str] = None) -> Dict[str, Any]:
        ev = normalize_evidence(item, agent=agent, domain=domain)
        if ev["id"] not in self._ids:
            self._ids.add(ev["id"])
            self.items.append(ev)
        return ev

    def add_many(self, items: Iterable[Dict[str, Any]], agent: str = "system", domain: Optional[str] = None) -> List[Dict[str, Any]]:
        return [self.add(item, agent=agent, domain=domain) for item in items or []]

    def list(self) -> List[Dict[str, Any]]:
        return list(self.items)

