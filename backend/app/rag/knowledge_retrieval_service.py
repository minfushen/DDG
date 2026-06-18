"""Unified RAG retrieval service with local fallback.

This service is the stable API agents should call. It attempts vector retrieval
first, but falls back to a deterministic Markdown keyword search when embedding
providers or Chroma are unavailable. Returned hits can be converted into
Evidence Store items.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.agents.evidence import normalize_evidence
from app.rag.collection_names import GENERAL_COLLECTION, company_collection_name
from app.rag.knowledge_ingestion import build_documents_from_markdown


DOMAIN_CATEGORIES = {
    "business": ["business_guide", "工商尽调", "peer_policy_reference", "同业制度参考", "credit_guide", "信贷尽调"],
    "financial": ["financial_guide", "财务尽调", "framework", "风险框架", "credit_guide", "授信决策", "peer_policy_reference", "同业制度参考", "annual_report", "research_report"],
    "legal": ["legal_guide", "司法尽调", "peer_policy_reference", "同业制度参考", "case", "尽调案例"],
    "industry": ["industry_guide", "行业指南", "peer_policy_reference", "同业制度参考", "credit_guide", "授信决策", "信贷尽调", "annual_report", "research_report"],
    "credit": ["credit_guide", "授信决策", "信贷尽调", "peer_policy_reference", "同业制度参考", "framework", "风险框架", "annual_report", "research_report"],
    "reporting": ["reporting_guide", "报告话术", "template", "报告模板", "尽调报告模板", "peer_policy_reference", "同业制度参考"],
    "all": [],
}


def _keywords(query: str) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", query.lower())
    seen = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return seen[:30]


@lru_cache(maxsize=1)
def _local_docs() -> List[Any]:
    root = Path(__file__).resolve().parents[2] / "knowledge_base"
    docs = []
    for path in sorted(root.rglob("*.md")):
        try:
            docs.extend(build_documents_from_markdown(path, root))
        except Exception:
            continue
    return docs


def _domain_filter(doc: Any, domain: str) -> bool:
    categories = DOMAIN_CATEGORIES.get(domain, [])
    if not categories:
        return True
    return doc.metadata.get("category") in categories or doc.metadata.get("knowledge_type") in categories


def _score_doc(doc: Any, query_terms: List[str], domain: str) -> float:
    text = f"{doc.metadata.get('title', '')} {doc.metadata.get('tags', '')} {doc.metadata.get('header', '')} {doc.page_content}".lower()
    score = 0.0
    for term in query_terms:
        count = text.count(term)
        if count:
            score += 1.0 + math.log(count)
            if term in str(doc.metadata.get("title", "")).lower() or term in str(doc.metadata.get("tags", "")).lower():
                score += 1.5
    if _domain_filter(doc, domain):
        score += 2.0
    return score


def _format_hit(doc: Any, score: float, retrieval_mode: str) -> Dict[str, Any]:
    confidence = max(0.35, min(0.92, 0.55 + score / 20))
    disclaimer = doc.metadata.get("disclaimer") or ""
    return {
        "id": doc.metadata.get("id"),
        "title": doc.metadata.get("title") or doc.metadata.get("filename"),
        "content": doc.page_content[:1200],
        "source": doc.metadata.get("source"),
        "relative_path": doc.metadata.get("relative_path"),
        "filename": doc.metadata.get("filename"),
        "category": doc.metadata.get("category"),
        "knowledge_type": doc.metadata.get("knowledge_type"),
        "source_label": doc.metadata.get("source_label") or "本地知识库",
        "disclaimer": disclaimer,
        "header": doc.metadata.get("header"),
        "score": score,
        "confidence": confidence,
        "reliability": "medium" if disclaimer else "high",
        "requires_manual_review": bool(disclaimer),
        "retrieval_mode": retrieval_mode,
    }


def _local_keyword_search(query: str, domain: str, top_k: int) -> List[Dict[str, Any]]:
    terms = _keywords(query)
    scored = []
    for doc in _local_docs():
        if not _domain_filter(doc, domain):
            continue
        score = _score_doc(doc, terms, domain)
        if score > 0:
            scored.append((doc, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    selected = []
    seen_sources = set()
    for doc, score in scored:
        source_key = doc.metadata.get("relative_path") or doc.metadata.get("source")
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        selected.append((doc, score))
        if len(selected) >= top_k:
            break
    if len(selected) < top_k:
        selected_keys = {(doc.metadata.get("relative_path") or doc.metadata.get("source"), doc.metadata.get("chunk_index")) for doc, _ in selected}
        for doc, score in scored:
            key = (doc.metadata.get("relative_path") or doc.metadata.get("source"), doc.metadata.get("chunk_index"))
            if key in selected_keys:
                continue
            selected.append((doc, score))
            if len(selected) >= top_k:
                break
    return [_format_hit(doc, score, "local_keyword") for doc, score in selected[:top_k]]


def _vector_search(query: str, domain: str, top_k: int, collection_name: str) -> List[Dict[str, Any]]:
    from app.config.embedding_config import get_embedding_model
    from app.rag.vector_store import VectorStoreManager

    embedding_model = get_embedding_model()
    manager = VectorStoreManager(embedding_model, collection_name=collection_name)
    vectorstore = manager.get_vectorstore()
    categories = DOMAIN_CATEGORIES.get(domain, [])

    raw_results = []
    if categories:
        per_category = max(2, math.ceil(top_k / len(categories)))
        for category in categories:
            raw_results.extend(vectorstore.similarity_search_with_score(
                query=query,
                k=per_category,
                filter={"category": category},
            ))
    else:
        raw_results = vectorstore.similarity_search_with_score(query=query, k=top_k)

    hits: List[Dict[str, Any]] = []
    seen = set()
    for doc, distance in raw_results:
        key = (doc.metadata.get("source"), doc.metadata.get("chunk_index"), doc.page_content[:80])
        if key in seen:
            continue
        seen.add(key)
        score = max(0.0, 1.0 - float(distance)) if isinstance(distance, (int, float)) else 0.65
        hits.append(_format_hit(doc, score * 10, "vector"))
        if len(hits) >= top_k:
            break
    return hits


def _dedupe_and_merge_hits(hit_lists: List[List[Dict[str, Any]]], top_k: int) -> List[Dict[str, Any]]:
    seen = set()
    merged: List[Dict[str, Any]] = []
    for hits in hit_lists:
        for hit in hits:
            key = (hit.get("source"), hit.get("chunk_index"), str(hit.get("content"))[:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)
    merged.sort(key=lambda item: item.get("score", 0), reverse=True)
    return merged[:top_k]


def retrieve_knowledge(query: str, domain: str = "all", top_k: int = 5, company_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve knowledge hits for an agent domain.

    When ``company_name`` is provided, the search spans both the company-specific
    collection (annual reports / research reports) and the general knowledge base
    collection (guides, policies, cases).
    """
    vector_error = ""
    hit_lists: List[List[Dict[str, Any]]] = []

    try:
        if company_name:
            company_hits = _vector_search(
                query=query,
                domain="all",
                top_k=max(2, top_k // 2),
                collection_name=company_collection_name(company_name),
            )
            if company_hits:
                hit_lists.append(company_hits)
    except Exception as exc:
        vector_error = f"company collection search failed: {exc}"

    try:
        general_hits = _vector_search(
            query=query,
            domain=domain,
            top_k=top_k,
            collection_name=GENERAL_COLLECTION,
        )
        if general_hits:
            hit_lists.append(general_hits)
    except Exception as exc:
        vector_error = f"{vector_error}; general collection search failed: {exc}".strip("; ")

    if hit_lists:
        hits = _dedupe_and_merge_hits(hit_lists, top_k)
        return {"success": True, "query": query, "domain": domain, "mode": "vector", "results": hits}

    # Fallback to local keyword search against general knowledge base markdown files.
    hits = _local_keyword_search(query, domain, top_k)
    return {
        "success": True,
        "query": query,
        "domain": domain,
        "mode": "local_keyword",
        "vector_error": vector_error or "vector search returned no results",
        "results": hits,
    }


def knowledge_hits_to_evidence(hits: Iterable[Dict[str, Any]], agent: str, domain: str) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for hit in hits or []:
        title = hit.get("title") or hit.get("filename") or "知识库命中"
        header = hit.get("header") or ""
        claim = f"命中知识库：{title}" + (f" / {header}" if header else "")
        evidence.append(normalize_evidence({
            "label": "知识库命中",
            "value": claim,
            "claim": claim,
            "source": hit.get("source") or hit.get("relative_path") or "本地知识库",
            "source_name": title,
            "source_type": "internal_knowledge_base" if not hit.get("disclaimer") else "peer_policy_reference",
            "confidence": hit.get("confidence", 0.7),
            "trust_level": hit.get("reliability", "medium"),
            "requires_manual_review": hit.get("requires_manual_review", False),
            "metadata": hit,
        }, agent=agent, domain=domain))
    return evidence
