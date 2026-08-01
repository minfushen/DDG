"""Knowledge base ingestion utilities.

The ingestion path is intentionally reusable from scripts and tests. It scans
Markdown files, extracts simple front matter, chunks by headings/paragraphs, and
writes documents into the configured Chroma vector store.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from app.config import settings
from app.rag.chunking import (
    MIN_CHUNK_CHARS,
    build_group_records,
    pack_blocks,
    split_into_blocks,
)

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover - fallback for local keyword retrieval
    class Document:  # type: ignore
        def __init__(self, page_content: str, metadata: Dict[str, Any]):
            self.page_content = page_content
            self.metadata = metadata


FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


CATEGORY_BY_DIR = {
    "analysis_templates": "template",
    "bank_policy_references": "peer_policy_reference",
    "business_guides": "business_guide",
    "case_studies": "case",
    "cases": "case",
    "credit_dd_guides": "credit_guide",
    "credit_guides": "credit_guide",
    "financial_guides": "financial_guide",
    "industry_guides": "industry_guide",
    "legal_guides": "legal_guide",
    "regulations": "regulation",
    "reporting_guides": "reporting_guide",
    "risk_frameworks": "framework",
    "templates": "template",
}


def _default_base_dir() -> Path:
    return settings.KNOWLEDGE_BASE_DIR


def parse_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text

    metadata: Dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        metadata[key.strip()] = value
    return metadata, text[match.end():]


def _category_for(path: Path, root: Path) -> str:
    try:
        first = path.relative_to(root).parts[0]
    except Exception:
        first = path.parent.name
    return CATEGORY_BY_DIR.get(first, first)


def _heading_info_md(line: str) -> Optional[Dict[str, Any]]:
    """Markdown 标题识别：# / ## / ### 层级，返回 {level, title}。"""
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    level = len(stripped) - len(stripped.lstrip("#"))
    title = stripped.lstrip("#").strip()
    if not title:
        return None
    return {"level": level, "title": title}


def _chunk_markdown(body: str, max_chars: int = 1400) -> List[Dict[str, Any]]:
    """按标题/段落切分 Markdown：表格块原子化、小块合并、携带层级路径。

    与年报 PDF 链路（pdf_knowledge_ingestion）共用 chunking 三条规则：
    表格行串不跨行切分；chunk 元数据携带完整标题链；<200 字符的小块并入相邻块。
    """
    if not body:
        return []
    blocks = split_into_blocks(body, _heading_info_md)
    groups = pack_blocks(blocks, max_chars, prefer_newline=True)
    return build_group_records(groups, section_label="", min_chars=MIN_CHUNK_CHARS)


def build_documents_from_markdown(file_path: Path, root: Path) -> List[Document]:
    raw = file_path.read_text(encoding="utf-8")
    front_matter, body = parse_front_matter(raw)
    category = front_matter.get("category") or _category_for(file_path, root)
    title = front_matter.get("title") or file_path.stem
    source = front_matter.get("source") or "本地知识库"
    disclaimer = front_matter.get("disclaimer") or ""
    tags = front_matter.get("tags") or ""
    rel_path = str(file_path.relative_to(root))
    docs: List[Document] = []

    for index, chunk in enumerate(_chunk_markdown(body)):
        content = chunk["text"]
        hierarchy_path = chunk["hierarchy_path"]
        content_hash = hashlib.sha1(f"{rel_path}|{index}|{content}".encode("utf-8")).hexdigest()[:16]
        docs.append(Document(
            page_content=content,
            metadata={
                "id": f"kb_{content_hash}",
                "title": title,
                "source": str(file_path),
                "relative_path": rel_path,
                "filename": file_path.name,
                "category": category,
                "knowledge_type": _category_for(file_path, root),
                "source_label": source,
                "disclaimer": disclaimer,
                "tags": tags,
                "header": hierarchy_path.split(" > ")[-1] if hierarchy_path else "",
                "hierarchy_path": hierarchy_path,
                "chunk_type": chunk["chunk_type"],
                "chunk_index": index,
            },
        ))
    return docs


def scan_knowledge_documents(root_dir: Path | None = None) -> List[Document]:
    root = root_dir or _default_base_dir()
    docs: List[Document] = []
    for path in sorted(root.rglob("*.md")):
        docs.extend(build_documents_from_markdown(path, root))
    return docs


def ingest_knowledge_base(root_dir: Path | None = None, reset: bool = False) -> Dict[str, Any]:
    """Ingest all Markdown knowledge docs into Chroma."""
    from app.config.embedding_config import get_embedding_model
    from app.rag.vector_store import VectorStoreManager

    persist_dir = settings.DB_DIR / "chroma"
    if reset and persist_dir.exists():
        import shutil
        shutil.rmtree(persist_dir)

    docs = scan_knowledge_documents(root_dir)
    embedding_model = get_embedding_model()
    manager = VectorStoreManager(embedding_model, persist_dir=str(persist_dir))
    vectorstore = manager.get_vectorstore()
    ids = [doc.metadata["id"] for doc in docs]
    if docs:
        vectorstore.add_documents(docs, ids=ids)

    category_counts: Dict[str, int] = {}
    for doc in docs:
        category = doc.metadata.get("category", "unknown")
        category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "success": True,
        "root_dir": str(root_dir or settings.KNOWLEDGE_BASE_DIR),
        "persist_dir": str(persist_dir),
        "documents": len(docs),
        "categories": category_counts,
    }
