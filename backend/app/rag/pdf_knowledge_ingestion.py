"""Ingest PDF annual report / research report content into per-company Chroma collections.

This module turns parsed PDF content into RAG-ready Document chunks and writes them
into company-specific Chroma collections. It is designed to be called from batch
scripts and API endpoints, not from the live task execution path.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover
    class Document:  # type: ignore
        def __init__(self, page_content: str, metadata: Dict[str, Any]):
            self.page_content = page_content
            self.metadata = metadata


from app.agents.tools.annual_report_section_extractor import SECTION_LABELS
from app.rag.chunking import (
    MIN_CHUNK_CHARS,
    build_group_records,
    merge_small_chunks,
    pack_blocks,
    split_into_blocks,
)
from app.rag.collection_names import company_collection_name
from app.rag.vector_store import VectorStoreManager


MAX_CHUNK_CHARS = 1400

# 附注/章节层级标题模式（（一）→ 1. → （1）），用于把层级路径写入 chunk 元数据。
_HEADING_LEVELS: List[tuple[re.Pattern[str], int]] = [
    (re.compile(r"^[（(][一二三四五六七八九十百]+[）)]"), 1),  # （一）
    (re.compile(r"^[一二三四五六七八九十百]+、"), 1),          # 一、
    (re.compile(r"^\d{1,2}[.、]\s*\D"), 2),                   # 1. / 1、
    (re.compile(r"^[（(]\d{1,3}[）)]"), 3),                   # （1）
]

DOC_TYPE_CATEGORY = {
    "annual_report": "annual_report",
    "research_report": "research_report",
    "announcement": "public_disclosure",
}

DOC_TYPE_KNOWLEDGE_TYPE = {
    "annual_report": "annual_report",
    "research_report": "research_report",
    "announcement": "public_disclosure",
}

DOC_TYPE_SOURCE_NAME = {
    "annual_report": "巨潮资讯网",
    "research_report": "研报来源",
    "announcement": "巨潮资讯网",
}


def _stable_chunk_id(enterprise_name: str, source_url: str, section: str, chunk_index: int, content: str) -> str:
    raw = f"{enterprise_name}|{source_url}|{section}|{chunk_index}|{content}"
    return "pdf_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _heading_info(line: str) -> Optional[Dict[str, Any]]:
    """识别层级标题行（（一）重要会计政策 / 1. 收入确认 / （1）坏账准备）。"""
    if not line or len(line) > 60:
        return None
    if re.search(r"[。；：,，!?！？]$", line):
        return None
    for pattern, level in _HEADING_LEVELS:
        if pattern.match(line):
            return {"level": level, "title": line.strip()}
    return None


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """按段落边界切分文本；表格块保持原子（不跨行切分），末尾小块合并到相邻块。"""
    if not text:
        return []
    groups = pack_blocks(split_into_blocks(text, _heading_info), max_chars)
    chunks = ["\n".join(block["text"] for block in group) for group in groups]
    return merge_small_chunks(chunks)


def _chunk_text_with_paths(
    text: str,
    section_label: str,
    max_chars: int = MAX_CHUNK_CHARS,
    min_chars: int = MIN_CHUNK_CHARS,
) -> List[Dict[str, Any]]:
    """与 ``_chunk_text`` 相同的切分策略，并携带附注层级路径与块类型。

    ``hierarchy_path`` 记录 chunk 内出现的全部标题链（分号拼接），形如
    "财务报告附注 > （一）重要会计政策 > 1. 收入确认 > （1）坏账准备; ..."，
    检索端可按层级限定召回（如查询"坏账准备计提方法"）。
    """
    groups = pack_blocks(split_into_blocks(text, _heading_info), max_chars)
    return build_group_records(groups, section_label, min_chars=min_chars)


def _table_to_text(table: List[List[str]]) -> str:
    """Convert a parsed table to a compact markdown-like text."""
    if not table:
        return ""
    rows: List[str] = []
    for row in table:
        cells = [str(cell or "").strip() for cell in row]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def build_documents_from_pdf_extraction(
    enterprise_name: str,
    doc_type: str,
    source_url: str,
    title: str,
    extraction_result: Dict[str, Any],
    sections: Optional[Dict[str, Optional[str]]] = None,
    main_business_rows: Optional[List[Dict[str, Any]]] = None,
    published_at: str = "",
    announcement_id: str = "",
) -> List[Document]:
    """Convert a parsed PDF into RAG-ready Document chunks.

    Args:
        enterprise_name: Company name used for collection isolation.
        doc_type: "annual_report", "research_report", or "announcement".
        source_url: Original PDF URL.
        title: Document title.
        extraction_result: Output from extract_pdf / extract_pdf_from_url.
        sections: Extracted narrative sections (annual reports).
        main_business_rows: Structured main-business-composition rows.
        published_at: Publication date.
        announcement_id: Announcement identifier.

    Returns:
        List of Document objects ready for Chroma.
    """
    sections = sections or {}
    parser_used = (extraction_result.get("metadata") or {}).get("parser_used", "")
    category = DOC_TYPE_CATEGORY.get(doc_type, "public_disclosure")
    knowledge_type = DOC_TYPE_KNOWLEDGE_TYPE.get(doc_type, "public_disclosure")
    source_name = DOC_TYPE_SOURCE_NAME.get(doc_type, "PDF来源")

    docs: List[Document] = []

    # 1. Section-based chunks for annual reports.
    for section, text in sections.items():
        if not text:
            continue
        section_label = SECTION_LABELS.get(section, section)
        for chunk_index, chunk in enumerate(_chunk_text_with_paths(text, section_label)):
            chunk_text = chunk["text"]
            doc = Document(
                page_content=chunk_text,
                metadata={
                    "id": _stable_chunk_id(enterprise_name, source_url, section, chunk_index, chunk_text),
                    "title": f"{enterprise_name} - {title}",
                    "source": source_url,
                    "source_name": source_name,
                    "source_type": "exchange_announcement" if doc_type != "research_report" else "research_report",
                    "category": category,
                    "knowledge_type": knowledge_type,
                    "source_label": source_name,
                    "section": section,
                    "section_label": section_label,
                    "enterprise_name": enterprise_name,
                    "announcement_id": announcement_id,
                    "published_at": published_at,
                    "parser_used": parser_used,
                    "chunk_index": chunk_index,
                    "hierarchy_path": chunk["hierarchy_path"],
                    "chunk_type": chunk["chunk_type"],
                    "trust_level": "high",
                    "confidence": 0.85,
                    "requires_manual_review": False,
                },
            )
            docs.append(doc)

    # 2. Table chunks for main business composition.
    if main_business_rows:
        table_text = "\n".join(
            f"{row.get('item_name')}：收入 {row.get('income')}，占比 {row.get('income_ratio')}，毛利率 {row.get('gross_margin')}"
            for row in main_business_rows
            if row.get("item_name")
        )
        if table_text:
            chunk_index = 0
            docs.append(Document(
                page_content=table_text,
                metadata={
                    "id": _stable_chunk_id(enterprise_name, source_url, "main_business_composition_table", chunk_index, table_text),
                    "title": f"{enterprise_name} - {title}",
                    "source": source_url,
                    "source_name": source_name,
                    "source_type": "exchange_announcement" if doc_type != "research_report" else "research_report",
                    "category": category,
                    "knowledge_type": knowledge_type,
                    "source_label": source_name,
                    "section": "main_business_composition_table",
                    "section_label": "主营业务构成表",
                    "enterprise_name": enterprise_name,
                    "announcement_id": announcement_id,
                    "published_at": published_at,
                    "parser_used": parser_used,
                    "chunk_index": chunk_index,
                    "trust_level": "high",
                    "confidence": 0.85,
                    "requires_manual_review": False,
                },
            ))

    # 3. Research reports / announcements without sections: use full text as summary chunks.
    if not sections:
        full_text = extraction_result.get("text") or ""
        for chunk_index, chunk_text in enumerate(_chunk_text(full_text)):
            docs.append(Document(
                page_content=chunk_text,
                metadata={
                    "id": _stable_chunk_id(enterprise_name, source_url, "full_text", chunk_index, chunk_text),
                    "title": f"{enterprise_name} - {title}",
                    "source": source_url,
                    "source_name": source_name,
                    "source_type": "research_report" if doc_type == "research_report" else "public_disclosure",
                    "category": category,
                    "knowledge_type": knowledge_type,
                    "source_label": source_name,
                    "section": "full_text",
                    "section_label": "全文摘要",
                    "enterprise_name": enterprise_name,
                    "announcement_id": announcement_id,
                    "published_at": published_at,
                    "parser_used": parser_used,
                    "chunk_index": chunk_index,
                    "hierarchy_path": "全文摘要",
                    "chunk_type": "narrative",
                    "trust_level": "high",
                    "confidence": 0.8,
                    "requires_manual_review": False,
                },
            ))

    return docs


def _dataframe_to_markdown_table(df) -> str:
    """把 DataFrame 转成紧凑的 markdown 风格表格文本。"""
    if df is None or df.empty:
        return ""
    lines = []
    headers = [str(c) for c in df.columns]
    lines.append(" | ".join(headers))
    lines.append(" | ".join(["---"] * len(headers)))
    for _, row in df.iterrows():
        cells = [str(v) if v is not None else "" for v in row.values]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def build_documents_from_pipeline_result(
    enterprise_name: str,
    pipeline_result: Any,
) -> List[Document]:
    """把 PDF pipeline 输出的结构化三大表和质量摘要转成 RAG Document chunks.

    Args:
        enterprise_name: 企业名称
        pipeline_result: PipelineResult dataclass 或其 dict 形式

    Returns:
        List[Document] 包含三张表和一份质量摘要
    """
    if pipeline_result is None:
        return []

    # 兼容 dataclass 和 dict
    def _get(attr: str, default: Any = None) -> Any:
        if isinstance(pipeline_result, dict):
            return pipeline_result.get(attr, default)
        return getattr(pipeline_result, attr, default)

    statements = _get("statements")
    if statements is None:
        return []

    def _statement_attr(attr: str) -> Any:
        if isinstance(statements, dict):
            return statements.get(attr)
        return getattr(statements, attr, None)

    pdf_url = _get("pdf_url", "")
    report_year = _get("report_year", "")
    title = f"{report_year}年年度报告" if report_year else "年度报告"
    source_name = DOC_TYPE_SOURCE_NAME.get("annual_report", "巨潮资讯网")
    parser_used = "financial_pdf_pipeline"

    docs: List[Document] = []
    statement_sections = {
        "income_statement": "利润表",
        "balance_sheet": "资产负债表",
        "cash_flow": "现金流量表",
    }
    for section, label in statement_sections.items():
        df = _statement_attr(section)
        table_text = _dataframe_to_markdown_table(df)
        if not table_text:
            continue
        content = f"{enterprise_name} {title} - {label}\n{table_text}"
        docs.append(Document(
            page_content=content,
            metadata={
                "id": _stable_chunk_id(enterprise_name, pdf_url, f"pipeline_{section}", 0, content),
                "title": f"{enterprise_name} - {title}",
                "source": pdf_url,
                "source_name": source_name,
                "source_type": "exchange_announcement",
                "category": "annual_report",
                "knowledge_type": "annual_report",
                "source_label": source_name,
                "section": f"pipeline_{section}",
                "section_label": f"PDF管道-{label}",
                "enterprise_name": enterprise_name,
                "parser_used": parser_used,
                "chunk_index": 0,
                "trust_level": "high",
                "confidence": 0.85,
                "requires_manual_review": False,
            },
        ))

    # 质量摘要 chunk
    quality_parts = [
        f"三大表覆盖度: {_get('main_table_coverage', '0/3')}",
        f"自动判定率: {_get('auto_judgment_rate', 0.0):.2f}",
        f"需人工复核: {_get('needs_human_review', True)}",
    ]
    issues = _get("issues", [])
    if issues:
        quality_parts.append(f"问题: {'; '.join(str(i) for i in issues[:5])}")
    quality_text = "\n".join(quality_parts)
    docs.append(Document(
        page_content=quality_text,
        metadata={
            "id": _stable_chunk_id(enterprise_name, pdf_url, "pipeline_quality", 0, quality_text),
            "title": f"{enterprise_name} - {title}",
            "source": pdf_url,
            "source_name": source_name,
            "source_type": "exchange_announcement",
            "category": "annual_report",
            "knowledge_type": "annual_report",
            "source_label": source_name,
            "section": "pipeline_quality",
            "section_label": "PDF管道-解析质量",
            "enterprise_name": enterprise_name,
            "parser_used": parser_used,
            "chunk_index": 0,
            "trust_level": "medium",
            "confidence": 0.75,
            "requires_manual_review": False,
        },
    ))

    return docs


def ingest_company_documents(
    enterprise_name: str,
    documents: List[Document],
    persist_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Write company documents into the per-company Chroma collection.

    Args:
        enterprise_name: Used to derive the collection name.
        documents: RAG-ready Document chunks.
        persist_dir: Optional Chroma persist directory.

    Returns:
        Dict with success, collection_name, document_count.
    """
    from app.config.embedding_config import get_embedding_model

    if not documents:
        return {
            "success": True,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "message": "No documents to ingest",
        }

    collection_name = company_collection_name(enterprise_name)
    embedding_model = get_embedding_model()
    manager = VectorStoreManager(
        embedding_model,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )
    vectorstore = manager.get_vectorstore()
    ids = [doc.metadata["id"] for doc in documents]
    vectorstore.add_documents(documents, ids=ids)

    return {
        "success": True,
        "collection_name": collection_name,
        "document_count": len(documents),
    }


def _ingest_with_timeout(
    enterprise_name: str,
    documents: List[Document],
    persist_dir: Optional[str],
    timeout_seconds: int,
) -> Dict[str, Any]:
    """Run ingest_company_documents in a thread with a timeout.

    Embedding and Chroma writes can block on network or disk; the timeout prevents
    the task from hanging if the vector store is slow.
    """
    import threading

    result: Dict[str, Any] = {}
    error: List[Exception] = []

    def target() -> None:
        try:
            result.update(ingest_company_documents(enterprise_name, documents, persist_dir))
        except Exception as exc:
            error.append(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)
    if thread.is_alive():
        return {
            "success": False,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "error": f"Ingestion timed out after {timeout_seconds} seconds",
        }
    if error:
        return {
            "success": False,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "error": f"{type(error[0]).__name__}: {error[0]}",
        }
    return result


def _ingestion_gap(
    enterprise_name: str,
    title: str,
    pdf_url: str,
    announcement_id: str,
    error: str,
) -> Dict[str, Any]:
    import hashlib
    raw = f"cninfo_ingest|{enterprise_name}|{announcement_id}|{error}"
    return {
        "id": "gap_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16],
        "description": f"巨潮年报《{title}》解析成功但未能写入企业知识库，影响后续 RAG 检索。",
        "why_it_matters": "未入库的年报原文无法通过 RAG 回答用户关于该企业资产负债、速动比率等授信问题。",
        "suggested_next_actions": [
            "检查 embedding 服务可用性",
            "重新触发搜索子任务",
            "使用 scripts/ingest_company_pdf_knowledge.py 手动补录",
        ],
        "severity": "medium",
        "metadata": {
            "enterprise_name": enterprise_name,
            "title": title,
            "pdf_url": pdf_url,
            "announcement_id": announcement_id,
            "error": error,
        },
    }


def auto_ingest_cninfo_annual_report(
    enterprise_name: str,
    cninfo_extraction_result: Dict[str, Any],
    timeout_seconds: Optional[int] = None,
    persist_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Automatically ingest a CNINFO annual report extraction result.

    This is intended to be called by the search sub-agent right after parsing a
    PDF. It returns a structured result and, on failure, an evidence gap that can
    be surfaced to the user instead of being silently swallowed.
    """
    from app.config import settings

    if not settings.AUTO_INGEST_CNINFO_ANNUAL_REPORT:
        return {
            "success": True,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "skipped": True,
            "reason": "AUTO_INGEST_CNINFO_ANNUAL_REPORT is disabled",
            "gaps": [],
        }

    if not cninfo_extraction_result.get("success"):
        return {
            "success": False,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "error": cninfo_extraction_result.get("error") or "Extraction failed",
            "gaps": [],
        }

    timeout = timeout_seconds or settings.AUTO_INGEST_TIMEOUT_SECONDS
    extraction = cninfo_extraction_result.get("extraction_result") or {}
    title = (
        cninfo_extraction_result.get("title")
        or (extraction.get("metadata") or {}).get("title")
        or "年报"
    )
    pdf_url = cninfo_extraction_result.get("pdf_url") or ""
    announcement_id = cninfo_extraction_result.get("announcement_id") or ""

    documents = build_documents_from_pdf_extraction(
        enterprise_name=enterprise_name,
        doc_type="annual_report",
        source_url=pdf_url,
        title=title,
        extraction_result=extraction,
        sections=cninfo_extraction_result.get("sections") or {},
        main_business_rows=cninfo_extraction_result.get("main_business_rows") or [],
        published_at=cninfo_extraction_result.get("published_at") or "",
        announcement_id=announcement_id,
    )

    pipeline_result = cninfo_extraction_result.get("pipeline_result")
    if pipeline_result is not None:
        documents.extend(build_documents_from_pipeline_result(enterprise_name, pipeline_result))

    if not documents:
        return {
            "success": True,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "skipped": True,
            "reason": "No RAG documents generated from extraction",
            "gaps": [],
        }

    result = _ingest_with_timeout(
        enterprise_name=enterprise_name,
        documents=documents,
        persist_dir=persist_dir,
        timeout_seconds=timeout,
    )
    if not result.get("success"):
        result["gaps"] = [
            _ingestion_gap(enterprise_name, title, pdf_url, announcement_id, result.get("error") or "unknown"),
        ]
    else:
        result["gaps"] = []
    return result


def ingest_annual_report_from_cninfo(
    enterprise_name: str,
    cninfo_extraction_result: Dict[str, Any],
    persist_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience: ingest a CNINFO annual report extraction result."""
    if not cninfo_extraction_result.get("success"):
        return {
            "success": False,
            "collection_name": company_collection_name(enterprise_name),
            "document_count": 0,
            "error": cninfo_extraction_result.get("error") or "Extraction failed",
        }

    documents = build_documents_from_pdf_extraction(
        enterprise_name=enterprise_name,
        doc_type="annual_report",
        source_url=cninfo_extraction_result.get("pdf_url", ""),
        title=cninfo_extraction_result.get("extraction_result", {}).get("metadata", {}).get("title", "年报"),
        extraction_result=cninfo_extraction_result.get("extraction_result") or {},
        sections=cninfo_extraction_result.get("sections") or {},
        main_business_rows=cninfo_extraction_result.get("main_business_rows") or [],
    )
    return ingest_company_documents(enterprise_name, documents, persist_dir=persist_dir)
