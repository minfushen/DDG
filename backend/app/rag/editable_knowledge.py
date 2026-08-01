"""可编辑知识库（非功能需求②：前端灵活修改知识库内容）。

与 Chroma 向量库解耦，提供一份可直接 CRUD 的 JSON 知识条目，并用关键词检索作为
``knowledge_retrieval_service`` 的额外召回源——这样无需重建向量索引即可让人工维护的
知识即时参与分析，且可随时改、随时生效。
"""
from __future__ import annotations

import json
import math
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings

STORE_PATH = settings.DATA_DIR / "editable_knowledge.json"

_CATEGORIES = [
    "regulations", "industry_guides", "analysis_templates",
    "case_studies", "risk_frameworks", "credit_guide", "other",
]


def _read_all() -> List[Dict[str, Any]]:
    if not STORE_PATH.exists():
        return []
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8")) or []
    except Exception:
        return []


def _write_all(items: List[Dict[str, Any]]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_knowledge(category: Optional[str] = None) -> List[Dict[str, Any]]:
    items = _read_all()
    if category:
        items = [it for it in items if (it.get("category") or "other") == category]
    return items


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    return next((it for it in _read_all() if it.get("id") == entry_id), None)


def create_entry(category: str, title: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    if category not in _CATEGORIES:
        category = "other"
    entry = {
        "id": "kb_" + uuid.uuid4().hex[:12],
        "category": category,
        "title": title,
        "content": content,
        "tags": tags or [],
        "source": "editable_knowledge",
        "updated_at": datetime.now().isoformat(),
    }
    items = _read_all()
    items.append(entry)
    _write_all(items)
    return entry


def update_entry(entry_id: str, **fields) -> Optional[Dict[str, Any]]:
    items = _read_all()
    for it in items:
        if it.get("id") == entry_id:
            for k in ("category", "title", "content", "tags"):
                if k in fields and fields[k] is not None:
                    it[k] = fields[k]
            if "category" in fields and fields["category"] not in _CATEGORIES:
                it["category"] = "other"
            it["updated_at"] = datetime.now().isoformat()
            _write_all(items)
            return it
    return None


def delete_entry(entry_id: str) -> bool:
    items = _read_all()
    new = [it for it in items if it.get("id") != entry_id]
    if len(new) == len(items):
        return False
    _write_all(new)
    return True


def _keywords(query: str) -> List[str]:
    return re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", query.lower())[:30]


def search_editable_knowledge(query: str, category: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """关键词检索可编辑知识，返回与 RAG hit 同形的字典，便于合并进分析结果。"""
    terms = _keywords(query)
    if not terms:
        return []
    scored = []
    for it in list_knowledge(category):
        text = f"{it.get('title', '')} {' '.join(it.get('tags', []) or [])} {it.get('content', '')}".lower()
        score = 0.0
        for term in terms:
            c = text.count(term)
            if c:
                score += 1.0 + math.log(c)
                if term in str(it.get("title", "")).lower():
                    score += 1.5
        if score > 0:
            scored.append((it, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    out = []
    for it, score in scored[:top_k]:
        out.append({
            "id": it.get("id"),
            "title": it.get("title"),
            "content": (it.get("content") or "")[:1200],
            "source": "editable_knowledge",
            "category": it.get("category"),
            "knowledge_type": it.get("category"),
            "source_label": "可编辑知识库",
            "disclaimer": "",
            "header": it.get("title"),
            "score": score,
            "confidence": max(0.4, min(0.92, 0.6 + score / 20)),
            "reliability": "high",
            "requires_manual_review": False,
            "retrieval_mode": "editable_knowledge",
        })
    return out
