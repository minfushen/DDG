"""Build dynamic RAG context for financial narrative generation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re

from app.config import settings
from app.rag.knowledge_retrieval_service import retrieve_knowledge


RULE_PATH = settings.BASE_DIR / "knowledge_base" / "risk_frameworks" / "financial_abnormal_rules.json"


@lru_cache(maxsize=1)
def load_financial_abnormal_rules() -> List[Dict[str, Any]]:
    if not Path(RULE_PATH).exists():
        return []
    return json.loads(Path(RULE_PATH).read_text(encoding="utf-8"))


def _parse_percent(value: Any) -> Optional[float]:
    text = str(value or "").strip()
    if not text or "不可用" in text:
        return None
    number_match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not number_match:
        return None
    number = float(number_match.group(0))
    return number / 100 if "%" in text else number


def _parse_ratio(value: Any) -> Optional[float]:
    text = str(value or "").strip()
    if not text or "不可用" in text:
        return None
    number_match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(number_match.group(0)) if number_match else None


def _triggered_rules(key_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    revenue_growth = _parse_percent(key_metrics.get("revenue_growth"))
    receivable_growth = _parse_percent(key_metrics.get("receivable_growth"))
    receivable_to_revenue = _parse_percent(key_metrics.get("receivable_to_revenue"))
    operating_cf_to_net_profit = _parse_ratio(key_metrics.get("operating_cf_to_net_profit"))
    debt_ratio_change = _parse_percent(key_metrics.get("debt_ratio_change"))
    current_ratio_change = _parse_ratio(key_metrics.get("current_ratio_change"))

    active: List[Dict[str, Any]] = []
    for rule in load_financial_abnormal_rules():
        rule_id = rule.get("rule_id")
        triggered = False
        if rule_id == "FIN-CROSS-001" and revenue_growth is not None and receivable_growth is not None:
            triggered = receivable_growth > revenue_growth
        elif rule_id == "FIN-CROSS-002" and revenue_growth is not None and receivable_growth is not None:
            triggered = revenue_growth > max(receivable_growth * 1.5, 0)
        elif rule_id == "FIN-CROSS-003" and receivable_to_revenue is not None:
            triggered = receivable_to_revenue > 0.2
        elif rule_id == "FIN-CROSS-004" and operating_cf_to_net_profit is not None:
            triggered = 0 <= operating_cf_to_net_profit < 0.5
        elif rule_id == "FIN-CROSS-007" and debt_ratio_change is not None and current_ratio_change is not None:
            triggered = debt_ratio_change > 0 and current_ratio_change < 0
        if triggered:
            active.append({**rule, "confidence": 0.82})
    return active[:6]


def _query_from_metrics(enterprise_name: str, key_metrics: Dict[str, Any], risk_summary: List[str], triggered_rules: List[Dict[str, Any]]) -> str:
    rule_titles = " ".join(rule.get("title", "") for rule in triggered_rules)
    return " ".join([
        enterprise_name,
        "财务异常信号 勾稽关系 交叉验证 尽调核查",
        f"营收增速 {key_metrics.get('revenue_growth')} 应收增速 {key_metrics.get('receivable_growth')} 应收营收占比 {key_metrics.get('receivable_to_revenue')}",
        f"经营现金流净利润 {key_metrics.get('operating_cf_to_net_profit')} 资产负债率变化 {key_metrics.get('debt_ratio_change')} 流动比率变化 {key_metrics.get('current_ratio_change')}",
        " ".join(risk_summary[:3]),
        rule_titles,
    ])


def build_financial_knowledge_context(
    enterprise_name: str,
    key_metrics: Dict[str, Any],
    risk_summary: List[str],
    industry_hint: str = "",
    top_k: int = 5,
) -> Dict[str, Any]:
    """Return triggered executable rules and RAG hits for the current financial case."""
    triggered = _triggered_rules(key_metrics)
    query = _query_from_metrics(enterprise_name, key_metrics, risk_summary, triggered)
    if industry_hint:
        query += f" 行业 {industry_hint}"
    retrieval = retrieve_knowledge(query=query, domain="financial", top_k=top_k)
    hits = retrieval.get("results") or []
    knowledge_briefs = []
    for hit in hits[:top_k]:
        knowledge_briefs.append({
            "source_id": hit.get("id"),
            "title": hit.get("title"),
            "source": hit.get("relative_path") or hit.get("source"),
            "header": hit.get("header"),
            "content": hit.get("content", "")[:350],
            "confidence": hit.get("confidence"),
            "retrieval_mode": hit.get("retrieval_mode"),
        })
    return {
        "query": query,
        "triggered_rules": triggered,
        "knowledge_briefs": knowledge_briefs,
        "retrieval": retrieval,
    }
